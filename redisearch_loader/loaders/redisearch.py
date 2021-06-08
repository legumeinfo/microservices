import redis
import redisearch


class RediSearchIndexExistsError(Exception):
  '''
  The exception to raise when a RediSearch index already existing is
  incompatible with the specified load type.
  '''
  pass


class RediSearchLoader(object):
  '''
  A class that provides an interface for consistently loading data into a
  Redis database containing the RediSearch module. This includes managing a
  connection to the Redis database, which is most effectively done by using the
  class as a Context Manager.
  '''

  def __init__(self, **kwargs):
    self.load_type = kwargs.get('load_type')
    self.no_save = kwagrsd.get('no_save')
    # connect to Redis
    self.redis_connection = \
      self.__connectToRedis(
        kwargs.get('host'),
        kwargs.get('port'),
        kwargs.get('db'),
        kwargs.get('password'),
      )
    # setup RediSearch
    self.chromosome_indexer, self.gene_indexer = \
      self.__setupIndexes(kwargs.get('chunk_size'))

  def __enter__(self):
    '''
    The method executed when the class is instantiated using 'with' syntax.
  
    Returns:
      RediSearchLoader: The instantiated instance of the class.
    '''
    return self

  def __exit__(self, exception_type, exception_value, exception_traceback):
    '''
    The method executed after the run-time context of the 'with' block exits
    when the class is instantiated using 'with' syntax .

    exception_type (Error): The type of error that triggered the exit. The value
      is None if the context is exiting without an error.
    exception_value (object): The value associated with the error type. It could
      be a variety of types, including a string describing the error or a tuple
      with an error code and an error description. The value is None if the
      context is exiting without an error.
    exception_traceback (TracebackType): The traceback of the error that caused
      the exit. The value is None if the context is exiting without an error.
    '''
    self.close()

  def __connectToRedis(self, host='localhost', port=6379, db=0, password=''):
    '''
    Creates a connection to a Redis database.
  
    Parameters:
      host (str): The host to connect to.
      port (int): The port to connect to on the host.
      db (int): The database to connect to.
      password (str): The password to use when connecting to the database.
  
    Returns:
      redis.Redis: A connection to a Redis database.
    '''

    pool = redis.ConnectionPool(host, port, db, password)
    connection = redis.Redis(connection_pool=pool)
    # ping to force connection, preventing errors downstream
    connection.ping()
    return connection

  def __makeOrGetIndex(name, fields, definition, chunk_size):
    '''
    Creates a RediSearch index, if necessary, and returns a batch indexer for
    bulk loading data into it.
  
    Parameters:
      name (str): The name of the RediSearch index to be loaded.
      fields (list[redisearch.Field]): The fields the index should contain.
      definition (redisearch.IndexDefinition): A definition of the index.
      chunk_size (int): The chunk size to be used for Redis batch processing.
  
    Returns:
      redisearch.Client.BatchIndexer: A batch processor for the index.
    '''

    # create a Client for the index that may or may not exist
    index = redisearch.Client(name, conn=self.redis_connection)
    # determine if the index exists
    exists = True
    try:
      index.info()  # will throw an error if index doesn't exist
      print(f'\t"{name}" already exists in RediSearch')
      if self.load_type == 'new':
        message = (f'Index "{name}" already exists but load type '
                  f'"{self.load_type}" does not support preexisting indexes.')
        raise RediSearchIndexExistsError(message)
    except redis.RedisError:
      exists = False
    # clear the index if necessary
    if exists and self.load_type == 'reload':
        index.drop_index()
        exists = False
    # create the index if necessary
    if not exists:
      index.create_index(fields, definition=definition)
    # create a batch indexer for the index
    indexer = chromosome_index.batch_indexer(chunk_size=chunk_size)

    return indexer

  def __setupIndexes(self, chunk_size):
    '''
    Sets up RediSearch indexes for chromosomes and genes.
  
    Parameters:
      chunk_size (int): The chunk size to be used for Redis batch processing.
  
    Returns:
      redisearch.Client.BatchIndexer: A batch processor for the chromosome
        index.
      redisearch.Client.BatchIndexer: A batch processor for the gene index.
    '''

    # create the chromosome index
    chromosome_name = 'chromosomeIdx'
    chromosome_fields = [
        redisearch.TextField('name'),
        redisearch.NumericField('length'),
        redisearch.TextField('genus'),
        redisearch.TextField('species'),
      ]
    chromosome_definition = redisearch.IndexDefinition(prefix=['chromosome:'])
    chromosome_indexer = \
      self.__makeOrGetIndex(
        chromosome_name,
        chromosome_fields,
        chromosome_definition,
        chunk_size,
      )

    # create the gene index
    gene_name = 'geneIdx'
    gene_fields = [
      redisearch.TextField('chromosome'),
      redisearch.TextField('name'),
      redisearch.NumericField('fmin'),
      redisearch.NumericField('fmax'),
      redisearch.TextField('family'),
      redisearch.NumericField('strand'),
      redisearch.NumericField('index', sortable=True),
    ]
    gene_definition = redisearch.IndexDefinition(prefix=['gene:'])
    gene_indexer = \
      self.__makeOrGetIndex(gene_name, gene_fields, gene_definition, chunk_size)

    return chromosome_indexer, gene_indexer

  def save(self):
    '''Saves the Redis database to disk.'''
    if not self.no_save:
      self.redis_connection.save()

  def close(self):
    '''Closes the Redis connection.'''
    self.chromosome_indexer.commit()
    self.gene_indexer.commit()
    self.save()
    self.redis_connection.close()

  def indexChromosome(self, name, length, genus, species):
    '''
    Index a given chromosome.
  
    Parameters:
      name (str): The name of the chromosome.
      length (int): The length of the chromosome in base pairs.
      genus (str): The genus of the chromosome's organism.
      species (str): The species of the chromosome's organism.
    '''

    self.chromosome_indexer\
      .add_document(
        f'chromosome:{name}',
        name=name,
        length=length,
        genus=genus,
        species=species,
      )

  def indexChromosomeGenes(self, chromosome, genes):
    '''
    Index the genes for a given chromosome.
  
    Parameters:
      chromosome (str): The name of the chromosome the genes are from.
      genes
      (
        list[{
          'name': str,
          'fmin': int,
          'fmax': int,
          'strand': int,
          'family': str,
        }]
      ): The chromosome's genes.
    '''

    # ensure the genes are in order
    genes.sort(key=lambda g: g['fmin'])

    # load each gene into RediSearch
    for i, gene in enumerate(genes):
      name = gene['name']
      self.gene_indexer.add_document(
        f'gene:{name}',
        chromosome = chromosome,
        name = name,
        fmin = gene['fmin'],
        fmax = gene['fmax'],
        strand = gene['strand'],
        family = gene['family'],
        index = i,
      )
    self.gene_indexer.commit()

    # save the gene attributes as ordered lists in Redis for indexed retrieval
    # and slicing
    pipeline = self.redis_connection.pipeline()
    pipeline.delete(f'chromosome:{chromosome}:genes')
    pipeline.rpush(f'chromosome:{chromosome}:genes', *map(lambda g: g['name'], genes))
    pipeline.delete(f'chromosome:{chromosome}:families')
    pipeline.rpush(f'chromosome:{chromosome}:families', *map(lambda g: g['family'], genes))
    pipeline.delete(f'chromosome:{chromosome}:fmins')
    pipeline.rpush(f'chromosome:{chromosome}:fmins', *map(lambda g: g['fmin'], genes))
    pipeline.delete(f'chromosome:{chromosome}:fmaxs')
    pipeline.rpush(f'chromosome:{chromosome}:fmaxs', *map(lambda g: g['fmax'], genes))
    pipeline.execute()
