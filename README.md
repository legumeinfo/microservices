# GCV Microservices
This repository contains a microservices implementation of the
[Genome Context Viewer](https://github.com/legumeinfo/gcv/)
[services API](https://github.com/legumeinfo/gcv/wiki/Services-API-v2).


## Setup
Due to intercommunication between microservices, the need for a proxy server to
serve gRPC Web requests, and the total number of microservices, we highly
recommend using the provided Docker Compose files to setup and run the
microservices.
See each microservice's directory for instructions on how to setup that
specific microservice without Docker.

### Docker Compose
Use the following command to setup and run the microservices locally for
development

    $ docker-compose up

The services can be brought down locally as follows

    $ docker-compose down

Use the following command to setup and run the microservices in production

    $ docker-compose -f ./docker-compose.prod.yml up

The services can be brought down in production with

    $ docker-compose -f ./docker-compose.prod.yml up

Refer to the [Docker Compose documentation](https://docs.docker.com/compose/)
for further information and how to use Docker Compose.


## Loading Data
The microservices depend on a [Redis](https://redis.io/) database; see the
[Wiki](https://github.com/legumeinfo/gcv-microservices/wiki/Redis-Schema)
for a description of the schema.
Data can be loaded into the Redis database from a
[Chado](http://gmod.org/wiki/Chado_-_Getting_Started) database (PostgreSQL) or
from [GFF](https://en.wikipedia.org/wiki/General_feature_format) and
[FASTA](https://en.wikipedia.org/wiki/FASTA_format) files; see the `database/`
directory for details.
