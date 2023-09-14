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

For more information about the script and additional commands and arguments, run

    $ python -m redis_loader --help

If the program was built as a docker container, it can be run as follows

    $ docker run redis_loader

Any `*.sh` scripts in the container /docker-entrypoint-initdb.d directory will be processed if the `REDIS_DB` (default 0) at `REDIS_HOST` (default 'localhost') on port `REDIS_PORT` (default 6379) is empty:

    $ docker run -e REDIS_HOST=my-redis-db-host -v $PWD/docker-entrypoint-initdb.d:/docker-entrypoint-initdb.d redis_loader

See [gcv-docker-compose](https://github.com/legumeinfo/gcv-docker-compose#redis_loader) instructions for running in the context of the system for which the service was conceived (example with actual data given there!).
