This directory contains `.proto` files ([Protocol Buffers](https://developers.google.com/protocol-buffers)) that define structured data types that may be used by the microservices in this repository and the clients that interact with them.
Each `.proto` file is individually versioned to allow microservices to use old and new versions of various data types simultaneously.
As such, each `.proto` file should be self contained and not import types from other `.proto` files, meaning related types should be contained within a single `.proto` file.
Additionally, each `.proto` file should include its major version in its package line, e.g.

    prackage gcv.filename.v1

`.proto` files that define [gRPC services](https://grpc.io/) should be stored with their microservice (i.e. not in this directory) and use their service's major version in their package line.
The microservices themselves should not include `.proto` files from this directory during their build process, but rather, should import each `.proto` file in a consistent, version aware way that I haven't settled on yet...
