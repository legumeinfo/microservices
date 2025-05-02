# Legumeinfo Microservices
This repository contains microservices developed and maintained by the Legume Information System to support the [Legumeinfo website](https://legumeinfo.org/) as well as the various apps developed and maintained by the group.
Each subdirectory contains a different microservice, with the exception of the `proto/` directory, which contains [Protocol Buffers](https://developers.google.com/protocol-buffers) that define common data types used by one or more of the microservices.
See the `proto/` directory for more information about using these Protocol Buffers.

## Usage
Each microservice is distributed as a Docker image via the GitHub container registry.
Unless you are a developer, we recommend using these prebuilt images rather trying to compile and run microservices yourself.
Additionally, if you are using microservices that depend on other microservices, we especially recommend using a tool for deploying multi-container applications, such as [Docker Compose](https://docs.docker.com/compose/) or [Kubernetes](https://kubernetes.io/).

Some containers support [gRPC](https://grpc.io/).
If you wish to communicate with these containers from a Web client using gRPC Web, then you must use a proxy that supports gRPC Web request, such as [Envoy Proxy](https://www.envoyproxy.io/).

**See the [Genome Context Viewer Docker Compose repository](https://github.com/legumeinfo/gcv-docker-compose) for an example of deploying Legumeinfo microservices using Docker Compose, Envoy Proxy, and Traefik.**
The example configures microservices to communicate and supports gRPC Web requests.

## Development
Please so our [contribution guidelines](.github/CONTRIBUTING.md) before contributing to this repository.

See the directories of microservices you wish to compile manually for instructions on doing so.
Generally, we recommend still using a solution like Docker Compose to orchestrate container building and cross-talk, even during development.

### Pre-Commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to manage pre-commit hooks, such as code formatting.
These hooks are also applied to all PRs on GitHub.
To run the hooks locally before opening a PR (which we recommend), first install pre-commit:
```console
$ pip install pre-commit
$ pre-commit install
```
The hooks will then be applied every time you make a commit.

If you want to run the hooks manually (i.e. without having to commit), use the following command:
```console
$ pre-commit run --all-files
```
See the [pre-commit documentation](https://pre-commit.com/) for more details and use cases.

### Managing Dependencies

Generally, we use the `pip-compile` command from the [pip-tools package](https://github.com/jazzband/pip-tools/) to manage microservice dependencies.
See the [Managing Microservice Dependencies](https://github.com/legumeinfo/microservices/wiki/Managing-Microservice-Dependencies) page in this repo's Wiki for details.
