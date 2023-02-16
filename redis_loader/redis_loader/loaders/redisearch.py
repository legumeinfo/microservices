# dependencies
import redis
from redis.commands.search import Search
from redis.commands.search.field import NumericField, TagField, TextField
from redis.commands.search.indexDefinition import IndexDefinition

# module
import redis_loader

VERSION_KEY = "GCV_SCHEMA_VERSION"
COMPATIBLE_KEY = "GCV_COMPATIBLE_SCHEMA_VERSIONS"

GENE_INDEX_NAME = "geneIdx"
CHROMOSOME_INDEX_NAME = "chromosomeIdx"


class SchemaVersionError(Exception):
    """
    The exception to raise when a GCV database already exists but its schema
    version isn't supported by the loader.
    """

    pass


class RediSearchExistsError(Exception):
    """
    The exception to raise when Redis already containing data related to the
    loader is incompatible with the specified load type.
    """

    pass


class RediSearchLoader(object):
    """
    A class that provides an interface for consistently loading data into a
    Redis database containing the RediSearch module. This includes managing a
    connection to the Redis database, which is most effectively done by using the
    class as a Context Manager.
    """

    def __init__(self, **kwargs):
        self.load_type = kwargs.get("load_type")
        self.no_save = kwargs.get("no_save")
        # connect to Redis
        self.redis_connection = self.__connectToRedis(
            kwargs.get("host"),
            kwargs.get("port"),
            kwargs.get("db"),
            kwargs.get("password"),
        )
        # check that the existing database schema is compatible
        if self.load_type == "append":
            schema_version = self.getExistingSchemaVersion()
            if (
                schema_version is not None
                and schema_version != redis_loader.__schema_version__
            ):
                message = (
                    "An existing GCV database was found with schema version "
                    f"{schema_version} but this loader only supports version "
                    f"{redis_loader.__schema_version__} of the schema."
                )
                raise SchemaVersionError(message)
        # setup RediSearch
        self.chromosome_indexer, self.gene_indexer = self.__setupIndexes(
            kwargs.get("chunk_size")
        )

    def __enter__(self):
        """
        The method executed when the class is instantiated using 'with' syntax.

        Returns:
          RediSearchLoader: The instantiated instance of the class.
        """
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        """
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
        """
        self.close()

    def __connectToRedis(self, host="localhost", port=6379, db=0, password=""):
        """
        Creates a connection to a Redis database.

        Parameters:
          host (str): The host to connect to.
          port (int): The port to connect to on the host.
          db (int): The database to connect to.
          password (str): The password to use when connecting to the database.

        Returns:
          redis.Redis: A connection to a Redis database.
        """

        # instantiate a connection instance
        connection = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
        )
        # ping to force connection, preventing errors downstream
        connection.ping()

        return connection

    def __makeOrGetIndex(self, name, fields, definition, chunk_size):
        """
        Creates a RediSearch index, if necessary, and returns a batch indexer for
        bulk loading data into it.

        Parameters:
          name (str): The name of the RediSearch index to be loaded.
          fields (list[redis.commands.search.field.Field]): The fields the index should
            contain.
          definition (redis.commands.search.indexDefinition.IndexDefinition): A
            definition of the index.
          chunk_size (int): The chunk size to be used for Redis batch processing.

        Returns:
          redis.commands.search.Search.BatchIndexer: A batch processor for the index.
        """

        # create a Search for the index that may or may not exist
        index = Search(self.redis_connection, index_name=name)
        # determine if the index exists
        exists = True
        try:
            index.info()  # will throw an error if index doesn't exist
            print(f'\t"{name}" already exists in RediSearch')
            if self.load_type == "new":
                message = (
                    f'Index "{name}" already exists but load type '
                    f'"{self.load_type}" does not support preexisting indexes.'
                )
                raise RediSearchExistsError(message)
        except redis.RedisError:
            exists = False
        # clear the index if necessary
        if exists:
            if self.load_type == "reload":
                print(f'\tDropping index "{name}"')
                index.dropindex(delete_documents=True)
                exists = False
            if self.load_type == "append":
                print(f'\tData will be appended to index "{name}"')
        # create the index if necessary
        if not exists:
            print(f'\tCreating index "{name}"')
            index.create_index(fields, definition=definition)
        # create a batch indexer for the index
        indexer = index.batch_indexer(chunk_size=chunk_size)

        return indexer

    def __checkChromosomeKeys(self):
        keys = self.redis_connection.keys("chromosome:*")
        if keys:
            print('\tKeys that match "chromosome:*" already exists')
            if self.load_type == "new":
                message = f"""
                    Chromosome keys already exists but load type {self.load_type}" does
                    not support preexisting keys.
                 """
                raise RediSearchExistsError(message)
            if self.load_type == "reload":
                print('\tDropping keys that match "chromosome:*"')
                # NOTE: we create a pipeline and iterate instead of expanding keys into
                # a single delete call in case there's A LOT of keys to avoid overflow
                pipeline = self.redis_connection.pipeline()
                for key in keys:
                    pipeline.delete(key)
                pipeline.execute()
            elif self.load_type == "append":
                print('\tNew "chromosome:*" keys will be appended')

    def __setupIndexes(self, chunk_size):
        """
        Sets up RediSearch indexes for chromosomes and genes.

        Parameters:
          chunk_size (int): The chunk size to be used for Redis batch processing.

        Returns:
          redis.commands.search.Search.BatchIndexer: A batch processor for the
            chromosome index.
          redis.commands.search.Search.BatchIndexer: A batch processor for the gene
            index.
        """

        # create the chromosome index
        chromosome_fields = [
            # TextField to support fuzzy search, use document ID for recovering specific
            # chromosomes
            TextField("name"),
            NumericField("length"),
            # TagField since this is a foreign key, i.e. we only match exactly
            TagField("genus"),
            # TagField since this is a foreign key, i.e. we only match exactly
            TagField("species"),
        ]
        chromosome_definition = IndexDefinition(prefix=["chromosome:"])
        chromosome_indexer = self.__makeOrGetIndex(
            CHROMOSOME_INDEX_NAME,
            chromosome_fields,
            chromosome_definition,
            chunk_size,
        )
        # check if any non-RediSearch chromosome keys exist, and drop if necessary
        self.__checkChromosomeKeys()

        # create the gene index
        gene_fields = [
            # TagField since this is a foreign key, i.e. we only match exactly
            TagField("chromosome"),
            # TextField to support fuzzy search, use document ID for recovering specific
            # genes
            TextField("name"),
            NumericField("fmin"),
            NumericField("fmax"),
            # TagField since this is a foreign key, i.e. we only match exactly
            TagField("family"),
            NumericField("strand"),
            NumericField("index", sortable=True),
        ]
        gene_definition = IndexDefinition(prefix=["gene:"])
        gene_indexer = self.__makeOrGetIndex(
            GENE_INDEX_NAME,
            gene_fields,
            gene_definition,
            chunk_size,
        )

        # set the schema version and compatible versions
        self.redis_connection.set(VERSION_KEY, redis_loader.__schema_version__)
        self.redis_connection.delete(COMPATIBLE_KEY)
        self.redis_connection.sadd(
            COMPATIBLE_KEY, *redis_loader.__compatible_schema_versions__
        )

        return chromosome_indexer, gene_indexer

    def save(self):
        """Saves the Redis database to disk."""
        if not self.no_save:
            self.redis_connection.save()

    def close(self):
        """Closes the Redis connection."""
        self.chromosome_indexer.commit()
        self.gene_indexer.commit()
        self.save()
        self.redis_connection.close()

    def indexChromosome(self, name, length, genus, species):
        """
        Index a given chromosome.

        Parameters:
          name (str): The name of the chromosome.
          length (int): The length of the chromosome in base pairs.
          genus (str): The genus of the chromosome's organism.
          species (str): The species of the chromosome's organism.
        """

        self.chromosome_indexer.add_document(
            f"chromosome:{name}",
            name=name,
            length=length,
            genus=genus,
            species=species,
        )

    def indexChromosomeGenes(self, chromosome, genes):
        """
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
        """

        # ensure the genes are in order
        genes.sort(key=lambda g: g["fmin"])

        # load each gene into RediSearch
        for i, gene in enumerate(genes):
            name = gene["name"]
            self.gene_indexer.add_document(
                f"gene:{name}",
                chromosome=chromosome,
                name=name,
                fmin=gene["fmin"],
                fmax=gene["fmax"],
                strand=gene["strand"],
                family=gene["family"],
                index=i,
            )
        self.gene_indexer.commit()

        # save the gene attributes as ordered lists in Redis for indexed retrieval
        # and slicing
        pipeline = self.redis_connection.pipeline()
        pipeline.rpush(
            f"chromosome:{chromosome}:genes", *map(lambda g: g["name"], genes)
        )
        pipeline.rpush(
            f"chromosome:{chromosome}:families", *map(lambda g: g["family"], genes)
        )
        pipeline.rpush(
            f"chromosome:{chromosome}:fmins", *map(lambda g: g["fmin"], genes)
        )
        pipeline.rpush(
            f"chromosome:{chromosome}:fmaxs", *map(lambda g: g["fmax"], genes)
        )
        pipeline.execute()

    def getExistingSchemaVersion(self):
        default_version = "1.0.0"
        # get the existing schema version
        existing_version = self.redis_connection.get(VERSION_KEY)
        # no version found
        if existing_version is None:
            # check if a v1.0.0 GCV database already exists
            gene_index = Search(self.redis_connection, index_name=GENE_INDEX_NAME)
            chromosome_index = Search(
                self.redis_connection, index_name=CHROMOSOME_INDEX_NAME
            )
            try:
                gene_index.info()  # will throw an error if index doesn't exist
                chromosome_index.info()  # ditto
                print(
                    f"""
                    found existing GCV database without schema version; assuming version
                    {default_version}
                """
                )
                existing_version = default_version
            except redis.RedisError:
                pass
        return existing_version
