# Macro-Synteny PAF Microservice

This directory contains the macro-synteny-paf microservice.
This microservice takes two genomes (1/query and 2/target), plus fields that describe their chromosome names, and returns a set of synteny blocks in PAF format.
The minimum number of matching annotations in a block and the maximum number of intermediate genes between any two matches in a block must also be provided.

## Setup

We assume you have already setup Redis with RediSearch and populated it with data from a PostgreSQL database configured with the Chado schema.
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

The microservice can be queried via HTTP GET or [TODO] gRPC.

The default request URL is `localhost:8080/macro-synteny-paf`.

The following is an example HTTP GET URL:

    localhost:8080/macro-synteny-paf?genome1=aradu.V14167.gnm1&chrpfx1=Aradu.A&chrdgt1=2&nchr1=10&genome2=arahy.Tifrunner.gnm1&chrpfx2=Arahy.&chrdgt2=2&nchr2=20&matched=10&intermediate=5&mask=20

where

    genome[1|2]: genome name (1 for query genome, 2 for target genome)
    chrpfx[1|2]: prefix of its chromosome names
    chrdgt[1|2]: number of digits for the chromosome number (in order to automatically pad with leading zeros when necessary)
    nchr[1|2]: number of chromosomes
      (This assumes that the full-yuck chromosome name is <genome>.<chrpfx><chromosome_number>, e.g. aradu.V14167.gnm1.Aradu.A05)
    matched: minimum number of matching annotations in a block
    intermediate: maximum number of intermediate genes between any two matches in a block
    mask: (optional)

See the `macrosyntenypaf.proto` file and its auto-generated stubs for gRPC requests.
