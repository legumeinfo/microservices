# Linkouts Microservice

This directory contains linkout microservices, ie services primarily intended for generating links to other user-facing endpoints given some information like a gene id. For example, an application displaying genes from many species may wish to allow the user to obtain possible destinations that are species specific, and the gene linkout service would mediate this so that all applications can rely on the same logic and provide consistent user experience. 

## Setup

The easiest way to install the linkouts microservice is with Docker.

## Running

The easiest way to run the linkouts microservice is with docker compose. You will need to set the DATA environment variable used in the compose file to the root of a directory hierarchy containing README.\*.yml files with linkout specifications (e.g. by cloning the legumeinfo/datastore-metadata repo if you are working for the legume).

## Use

The microservice can be queried via HTTP POST or gRPC.

The default request URLs are :
- `localhost:8080/gene_linkouts`
- `localhost:8080/genomic_region_linkouts`
