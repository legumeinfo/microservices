# Genome Context Viewer Redis loader

The microservices that support the GCV client are built on a [Redis](https://redis.io/) database equipped with the [RediSearch](https://oss.redislabs.com/redisearch/) module.
This directory contains scripts for loading data into Redis from GFF files or a PostgreSQL database configured with the [Chado](http://gmod.org/wiki/Chado_-_Getting_Started) schema.

## Setup

RediSearch is a module for Redis.
It can be [installed locally or run via Docker](https://oss.redislabs.com/redisearch/Quick_Start/).
When running with Docker, we recommend mounting a volume to ensure any data loaded persists when the container is stopped.

    $ docker run -d -p 6379:6379 --mount type=bind,source=/host/path/to/save/data/to,target=/data redislabs/redisearch:latest

The easiest way to run the data loading script is with a [Python Virtual Environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/).
Once Python virtual environments is installed, you can create a virtual environment as follows

    $ virtualenv venv

All the script's dependencies are listed in the `requirements.txt` file, which can be used to bootstrap the virtual environment as follows

    $ . ./venv/bin/activate
    (venv) $ pip install -r requirements.txt

## Running

The script loads data into Redis from GFF files or a Chado (PostgreSQL) database.
The credentials for Redis and the different data sources can be set via command line flags or via environment variables.
The Redis credentials can be provided via the `REDIS_DB`, `REDIS_PASSWORD`, `REDIS_HOST`, and `REDIS_PORT` environment variables.
The GFF credits can be provided via the `GENUS`, `SPECIES`, `STRAIN`, `GENE_GFF_FILE`, `CHROMOSOME_GFF_FILE`, and `GFA_FILE` environment variables.
And the Chaddo (PostgreSQL) database credentials can be provided via the `POSTGRES_DATABASE`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT` environment variables.

The loading script can be run as follows

    (venv) $ ./load_redis.py

For more information about the script and additional commands and arguments, run

    (venv) $ ./load_redis.py --help
