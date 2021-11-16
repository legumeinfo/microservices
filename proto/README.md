# Protocol Buffers

This directory contains `.proto` files ([Protocol Buffers](https://developers.google.com/protocol-buffers)) that define structured data types that may be used by the microservices in this repository and the clients that interact with them.
Each `.proto` file is individually versioned (i.e. MAJOR.MINOR.PATCH) to allow microservices to use old and new versions of various data types simultaneously.
As such, each `.proto` file should be self contained and not import types from other `.proto` files, meaning related types should be contained within a single `.proto` file.
To support version differentiation across various languages, each `.proto` file should be placed in a subpath defined by its name and major version, and the package line in the file should use the same scheme but have the GitHub organization and repository as the prefix.
For example, as long as the major version of the `gene.proto` file is 1 (e.g. 1.0.0, 1.2.3, 1.16.7, etc), its path in this repository should be

    proto/gene/v1/gene.proto

Similarly, as long as the major version of the `gene.proto` file is 1, the package line in the file should be

    package legumeinfo.microservices.gene.v1

`.proto` files that define [gRPC services](https://grpc.io/) should be stored with their microservice (i.e. not in this directory) and also use their name and service's major version in their subpath and package line.
Additionally, the name portion of a microservice's `.proto` file subdirectory and package line should have `_service` appended to it to prevent collisions with `.proto` files defined in this directory.
As with `.proto` files located in this directory, microservice `.proto` files' packages lines should also have the GitHub organization and repository as the prefix.
For example, as long as the major version of the micro-synteny search service is 1, the path to its `microsyntenysearch.proto` file in this repository should be

    micro_synteny_search/proto/microsyntenysearch_service/v1/microsyntenysearch.proto

Similarly, as long as the major version of the micro-synteny search service is 1, the package line in its `.proto` file should be

    package legumeinfo.microservices.microsyntenysearch_service.v1

The microservices themselves should not symlink, copy, or directly include `.proto` files from this directory or from other microservices.
Instead, the `git read-tree` command should be used to create versioned copies of the `.proto` files a microservice depends on in its `proto/` directory.
For example, major version 1 of the macro-synteny blocks service depends on major version 1 of the pairwise macro-synteny blocks service and major version 1 of the block data type.
`git read-tree` can be used to copy these specific versions into the macro-synteny blocks service's `proto/` directory as follows

    $ git read-tree --prefix=macro_synteny_blocks/proto/pairwisemacrosynteny_service -u pairwise_macro_synteny_blocks@v1:pairwise_macro_synteny_blocks/proto/pairwisemacrosyntenyblocks_service
    $ git read-tree --prefix=macro_synteny_blocks/proto/block -u proto/blocks@v1:proto/block 

Notice that this preserves the previously described subpaths of each `.proto` file.
This is intentional to preserve version differentiation across languages and so dependencies are correct when compiling with `protoc`.

This technique ensures that a microservice is built against the specific versions of the `.proto` files it depends on.
It also allows old versions of `.proto` files to be removed from the repository but still remain available as dependency targets.
