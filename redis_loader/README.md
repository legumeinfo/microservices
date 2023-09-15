# Redis Loader

Various microservices are built on a [Redis](https://redis.io/) database equipped with the [RediSearch](https://oss.redislabs.com/redisearch/) module.
This directory contains a program for loading data into Redis from GFF files or a PostgreSQL database configured with the [Chado](http://gmod.org/wiki/Chado_-_Getting_Started) schema.

## Setup

redis_loader requires running a Redis server with the RediSearch module loaded.
See [RediSearch's quickstart](https://oss.redislabs.com/redisearch/Quick_Start/) for installation instructions. By default, Redis is configured to automatically backup to disk whenever the database changes. However, this may cause issues if you're repeatedly running redis_loader (e.g. running in a bash script to bulk load several GFF files). To avoid any such problems, we recommend running Redis with the ` --save ""` flag, which disables its automatic background saving (see the [Redis config documentation](https://redis.io/docs/manual/config/) for other methods of changing this setting). Changes to the database can still be saved to disk by explicitly calling the Redis [SAVE command](https://redis.io/commands/save/), which redis_loader does by default (disable this behavior with the `--no-save` flag). **Using these flags is how to effectively implement transactional loading, i.e. if a load fails the changes will not be written to disk, though the database in memory will need to be reloaded to purge the partial changes.**

redis_loader is currently not available via pip so it must be built locally.
We recommend installing redis_loader in a [Python Virtual Environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/) to avoid conflicts with other package managers and Python projects.

To install redis_loader, simply run

    $ python setup.py install

or

    $ pip install .

Alternatively, the Docker container can be built with

    $ docker build . -t redis_loader:latest

## Running

The script loads data into Redis from GFF files or a Chado (PostgreSQL) database.
The credentials for Redis and the different data sources can be set via command line flags or via environment variables.
The Redis credentials can be provided via the `REDIS_DB`, `REDIS_PASSWORD`, `REDIS_HOST`, and `REDIS_PORT` environment variables.
The GFF credits can be provided via the `GENUS`, `SPECIES`, `STRAIN`, `GENE_GFF_FILE`, `CHROMOSOME_GFF_FILE`, and `GFA_FILE` environment variables.
And the Chado (PostgreSQL) database credentials can be provided via the `POSTGRES_DATABASE`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT` environment variables.

The loading script can be run as follows

    $ python -m redis_loader

By default, the loading script will only load new databases, i.e. no data will be loaded if the indexes it creates already exist.
This behavior can be changed using the `--load-type` flag.
For example, the following command will create a new database or append data to an existing database:

    $ python -m redis_loader --load-type append

For more information about the script and additional commands and arguments, run

    $ python -m redis_loader --help

If the program was built as a docker container, it can be run as follows

    $ docker run redis_loader

When the loading script is run without any arguments AND the target Redis database is empty, any `*.sh` scripts in the container's `/docker-entrypoint-initdb.d/` directory will be executed in alphabetical order.
Custom `*sh` scripts can be put in the container's `/docker-entrypoint-initdb/` directory using [volumes](https://docs.docker.com/storage/volumes/):

    $ docker run -v /path/to/local/docker-entrypoint-initdb.d:/docker-entrypoint-initdb.d:rw redis_loader

These scripts should use the Python command above to load data.

See the [gcv-docker-compose instructions](https://github.com/legumeinfo/gcv-docker-compose#loading-data) for examples of using the loading script.
