# Genome Context Viewer macro-synteny blocks microservice

This directory contains the macro-synteny blocks microservice.
This microservice takes a chromosome as an ordered list of functional annotations and returns a set of synteny blocks computed on-demand from chromosome in the database.
The minimum number of matching annotations in a block and the maximum number of intermediate genes between any two matches in a block must also be provided.
Optionally, the maximum number of members in a family and target chromosomes can be provided.

## Setup

We assume you have already setup Redis with RediSearch and populated it with data from a PostgreSQL database configured with the Chado shema.
See the `../../database/README.md` file for instructions on how to do this.

The easiest way to run the microservice is with a [Python Virtual Environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/).
Once Python virtual environments is installed, you can create a virtual environment as follows

    $ virtualenv venv

All the microservice's dependencies are listed in the `requirements.txt` file, which can be used to bootstrap the virtual environment as follows

    $ . ./venv/bin/activate
    (venv) $ pip install -r requirements.txt

## Running

The microservice loads data from a RediSearch index and hosts an HTTP and a gRPC server.
The credentials for the microservice can be set via command line flags or via environment variables.
The RediSearch database credentials can be provided via the `REDIS_DB`, `REDIS_PASSWORD`, `REDIS_HOST`, and `REDIS_PORT` environment variables.
The HTTP server credentials can be provided via the `HTTP_HOST` and `HTTP_PORT` environment variables.
And the gRPC server credentials can be provided via the `GRPC_HOST` and `GRPC_PORT` environment variables.

Run the microservice as follows

    (venv) $ ./microservice.py

For more information about the microservice, run

    (venv) $ ./microservice.py --help

## Use

The microservice can be queried via HTTP POST or gRPC.

The default request URL is `localhost:8080/macro-synteny-blocks`.
The following is an example HTTP POST data

    {
      chromosome: [afunctionalannotation, anotherannotation, andsoon],
      matched: 20,
      intermediate: 5,
      mask: 50,
      targets: [achromosomename, anotherchromosomename, andsoon],
    }

See the `macrosyntenyblocks.proto` file and its auto-generated stubs for gRPC requests.
