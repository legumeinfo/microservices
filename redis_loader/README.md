# Redis Loader

Various microservices are built on a [Redis](https://redis.io/) database equipped with the [RediSearch](https://oss.redislabs.com/redisearch/) module.
This directory contains a program for loading data into Redis from GFF files or a PostgreSQL database configured with the [Chado](http://gmod.org/wiki/Chado_-_Getting_Started) schema.

## Setup

redis_loader requires running a Redis server with the RediSearch module loaded.
See [RediSearch's quickstart](https://oss.redislabs.com/redisearch/Quick_Start/) for installation instructions.

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
And the Chaddo (PostgreSQL) database credentials can be provided via the `POSTGRES_DATABASE`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT` environment variables.

The loading script can be run as follows

    $ python -m redis_loader

For more information about the script and additional commands and arguments, run

    $ python -m redis_loader --help

If the program was built as a docker container, it can be run as follows

    $ docker run redis_loader
