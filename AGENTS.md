# Working on the microservices

A monorepo of independently versioned Python microservices for the Legume Information
System. Most serve the Genome Context Viewer (GCV, `legumeinfo/gcv`) from a Redis Stack
database that `redis_loader` fills; each ships as a container image, `ghcr.io/legumeinfo/
microservices-<service>`, deployed with `legumeinfo/gcv-docker-compose`.

A service's gRPC API and published image are contracts with clients you can't see, most
of all the GCV frontend, which compiles its client stubs from tagged releases of these
`.proto` files. Change them compatibly, and version them deliberately.

## Map

| Service | Role | Transports | Calls |
| --- | --- | --- | --- |
| `genes` | gene objects by name | HTTP, gRPC | |
| `gene_search` | gene names like a query | HTTP, gRPC | |
| `chromosome` | a chromosome as an ordered list of genes | HTTP, gRPC | |
| `chromosome_region` | genes in a chromosome interval | HTTP, gRPC | |
| `chromosome_search` | chromosome names like a query | HTTP, gRPC | |
| `search` | GCV's search box: genes, chromosomes and regions | HTTP, gRPC | `gene_search`, `chromosome_search`, `chromosome_region` |
| `micro_synteny_search` | tracks with similar gene-family content | HTTP, gRPC | |
| `pairwise_macro_synteny_blocks` | synteny blocks between two chromosomes | HTTP, gRPC | |
| `macro_synteny_blocks` | synteny blocks against many targets | HTTP, gRPC | `pairwise_macro_synteny_blocks`, `chromosome`, `genes` |
| `macro_synteny_paf` | genome-to-genome blocks as PAF or JSON, cached in Redis | HTTP, gRPC | `macro_synteny_blocks`, `chromosome`, `genes` |
| `redis_loader` | CLI that loads Redis from GFF3 or Chado | none | |
| `dscensor` | data for the DSCensor web app | HTTP | |
| `ds_utilities` | sequence bytes from indexed Data Store files | HTTP | |
| `linkouts` | gene and region link-outs | HTTP | |

The Redis schema (`chromosome:` and `gene:` documents, the `chromosomeIdx` and `geneIdx`
RediSearch indexes) is on the wiki's Redis Schema page; `redis_loader/redis_loader/
loaders/redisearch.py` creates it, and every reader depends on it.

## Service layout

```
<service>/
  Dockerfile           context is this directory alone; CI builds it on a release tag
  pyproject.toml       Hatchling; version read from <service>/__init__.py
  requirements.txt     pip-compile lock, installed before the package
  README.md, LICENSE
  proto/               gRPC services only: this service's API and vendored data types
  <service>/
    __init__.py        __version__
    __main__.py        argparse (EnvArg) and the uvloop event loop
    http_server.py     aiohttp routes; transport only
    grpc_server.py     servicers; transport only
    grpc_client.py     outbound gRPC, for services that call others
    request_handler.py domain logic; imports neither aiohttp nor grpc
    proto/__init__.py  puts the generated modules on sys.path (see below)
```

- **Keep the split.** `__main__.py` knows the CLI and the loop, the servers know their
  transport, `request_handler.py` knows the domain. HTTP and gRPC share one
  `RequestHandler`.
- **Flags fall back to environment variables** through the `EnvArg` action in each
  `__main__.py`: `HTTP_HOST`/`HTTP_PORT` (default `localhost:8080`), `GRPC_HOST`/
  `GRPC_PORT` (`[::]:8081`), `REDIS_HOST`/`REDIS_PORT`/`REDIS_DB`/`REDIS_PASSWORD`, and a
  peer's address as `<PEER>_ADDR` (`GENES_ADDR`, `PAIRWISE_ADDR`, ...). Copy a sibling's
  `__main__.py` rather than inventing flags.
- **Import banners.** Modules group imports under `# Python`, `# dependencies` and
  `# module` comments.
- **Stdlib `logging`, never `print`.** Default level `WARNING`.

## Protocol Buffers and builds

The wiki's Protocol Buffers and Tagging Releases pages are the policy; in short:

- **Data types** (`block`, `gene`, `region`, `track`) live in the top-level `proto/`, each
  versioned on its own and tagged `proto-<type>@vX.Y.Z`. **A service's API** lives in
  `<service>/proto/<name>_service/v<major>/`, versioned with the service.
- **Services vendor their dependencies.** A service's `proto/` holds copies of the
  data types and peer APIs it uses, taken from tagged releases with `git read-tree`, never
  symlinks or edits in place. Change a data type at the top level, tag it, then refresh
  the copies.
- **Change protos compatibly**: add fields with new numbers, never renumber, retype or
  reuse one. The major version is in the path (`v1/`) and the package line, so a breaking
  change is a new directory, not an edit.
- **Generated stubs are never committed** (`*_pb2.py`, `*_pb2_grpc.py` are ignored). The
  Dockerfile generates them into the package before installing it:

  ```sh
  python3 -m grpc_tools.protoc --proto_path=proto \
    --python_out=<service>/proto --grpc_python_out=<service>/proto \
    $(find proto -name '*.proto')
  pip install --no-deps .
  ```

  Hatchling ships them through `artifacts` in `pyproject.toml`. For local work, run the
  same two commands after `pip install -r requirements.txt` (the README says so too).
- **protoc's version is pinned to the protobuf runtime.** grpcio-tools is the `codegen`
  extra in `pyproject.toml` and locked in `requirements.txt`. Its generated code requires a
  `protobuf` at least as new as itself, so upgrade grpcio-tools and protobuf together. Each
  gRPC Dockerfile imports `<service>.grpc_server` at build time, so a mismatch fails the
  build rather than the container.
- **Generated modules import each other by flat names** (`from block.v1 import
  block_pb2`), so code imports `<service>.proto` first, which appends its directory to
  `sys.path`, between `# isort: off` and `# isort: on`. Tests do the same.

## Dependencies

`requirements.txt` is a pip-compile lock of `pyproject.toml`; its header records the
command. Regenerate it in the service directory:

```sh
pip-compile --extra=codegen --no-emit-index-url --output-file=requirements.txt pyproject.toml  # gRPC services
pip-compile --no-emit-index-url --output-file=requirements.txt pyproject.toml                  # the rest
```

pip-compile keeps existing pins unless asked to `--upgrade`; review the pin diff either
way. `ds_utilities`' lock comes from a `requirements.in` that isn't in the repository; leave
it to its owner.

## Releases

- Each service is versioned in `<service>/__init__.py` (semver). Bump it in the PR that
  changes the service: patch for fixes and packaging, minor for compatible features
  (new fields, new RPCs), major only with a new `v<major>/` proto path.
- A tag `<service>@vX.Y.Z` on `main` builds and pushes the image
  (`.github/workflows/build-push-on-tag.yml`), tagged `X.Y.Z`, `X.Y`, `X` and `latest`. A
  new service must be added to that workflow's tag list, or its tags build nothing.
- Tags are pushed by maintainers after merge, never from a PR branch, and never moved.

## Checks

```sh
pre-commit run --all-files     # isort (black profile), black, flake8 at 88 columns
```

- **Unit tests** exist for `macro_synteny_blocks`, `macro_synteny_paf` and
  `pairwise_macro_synteny_blocks` (pytest, in `tests/`). Run them against the installed
  package: install the requirements and `requirements-test.txt`, generate the stubs,
  `pip install --no-deps .`, then `pytest` from the service directory. Tests that need
  Redis Stack (`geneIdx`) create the index themselves and skip when no Redis is reachable;
  `./run-tests.sh` runs everything in Docker beside a `gcv-docker-compose` checkout.
- **Build what you change.** A packaging or proto change isn't done until the image
  builds from a clean context (`docker build <service>`) or the Dockerfile's steps pass
  in a fresh virtualenv, ending with the import of `<service>.grpc_server`.
- Exercise HTTP endpoints with `curl` against a running service; each README has
  examples.
- Test mocks of gRPC messages use the generated classes (`block_pb2.Block(...)`), not
  namedtuples, so tests break when the proto changes rather than drifting from it.

## Writing

- **Comments are terse and explain why.** Describe the code as it is now: no history
  ("used to", "previously", "fixed"), and no issue or PR numbers unless the condition is
  still true. History belongs in commit messages.
- **Commit messages** say what changed and why, and name every service whose image
  changes.

## Known deviations

New code follows the rules above; these existing spots don't yet:

| Where | Deviation |
| --- | --- |
| 12 services | HTTP flags are `--hhost`/`--hport`, not `--host`/`--port` |
| `ds_utilities`, `linkouts` | `web.run_app` starts its own event loop, bypassing `__main__.py`'s signal handling |
| `search`, `macro_synteny_blocks`, `macro_synteny_paf` | `grpc_client.py` opens a channel per call and never closes it; use `async with aio.insecure_channel(...)` |
| `ds_utilities` | reads `ds_utilities.yaml` from its package, but the spec lives in `ds_utilities/openapi/`, outside it |
| `dscensor` | its OpenAPI spec is documentation only; routes are registered by hand |

Remove a row when you fix it.

## Related repositories

- `legumeinfo/gcv`: the frontend; `dep/legumeinfo-microservices` pins the service and proto
  tags it compiles client stubs from.
- `legumeinfo/gcv-docker-compose`: runs the services, Envoy (gRPC-Web) and Traefik, with
  these images (production) or this repository as a submodule (development).
