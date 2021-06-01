#!/usr/bin/env python

# Python
import argparse
import os
import re
import sys
from collections import defaultdict
# dependencies
import redisearch
# module
from database import connectToChado, connectToRedis


class EnvArg(argparse.Action):
  '''
  A class that loads argument values from environment variables, resulting in a
  value priority: command line > environment variable > default value
  '''

  def __init__(self, envvar, required=False, default=None, **kwargs):
    if envvar in os.environ:
      default = os.environ[envvar]
    if required and default is not None:
      required = False
    super(EnvArg, self).__init__(default=default, required=required, **kwargs)

  def __call__(self, parser, namespace, values, option_string=None):
    setattr(namespace, self.dest, values)


def parseArgs():
  '''
  Parses command-line arguments.

  Returns:
    argparse.Namespace: A namespace mapping parsed arguments to their values.
  '''

  # create the parser
  parser = argparse.ArgumentParser(
    description=('Loads data from a Chado (PostreSQL) database into a '
                 'RediSearch index for use by the GCV search microservices.'),
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  # PostgreSQL args
  pdb_envvar = 'POSTGRES_DB'
  parser.add_argument(
    '--pdb',
    action=EnvArg,
    envvar=pdb_envvar,
    type=str,
    default='chado',
    help=('The PostgreSQL database (can also be specified using the '
          f'{pdb_envvar} environment variable).'))
  puser_envvar = 'POSTGRES_USER'
  parser.add_argument(
    '--puser',
    action=EnvArg,
    envvar=puser_envvar,
    type=str,
    default='chado',
    help=('The PostgreSQL username (can also be specified using the '
          f'{puser_envvar} environment variable).'))
  ppassword_envvar = 'POSTGRES_PASSWORD'
  parser.add_argument(
    '--ppassword',
    action=EnvArg,
    envvar=ppassword_envvar,
    type=str,
    default=None,
    help=('The PostgreSQL password (can also be specified using the '
          f'{ppassword_envvar} environment variable).'))
  phost_envvar = 'POSTGRES_HOST'
  parser.add_argument(
    '--phost',
    action=EnvArg,
    envvar=phost_envvar,
    type=str,
    default='localhost',
    help=('The PostgreSQL host (can also be specified using the '
          f'{phost_envvar} environment variable).'))
  pport_envvar = 'POSTGRES_PORT'
  parser.add_argument(
    '--pport',
    action=EnvArg,
    envvar=pport_envvar,
    type=int,
    default=5432,
    help=('The PostgreSQL port (can also be specified using the '
          f'{pport_envvar} environment variable).'))
  parser.add_argument(
    '--uniquename',
    action='store_true',
    help=('Load names from the uniquename field of the Chado feature table, '
          'otherwise use the name field.'))
  parser.set_defaults(uniquename=False)

  # Redis args
  rdb_envvar = 'REDIS_DB'
  parser.add_argument(
    '--rdb',
    action=EnvArg,
    envvar=rdb_envvar,
    type=int,
    default=0,
    help=(f'The Redis database (can also be specified using the {rdb_envvar} '
          'environment variable).'))
  rpassword_envvar = 'REDIS_PASSWORD'
  parser.add_argument(
    '--rpassword',
    action=EnvArg,
    envvar=rpassword_envvar,
    type=str,
    default='',
    help=('The Redis password (can also be specified using the '
          f'{rpassword_envvar} environment variable).'))
  rhost_envvar = 'REDIS_HOST'
  parser.add_argument(
    '--rhost',
    action=EnvArg,
    envvar=rhost_envvar,
    type=str,
    default='localhost',
    help=(f'The Redis host (can also be specified using the {rhost_envvar} '
          'environment variable).'))
  rport_envvar = 'REDIS_PORT'
  parser.add_argument(
    '--rport',
    action=EnvArg,
    envvar=rport_envvar,
    type=int,
    default=6379,
    help=(f'The Redis port (can also be specified using the {rport_envvar} '
          'environment variable).'))
  rchunksize_envvar = 'REDIS_CHUNK_SIZE'
  parser.add_argument(
    '--rchunksize',
    action=EnvArg,
    envvar=rchunksize_envvar,
    type=int,
    default=100,
    help=('The chunk size to be used for Redis batch processing (can also be '
          f'specified using the {rchunksize_envvar} environment variable).'))
  parser.add_argument(
    '--no-save',
    dest='nosave',
    action='store_true',
    help='Don\'t save the Redis database to disk after loading.')
  parser.set_defaults(nosave=False)
  load_types = {
      'new': 'Will only load indexes if they have to be created first.',
      'reload': 'Will remove existing indexes before loading data.',
      'append': 'Will add data to an existing index or create a new index.',
    }
  # TODO: prevent argparse from removing line breaks in help text
  loadtype_help = ''.join([
      f'\t{type} - {description} \n '
      for type, description in load_types.items()
    ])
  loadtype_envvar = 'LOAD_TYPE'
  parser.add_argument(
    '--load-type',
    dest='load_type',
    action=EnvArg,
    envvar=loadtype_envvar,
    type=str,
    choices=list(load_types.keys()),
    default='append',
    help=(f'How the data should be loaded into Redis:\n{loadtype_help}'
          f'(can also be specified using the {loadtype_envvar} environment '
          'variable).'))

  return parser.parse_args()


def _redisearchIndex(redis_connection, name, fields, definition, load_type):
  '''
  A helper function that creates a RediSearch index, if necessary, and returns a
  connection to the index.

  Parameters:
    redis_connection (redis.Redis): A connection to a Redis database loaded with
      the RediSearch module.
    name (str): The name of the RediSearch index to be loaded.
    fields (list[redisearch.Field]): The fields the index should contain.
    definition (redisearch.IndexDefinition): A definition of the index.
    load_type (str): The type of load the index will be used for.

  Returns:
    redisearch.Client: A connection to the RediSearch index.
  '''

  index = redisearch.Client(name, conn=redis_connection)
  exists = True
  try:
    index.info()  # will throw an error if index doesn't exist
    print(f'\t"{name}" already exists in RediSearch')
    if load_type == 'new':
      return
  except:
    exists = False
  if exists and load_type == 'reload':
      msg = f'\tClearing {name} index... {}'
      print(msg.format(''))
      index.drop_index()
      exists = False
      _replacePreviousPrintLine(msg.format('done'))
  if not exists:
    msg = f'\tCreating {name} index... {}'
    print(msg.format(''))
    index.create_index(fields, definition=definition)
    _replacePreviousPrintLine(msg.format('done'))
  return index



def _getCvterm(c, name, cv=None):
  '''
  A helper function that loads a CV term from a Chado (PostgreSQL) database by
  name and, optionally, by CV name.

  Parameters:
    c (psycopg2.cursor): A cursor associated with a connection to a PostgreSQL
      database.
    name (str): The name of the CV term to be loaded.
    cv (str, optional): The name a CV term's CV must have.

  Returns:
    int: The Chado database ID of the specified CV term.
  '''

  # get the cvterm
  query = ('SELECT cvterm_id '
           'FROM cvterm '
           'WHERE name=\'' + name + '\'')
  if cv is not None:
    query += ' AND cv_id = (select cv_id from cv where name=\'' + cv + '\')'
  query += ';'
  c.execute(query)
  # does it exist?
  if not c.rowcount:
    raise Exception('Failed to retrieve the "' + name + '" cvterm entry')
  term, = c.fetchone()
  return term


def _replacePreviousPrintLine(newline):
  '''
  A helper function that replaces the previous line in the command-line with the
  given newline.

  Parameters:
    newline (str): The newline to replace the previous line with.
  '''

  sys.stdout.write('\033[F') # back to previous line
  sys.stdout.write('\033[K') # clear line
  print(newline)


def transferChromosomes(postgres_connection, redis_connection, chunk_size,
load_type, uniquename):
  '''
  Loads chromosomes from a Chado (PostgreSQL) database into a RediSearch
  database.

  Parameters:
    postgres_connection (psycopg2.connection): A connection to the PostgreSQL
      database to load data from.
    redis_connection (redis.Redis): A connection to the Redis database to be
      loaded.
    chunk_size (int): The chunk size to be used for Redis batch processing.
    load_type (str): The type of load that should be performed.
    uniquename (bool): Whether or not the chromosome names should come from the
      "uniquename" field of the Chado Feature table.

  Returns:
    dict[int, str]: A dictionary mapping Chado database IDs of chromosomes to
      the name they were loaded into Redis with.
  '''

  print('Loading chromosomes...')
  # prepare RediSearch
  indexName = 'chromosomeIdx'
  fields = [
      redisearch.TextField('name'),
      redisearch.NumericField('length'),
      redisearch.TextField('genus'),
      redisearch.TextField('species'),
    ]
  definition = redisearch.IndexDefinition(prefix=['chromosome:'])
  chromosome_index = \
    _redisearchIndex(redis_connection, indexName, fields, definition, load_type)
  indexer = chromosome_index.batch_indexer(chunk_size=chunk_size)

  # load the data
  with postgres_connection.cursor() as c:

    # get cvterms
    msg = '\tLoading cvterms... {}'
    print(msg.format(''))
    chromosome_id = _getCvterm(c, 'chromosome', 'sequence')
    #supercontig_id = _getCvterm(c, 'supercontig', 'sequence')
    _replacePreviousPrintLine(msg.format('done'))

    # get all the organisms
    msg = '\tLoading organisms... {}'
    print(msg.format(''))
    i = 0
    query = ('SELECT organism_id, genus, species '
             'FROM organism;')
    c.execute(query)
    organism_id_map = {}
    for (o_id, o_genus, o_species,) in c:
      organism_id_map[o_id] = {'genus': o_genus, 'species': o_species}
    _replacePreviousPrintLine(msg.format('done'))

    # get all the chromosomes
    msg = '\tLoading chromosomes... {}'
    print(msg.format(''))
    name = 'uniquename' if uniquename else 'name'
    query = (f'SELECT feature_id, {name}, organism_id, seqlen '
             'FROM feature '
             'WHERE type_id=' + str(chromosome_id) + ';')
    #         'OR type_id=' + str(supercontig_id) + ';')
    c.execute(query)
    _replacePreviousPrintLine(msg.format('done'))

    # index the chromosomes
    msg = '\tIndexing chromosomes... {}'
    print(msg.format(''))
    chromosome_id_name_map = {}
    for (chr_id, chr_name, chr_organism_id, chr_length,) in c:
      chromosome_id_name_map[chr_id] = chr_name
      organism = organism_id_map[chr_organism_id]
      indexer.add_document(
        f'chromosome:{chr_name}',
        name=chr_name,
        length=chr_length,
        genus=organism['genus'],
        species=organism['species'],
      )
    indexer.commit()
    _replacePreviousPrintLine(msg.format('done'))

    return chromosome_id_name_map


def transferGenes(postgres_connection, redis_connection, chunk_size, load_type,
chromosome_id_name_map, uniquename):
  '''
  Loads genes from a Chado (PostgreSQL) database into a RediSearch database.

  Parameters:
    postgres_connection (psycopg2.connection): A connection to the PostgreSQL
      database to load data from.
    redis_connection (redis.Redis): A connection to the Redis database to be
      loaded.
    chunk_size (int): The chunk size to be used for Redis batch processing.
    load_type (str): The type of load that should be performed.
    chromosome_id_name_map (dict[int, str]): A dictionary mapping Chado database
      IDs of chromosomes to the name they were loaded into Redis with.
    uniquename (bool): Whether or not the genes names should come from the
      "uniquename" field of the Chado Feature table.
  '''

  print('Loading genes...')
  # prepare RediSearch
  indexName = 'geneIdx'
  fields = [
    redisearch.TextField('chromosome'),
    redisearch.TextField('name'),
    redisearch.NumericField('fmin'),
    redisearch.NumericField('fmax'),
    redisearch.TextField('family'),
    redisearch.NumericField('strand'),
    redisearch.NumericField('index', sortable=True),
  ]
  definition = redisearch.IndexDefinition(prefix=['gene:'])
  interval_index = \
    _redisearchIndex(redis_connection, indexName, fields, definition, load_type)
  indexer = interval_index.batch_indexer(chunk_size=chunk_size)

  with postgres_connection.cursor() as c:

    # get cvterms
    msg = '\tLoading cvterms... {}'
    print(msg.format(''))
    gene_id = _getCvterm(c, 'gene', 'sequence')
    genefamily_id = _getCvterm(c, 'gene family')
    _replacePreviousPrintLine(msg.format('done'))

    # get all the gene annotations
    msg = '\tLoading gene annotations... {}'
    print(msg.format(''))
    query = ('SELECT feature_id, value '
             'FROM featureprop '
             'WHERE type_id=' + str(genefamily_id) + ';')
    c.execute(query)
    gene_id_family_map = dict((g_id, g_family) for (g_id, g_family,) in c)
    _replacePreviousPrintLine(msg.format('done'))

    # get all the genes
    msg = '\tLoading genes... {}'
    print(msg.format(''))
    name = 'uniquename' if uniquename else 'name'
    query = (f'SELECT fl.srcfeature_id, f.feature_id, f.{name}, fl.fmin, '
             'fl.fmax, fl.strand '
             'FROM featureloc fl, feature f '
             'WHERE fl.feature_id=f.feature_id '
             'AND f.type_id=' + str(gene_id) + ';')
    c.execute(query)
    _replacePreviousPrintLine(msg.format('done'))

    # prepare genes for indexing
    msg = '\tProcessing genes... {}'
    print(msg.format(''))
    chromosome_genes = defaultdict(list)
    for (chr_id, g_id, g_name, g_fmin, g_fmax, g_strand,) in c:
      if chr_id in chromosome_id_name_map:
        gene = {
            'name': g_name,
            'fmin': g_fmin,
            'fmax': g_fmax,
            'strand': g_strand,
            'family': gene_id_family_map.get(g_id, ''),
          }
        chromosome_genes[chr_id].append(gene)
    _replacePreviousPrintLine(msg.format('done'))

    # index the genes
    msg = '\tIndexing genes... {}'
    print(msg.format(''))
    pipeline = redis_connection.pipeline()
    for chr_id, genes in chromosome_genes.items():
      chr_name = chromosome_id_name_map[chr_id]
      genes.sort(key=lambda g: g['fmin'])
      # RediSearch
      for (j, gene) in enumerate(genes):
        gene_name = gene['name']
        indexer.add_document(
          f'gene:{gene_name}',
          chromosome=chr_name,
          name=gene['name'],
          fmin=gene['fmin'],
          fmax=gene['fmax'],
          strand= gene['strand'],
          family=gene['family'],
          index=j,
        )
      # Redis
      pipeline.delete(f'chromosome:{chr_name}:genes')
      pipeline.rpush(
        f'chromosome:{chr_name}:genes',
        *map(lambda g: g['name'], genes)
      )
      pipeline.delete(f'chromosome:{chr_name}:families')
      pipeline.rpush(
        f'chromosome:{chr_name}:families',
        *map(lambda g: g['family'], genes)
      )
      pipeline.delete(f'chromosome:{chr_name}:fmins')
      pipeline.rpush(
        f'chromosome:{chr_name}:fmins',
        *map(lambda g: g['fmin'], genes)
      )
      pipeline.delete(f'chromosome:{chr_name}:fmaxs')
      pipeline.rpush(
        f'chromosome:{chr_name}:fmaxs',
        *map(lambda g: g['fmax'], genes)
      )
    indexer.commit()
    pipeline.execute()
    _replacePreviousPrintLine(msg.format('done'))


def transferData(postgres_connection, redis_connection, chunk_size, load_type,
uniquename, nosave):

  chromosome_id_name_map = \
    transferChromosomes(
      postgres_connection,
      redis_connection,
      chunk_size,
      load_type,
      uniquename
    )
  transferGenes(
    postgres_connection,
    redis_connection,
    chunk_size,
    load_type,
    chromosome_id_name_map,
    uniquename
  )
  # manually save the data
  if not nosave:
    redis_connection.save()


if __name__ == '__main__':
  args = parseArgs()
  # connect to the databases
  postgres_connection = None
  redis_connection = None
  msg = 'Connecting to PostgreSQL... {}'
  print(msg.format(''))
  try:
    postgres_connection = \
      connectToChado(
        args.pdb,
        args.puser,
        args.ppassword,
        args.phost,
        args.pport,
      )
  except Exception as e:
    _replacePreviousPrintLine(msg.format('failed'))
    exit(e)
  _replacePreviousPrintLine(msg.format('done'))
  msg = 'Connecting to Redis... {}'
  print(msg.format(''))
  try:
    redis_connection = \
      connectToRedis(args.rhost, args.rport, args.rdb, args.rpassword)
  except Exception as e:
    _replacePreviousPrintLine(msg.format('failed'))
    exit(e)
  _replacePreviousPrintLine(msg.format('done'))
  # transfer the relevant data from Chado to Redis
  try:
    transferData(
      postgres_connection,
      redis_connection,
      args.rchunksize,
      args.load_type,
      args.uniquename,
      args.nosave,
    )
  except Exception as e:
    print(e)
  # disconnect from the database
  postgres_connection.close()
