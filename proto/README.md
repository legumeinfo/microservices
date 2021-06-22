This directory contains `.proto` files ([Protocol Buffers](https://developers.google.com/protocol-buffers)) that define structured data types that may be used by the microservices in this repository and the clients that interact with them.
Each `.proto` file is individually versioned (i.e. MAJOR.MINOR.PATCH) to allow microservices to use old and new versions of various data types simultaneously.
As such, each `.proto` file should be self contained and not import types from other `.proto` files, meaning related types should be contained within a single `.proto` file.
To support version differentiation across various languages, each `.proto` file should be placed in a subpath defined by its name and major version, and the package line in the file should use the same scheme.
For example, as long as the major version of the `gene.proto` file is 1 (e.g. 1.0.0, 1.2.3, 1.16.7, etc), its path in this repository should be

    proto/gene/v1/gene.proto

Similarly, as long as the major version of the `gene.proto` file is 1, the package line in the file should be

    prackage gcv.gene.v1

`.proto` files that define [gRPC services](https://grpc.io/) should be stored with their microservice (i.e. not in this directory) and also use their name and service's major version in their subpath and package line.
Additionally, the name portion of a microservice's `.proto` file subdirectory and package line should have `_service` appended to it to prevent collisions with `.proto` files defined in this directory.
For example, as long as the major version of the chromosome service is 1, the path to its `chromosome.proto` file in this repository should be

    chromosome/proto/chromosome_service/v1/chromosome.proto

Similarly, as long as the major version of the chromosome service is 1, the package line in its `.proto` file should be

    prackage gcv.chromosome_service.v1

The microservices themselves should not symlink or directly include `.proto` files from this directory or from other microservices.
Instead, the `git read-tree` command should be used to create versioned copies of the `.proto` files a microservice depends on in its `proto/` directory.
For example, major version 1 of the macro-synteny blocks service depends on major version 1 of the pairwise macro-synteny blocks service and major versino 1 the blocks data type.
`git read-tree` can be used to copy these specific versions into the macro-synteny blocks service's `proto/` directory as follows

  git read-tree --prefix=macro_synteny_blocks/proto/blocks -u proto/blocks@v1:proto/blocks 

should import each `.proto` file in a consistent, version aware way that I haven't settled on yet...
