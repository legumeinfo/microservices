# Microservices: architecture and engineering conventions

**Audience.** Engineers (human and AI) contributing to this monorepo. Read this before adding a new service or making cross-cutting changes. Skim it before non-trivial edits to an existing one.

**Status of this document.** It describes the *target* conventions — what new code MUST do and what existing code SHOULD eventually look like. Where the current tree disagrees with the spec, the inconsistencies are catalogued in the "Known deviations" section at the end so the gap is explicit, not folkloric.

**Normative language.**
- **MUST / MUST NOT** — required. Code that violates this should not merge.
- **SHOULD / SHOULD NOT** — strongly recommended. Deviations need rationale in the PR description.
- **MAY** — discretionary; no policy attached.
- **AVOID** — pattern present in the tree that is now considered a mistake. Don't propagate it.

**Conventions for this document.**
- In prose, cross-reference a section by **name as well as number** ("see [§ 3.1](#31-the-three-module-split), *The three-module split*"). Section *numbers* are navigational aids and may shift when the document is reorganized; if you renumber, update the references you moved. The *Quick map* below and the table of contents are lookup indexes — numbers there are fine.

## Quick map

Jump to what you need:

| I want to… | Start at |
|---|---|
| Add a new service | [§ 15](#15-adding-a-new-service-checklist) (checklist) → [§ 3](#3-service-layout) (layout) |
| Understand the module split | [§ 3.1](#31-the-three-module-split); orchestration services [§ 3.2](#32-orchestration-service-layout-the-clientspy-boundary) |
| Fix a failing gRPC image build | [§ 9.2](#92-build-robustness-must-read-before-building-a-grpc-service-image) (build robustness) |
| Get the JSON error-response shape right | [§ 7.4](#74-error-response-shape) |
| Register HTTP routes (spec-driven vs. manual) | [§ 7.3](#73-route-registration) |
| Handle FASTA / GFF / coordinates / strand | [§ 10](#10-file-io-for-genomics-data) |
| Package a service (setup.py / MANIFEST / where contracts live) | [§ 4](#4-packaging) |
| Run a service under compose | [§ 13.2](#132-three-file-compose-pattern) |
| See what's currently non-conformant | [§ 17](#17-known-deviations-from-this-spec) (known deviations) |

---

## 1. Overview

This repository hosts a family of Python microservices for the Legume Information System (LIS) and adjacent AgBio databases. They sit between the LIS datastore (FASTA / GFF / BED / VCF / BAM / Redis) and the consumer-facing UI components in the [`web-components`](https://github.com/legumeinfo/web-components) repo.

Three service shapes exist:

1. **File-format proxy services.** Wrap `pysam` over remote indexed files in the LIS datastore. Examples: `ds_utilities`, `linkouts`. HTTP-only, generally stateless. These MUST stay dumb: no calls to sibling services, no domain logic (e.g. `ds_utilities` is strand-agnostic — see [§ 10.4](#104-strand-and-coordinate-semantics)).
2. **Query services.** Backed by Redis with the RediSearch module (built by `redis_loader`) or by a static catalog. Examples: `genes`, `gene_search`, `chromosome`, `chromosome_search`, `chromosome_region`, `micro_synteny_search`, `macro_synteny_blocks`, `pairwise_macro_synteny_blocks`, `search`, `dscensor`. Most expose both HTTP and gRPC; `dscensor` is the exception — it is HTTP-only (manual `aiohttp` routing), backed by an autocontent digraph rather than Redis, and has no `proto/` or gRPC server.
3. **Orchestration services.** Own no datastore of their own; they compose other services into a higher-level operation, adding a `clients.py` transport-out module ([§ 3.2](#32-orchestration-service-layout-the-clientspy-boundary)). Example: `sequences` resolves gene-ID → FASTA by calling `genes` (gRPC, for coordinates/strand), `dscensor` (HTTP, for file URLs), and `ds_utilities` (HTTP, for bytes), and owns the domain logic the leaf services deliberately don't (reverse-complement, flank math, FASTA assembly). Dependencies MUST point downward (orchestration → query/proxy), never the reverse, and an orchestration endpoint's failure MUST be isolated to that endpoint. They are HTTP-only (a FASTA/file response has no natural gRPC analog) and stateless apart from the upstream service addresses they're configured with.

All shapes follow the same packaging / CLI / asyncio / linting conventions detailed below.

---

## 2. Repository layout

```
microservices/
├── ARCHITECTURE.md          ← this file
├── README.md
├── LICENSE
├── .gitignore               ← shared gitignore for all services
├── .pre-commit-config.yaml  ← shared lint/format hooks
├── data/                    ← shared fixture data (e.g. dscensor autocontent)
├── tests/                   ← cross-service integration fixtures
├── proto/                   ← SHARED protobuf message types (copied per-service)
├── openapi/                 ← README only; specs live per-service (§ 4.4)
└── <service-name>/          ← one directory per service (see § 3)

Note on contract-file locations (see § 4.4, § 9.1):
  - OpenAPI YAML lives INSIDE the package: `<service>/<service>/openapi/...`
  - `.proto` SOURCES live at the service root: `<service>/proto/...`
  - generated `*_pb2*.py` are built INTO the package (`<service>/<service>/proto/`)
    and are not committed.
None of these live at the repo *root*.
```

### 2.1 New top-level directories

A new top-level directory MUST be one of:
- A service (per [§ 3](#3-service-layout))
- `data/` content (fixtures, never service-specific runtime state)
- `tests/` (cross-service fixtures)
- The repo-root `proto/` — the canonical home of **shared** protobuf *message* types (`gene/v1/gene.proto`, `block/v1/block.proto`, `track/v1/region.proto`, …) that multiple gRPC services reuse. Each consuming service keeps a copy of the message protos it needs under its own `<svc>/proto/` (alongside its service-specific `*_service` proto) and generates stubs from that copy ([§ 9.1](#91-proto-sources-and-the-uncommitted-generated-stubs)); the repo-root `proto/` is the source those copies track. The repo-root `openapi/` holds only a README — per-service specs live in the package ([§ 4.4](#44-where-contract-files-live)).
- Tooling shared across services (e.g. `.github/`, dotfiles)

Anything else (deploys, docs subsites, marketing pages) belongs in a sibling repo.

---

## 3. Service layout

A service named `myservice` MUST conform to this tree:

```
myservice/
├── Dockerfile               ← REQUIRED
├── INSTALL                  ← REQUIRED (build-time copy target; can be empty)
├── LICENSE                  ← REQUIRED — Apache-2.0
├── MANIFEST.in              ← REQUIRED — see § 4
├── README.md                ← REQUIRED — usage + curl examples
├── requirements.txt         ← REQUIRED — pip-compile output of requirements.in
├── requirements.in          ← SHOULD — abstract dependency list
├── setup.cfg                ← REQUIRED — see § 4
├── setup.py                 ← REQUIRED — one-liner, or BuildProtos variant for gRPC (§ 4.1)
├── compose.yaml             ← MAY (services intended for docker deployment)
├── compose.dev.yaml         ← paired with compose.yaml
├── compose.prod.yaml        ← paired with compose.yaml
├── test.py                  ← SHOULD — integration tests (live HTTP)
├── test_<unit>.py           ← MAY — additional unit-test modules
└── myservice/                       ← the Python package
    ├── __init__.py                  ← REQUIRED — exports `__version__`
    ├── __main__.py                  ← REQUIRED — argparse + uvloop entry point
    ├── http_server.py               ← REQUIRED (HTTP-exposing services)
    ├── grpc_server.py               ← REQUIRED (gRPC-exposing services)
    ├── request_handler.py           ← REQUIRED — business logic, transport-agnostic
    └── openapi/myservice/v1/        ← OpenAPI YAML (if applicable, see § 4.4)
        └── myservice.yaml
```

A service MUST NOT keep generated artifacts (built YAML copies, compiled protos in the package dir, etc.) under source control. Build at install time via `setup.py` / `MANIFEST.in`.

### 3.1 The three-module split

The split between `__main__.py`, `http_server.py` / `grpc_server.py`, and `request_handler.py` is load-bearing. New code MUST preserve it:

- `__main__.py` knows the CLI and the event loop. Nothing else.
- `http_server.py` / `grpc_server.py` know transport (routes, CORS, protobuf services). They MUST NOT contain business logic.
- `request_handler.py` knows the domain. It MUST NOT import `aiohttp`, `grpc`, or other transport libraries. Its functions are normal Python — sync where possible, async only when they actually `await` something.

This makes the same `request_handler` callable from a script, a test, both transports, or a future transport without rewrites.

### 3.2 Orchestration-service layout (the `clients.py` boundary)

Orchestration services ([§ 1](#1-overview), shape 3 — currently only `sequences`) add one module to the split: **`clients.py`**, the *transport-out* boundary. Because an orchestration service's whole job is calling siblings, `request_handler.py` would otherwise have to import `aiohttp`/`grpc` and violate [§ 3.1](#31-the-three-module-split). Instead, every outbound call (gRPC stub calls, `aiohttp` requests, the `aiohttp.ClientSession` factory) lives in `clients.py`, and `request_handler.py` imports *that* — never the transport library directly. This mirrors how `search` (a query service that fans out to other gRPC services) isolates its outbound gRPC in `grpc_client.py`.

```
sequences/
└── sequences/
    ├── __init__.py          ← __version__
    ├── __main__.py          ← CLI (upstream addresses) + uvloop
    ├── http_server.py       ← routes (spec-driven, § 7.3), no business logic
    ├── request_handler.py   ← orchestration: fan-out, fail-whole-request,
    │                          coordinate math; imports clients.py, never
    │                          aiohttp/grpc directly
    ├── clients.py           ← transport-out: gRPC stub + HTTP wrappers +
    │                          make_session(); maps upstream failures to a
    │                          domain ServiceError(status=...)
    ├── fasta.py             ← pure, pysam-free helpers (revcomp, flank math,
    │                          FASTA assembly); unit-tested in isolation
    └── openapi/...          ← contract (loaded; § 7.3, § 8)
```

Rules specific to this shape:

- `request_handler.py` MUST NOT import `aiohttp` or `grpc`; it calls `clients.py` helpers (including a `make_session()` factory) so the [§ 3.1](#31-the-three-module-split) guarantee holds.
- `clients.py` MUST translate every upstream failure into a domain exception carrying an HTTP-ish `status` (see [§ 7.4](#74-error-response-shape)) — including transport errors. For HTTP siblings, wrap calls in `try/except aiohttp.ClientError` and re-raise as `ServiceError(..., status=502)`; otherwise an unreachable sibling surfaces as a raw aiohttp traceback → HTTP 500 instead of a clean 502. For the gRPC sibling, catch around the stub call.
- The request handler opens **one** `aiohttp.ClientSession` per request (via `make_session()`) and threads it through the fan-out, so the batch's N fetches reuse one connection pool. Per-call `aiohttp.ClientSession()` creation is an AVOID.
- Fan out independent upstream work with `asyncio.gather`, preserving input order, and **fail the whole request** if any element fails (no partial assembly). Batchable upstreams MUST be called once for the whole batch (e.g. `sequences` resolves all gene coordinates in a single `genes` gRPC call, and resolves `dscensor` file URLs once per distinct annotation prefix, not once per gene).

---

## 4. Packaging

### 4.1 `setup.py`

For services that do **not** generate code at build time (HTTP-only services — `ds_utilities`, `dscensor`, `linkouts`), `setup.py` MUST be exactly:

```python
#!/usr/bin/env python
import setuptools

setuptools.setup()
```

AVOID running side effects in `setup.py` (file copies, network calls). Put all packaging metadata in `setup.cfg` and shipped-file selection in `MANIFEST.in`.

**Exception — protobuf codegen (gRPC servers and clients).** Services that ship or consume gRPC (`genes`, `gene_search`, `search`, `chromosome`, `chromosome_region`, `chromosome_search`, `micro_synteny_search`, `macro_synteny_blocks`, `pairwise_macro_synteny_blocks`, and the orchestration client `sequences`) MUST generate their `*_pb2.py` / `*_pb2_grpc.py` stubs at build time, because the stubs are deliberately not committed ([§ 9](#9-grpc-conventions)). These services use a custom `setup.py` that subclasses `build_py` to run a `BuildProtos` command (in `<svc>/<svc>/commands.py`) after the normal build:

```python
#!/usr/bin/env python
import setuptools
from setuptools.command.build_py import build_py

from <svc> import commands   # BuildProtos lives here

class BuildPy(build_py):
    def run(self):
        build_py.run(self)
        self.run_command("build_proto")

setuptools.setup(
    package_dir={"": "."},
    setup_requires=("grpcio-tools",),
    cmdclass={"build_proto": commands.BuildProtos, "build_py": BuildPy},
)
```

This is the *only* sanctioned codegen-in-`setup.py`. It is still subject to the [§ 9](#9-grpc-conventions) build-robustness rules (importlib.resources, `--no-build-isolation` in the Dockerfile, gencode/runtime version pinning) — read those before copying this pattern.

### 4.2 `setup.cfg`

REQUIRED sections, in this order:

```ini
[metadata]
name = myservice
version = attr: myservice.__version__
description = A Microservice that ...
long_description = file: README.md
url = https://github.com/legumeinfo/microservices
author = Your Name
author_email = you@ncgr.org
keywords = genomics, bioinformatics, microservices
license = Apache-2.0
classifiers =
    Development Status :: 4 - Beta
    Environment :: Console
    Intended Audience :: Science/Research
    Topic :: Scientific/Engineering :: Bio-Informatics
    License :: OSI Approved :: Apache Software License
    Operating System :: OS Independent
    Programming Language :: Python :: 3
    Programming Language :: Python :: 3 :: Only

[options]
packages = find:
python_requires = >=3.5,<4
install_requires =
    aiohttp          # HTTP-exposing services
    aiohttp-cors     # HTTP-exposing services
    uvloop
    # pyyaml         # ONLY services that load a YAML at runtime (OpenAPI:
    #                # dscensor, ds_utilities, linkouts, sequences). genes and
    #                # the pure-gRPC services omit it.
    # grpcio         # gRPC servers and clients
    # grpcio-tools   # gRPC servers and clients (also a build dep — see § 9)
    # pysam          # file-format-proxy services
    # ...service-specific deps

[options.entry_points]
console_scripts =
    myservice = myservice.__main__:main
```

`install_requires` is per-service, not a fixed list — only `uvloop` (and `aiohttp`/`aiohttp-cors` for HTTP services) is universal. `python_requires` floors vary across the tree (`>=3.5`, `>=3.7`, `>=3.9`); they are cosmetic — the real interpreter is pinned at 3.13 ([§ 12](#12-linting-formatting-pre-commit)), so new services SHOULD use `>=3.9,<4`.

The `console_scripts` entry MUST match the package name. It is wrong in **most** existing services (they register the binary as `chromosome` — see [§ 17](#17-known-deviations-from-this-spec)), which is exactly why every Dockerfile invokes `python3 -u -m <svc>` instead of the bare console-script name ([§ 13.1](#131-dockerfile)). New services MUST get this right.

### 4.3 `MANIFEST.in`

Standard preamble plus one `recursive-include` per shipped non-Python tree:

```
include INSTALL
include LICENSE
include MANIFEST.in
include *.md
recursive-include openapi/ *.yaml    # if the service uses OpenAPI
recursive-include proto/ *.proto     # if the service uses gRPC
```

The package directory itself (`myservice/`) is picked up automatically via `packages = find:` in `setup.cfg`. Do not list it in MANIFEST.

### 4.4 Where contract files live

Contract files MUST live **inside the package directory** so they ship with the wheel and are reachable from a non-editable install. Path lookups MUST use `importlib.resources`, never `Path(__file__).parent.parent`.

| Contract type | Source path | Loaded at runtime via |
|---|---|---|
| OpenAPI | `<svc>/<svc>/openapi/<svc>/v1/<svc>.yaml` | `importlib.resources.files("<svc>") / "openapi/<svc>/v1/<svc>.yaml"` |
| Protobuf | `<svc>/proto/<svc>/v1/<svc>.proto` | generated `_pb2.py` / `_pb2_grpc.py` shipped under the package |

One source of truth, period. AVOID:

- Storing the OpenAPI YAML *outside* the package directory (e.g. at `<svc>/openapi/`). `pip install .` won't put it into site-packages, so a non-editable / Docker install fails at startup with `FileNotFoundError` the moment the service tries to load the spec.
- Copying YAML or generated code into the package directory at install time via `shutil.copy2` in `setup.py`. Generates drift between the working tree and the install target and pollutes version control with a copy that's supposed to be derived.
- Computing the path via `Path(__file__).parent.parent / "openapi/..."` — works only in editable installs where the project root is still on disk.

The right pattern, copy-paste:

```python
# http_server.py
from importlib import resources

async def run_http_server(host, port, handler):
    api_path = resources.files("<svc>") / "openapi/<svc>/v1/<svc>.yaml"
    # load the spec from the Traversable:
    #   with api_path.open("r") as f:
    #       spec = yaml.safe_load(f)
    # (if a library needs a filesystem path string instead: api_path = str(api_path))
    ...
```

```ini
# setup.cfg
[options]
include_package_data = true
packages = find:

[options.package_data]
<svc> = openapi/<svc>/v1/*.yaml
```

```
# MANIFEST.in
recursive-include <svc>/openapi/ *.yaml
```

```
# Dockerfile — only the package dir needs to be copied; openapi/ rides along
COPY <svc>/ ./<svc>/
# do NOT add `COPY openapi/ ./openapi/` — it doesn't ship the spec into the package
```

---

## 5. CLI and environment

### 5.1 Standard flags

Every service MUST expose the following flags via `argparse`, in this order, with the names and defaults below:

| Flag | Env var | Type | Default | Purpose |
|---|---|---|---|---|
| `--version` | — | (action) | — | Print version, exit |
| `--log-level` | `LOG_LEVEL` | str (enum) | `WARNING` | One of `DEBUG/INFO/WARNING/ERROR/CRITICAL` |
| `--log-file` | `LOG_FILE` | str | unset | If set, log to file instead of stderr |
| `--host` | `HTTP_HOST` | str | `127.0.0.1` | HTTP bind host |
| `--port` | `HTTP_PORT` | int | `8080` | HTTP bind port |

Services that also expose gRPC MUST add `--ghost` / `--gport` (env: `GRPC_HOST` / `GRPC_PORT`) and `--no-http` / `--no-grpc` toggles.

Service-specific flags follow the standard ones. Each flag MUST be readable from both CLI and environment via the `EnvArg` pattern (next section).

AVOID `--hhost` / `--hport`. They exist in older services as a historical accident; new code uses `--host` / `--port`.

### 5.2 The `EnvArg` pattern

Argparse alone has no environment-variable affordance. Every service uses the same `EnvArg` action so flags fall back to env vars cleanly. Copy verbatim:

```python
class EnvArg(argparse.Action):
    """argparse.Action that falls back to an environment variable."""

    def __init__(self, envvar, required=False, default=None, **kwargs):
        if envvar in os.environ:
            default = os.environ[envvar]
        if required and default is not None:
            required = False
        super().__init__(default=default, required=required, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
```

Use it like:

```python
parser.add_argument(
    "--host",
    action=EnvArg,
    envvar="HTTP_HOST",
    type=str,
    default="127.0.0.1",
    help="The HTTP server host (also: HTTP_HOST env var).",
)
```

Resolution priority is `CLI > env var > default`.

### 5.3 Service-specific environment variables

Service-specific env vars MUST be documented in the README and prefixed by purpose, not service name. Examples already in the tree:
- `ALLOWED_URLS` (ds_utilities, comma-separated URL prefix allowlist)
- `NODES` (dscensor, autocontent directory)
- `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` / `REDIS_PASSWORD` (Redis-backed services)

---

## 6. asyncio and the event loop

Every service MUST use the same loop wiring in `__main__.py`. Copy this template:

```python
import asyncio
import logging
import os
import signal

import uvloop

from myservice.http_server import run_http_server
from myservice.request_handler import RequestHandler


async def shutdown(loop, signal=None):
    if signal:
        logging.info(f"Received exit signal {signal.name}")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


def handleException(loop, context):
    msg = context.get("exception", context["message"])
    logging.critical(f"Caught exception: {msg}")
    asyncio.create_task(shutdown(loop))


def main():
    args = parseArgs()
    # ...logging setup elided...

    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)

    for s in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            s, lambda s=s: loop.create_task(shutdown(loop, signal=s))
        )
    loop.set_exception_handler(handleException)

    try:
        handler = RequestHandler(...)
        if not getattr(args, "no_http", False):
            loop.create_task(run_http_server(args.host, args.port, handler))
        if not getattr(args, "no_grpc", False):  # gRPC services only
            loop.create_task(run_grpc_server(args.ghost, args.gport, handler))
        loop.run_forever()
    except Exception as e:
        loop.call_exception_handler({"exception": e, "message": str(e)})
    finally:
        loop.close()


if __name__ == "__main__":
    main()
```

Specifically:

- MUST use `uvloop.new_event_loop()` — the codebase standardizes on it for performance, and consistent loop semantics matter for the signal/shutdown logic.
- MUST install SIGHUP/SIGTERM/SIGINT handlers that schedule `shutdown(loop, signal=s)` so containers can be stopped cleanly.
- MUST schedule transport servers via `loop.create_task(...)` and then `loop.run_forever()`. AVOID `web.run_app(app)` — it spawns its own event loop and ignores the surrounding signal/exception handlers, leaving them as dead code.

### 6.1 Never block the event loop

A synchronous call that does real I/O or CPU work blocks the *entire* loop — every other in-flight request stalls until it returns. The offender in this codebase is `pysam`: its calls are synchronous C, and opening a remote file is dominated by HTTPS round-trips (seconds). An HTTP handler that calls `pysam` inline serializes all concurrent requests (measured: 6 concurrent FASTA fetches took ~6× one fetch).

Services that make blocking calls from an async handler MUST offload them to a thread pool via `loop.run_in_executor(...)`. This is safe and effective here because `pysam`/htslib **release the GIL during I/O**, so threads run genuinely concurrently (measured: 12 concurrent fetches ~10× faster on a 12-thread pool). The full pattern — a bounded pool, where it's created, and the `request_handler` thread-safety it requires — is in [§ 10.5](#105-offloading-pysam-to-a-thread-pool).

Background maintenance loops (periodic sweeps, cache eviction) follow the same rule: schedule them with `loop.create_task(...)` and run their blocking parts in the executor too (see `ds_utilities`' index-cache pruner, [§ 10.6](#106-local-fasta-index-cache)).

---

## 7. HTTP server

Each HTTP-exposing service has a `http_server.py` whose entry point is:

```python
async def run_http_server(host: str, port: int, handler) -> None:
    ...
```

It MUST:

1. Build the `aiohttp.web.Application` and store the handler under `app["handler"]`.
2. Register CORS via `aiohttp_cors` with permissive defaults (see [§ 7.2](#72-cors)).
3. Wire routes (manually or from OpenAPI, see [§ 7.3](#73-route-registration)).
4. Start via `AppRunner` + `TCPSite`:

```python
runner = web.AppRunner(app)
await runner.setup()
site = web.TCPSite(runner, host, port)
await site.start()
```

It MUST NOT call `web.run_app(app)`. That bypasses the parent event loop.

### 7.1 The "handler" abstraction

Handlers live in `request_handler.py` and accept primitive Python types only — no `aiohttp.web.Request`. Transport modules extract path/query/body parameters and pass them in:

```python
# http_server.py
async def http_genes_get_handler(request):
    ids = request.rel_url.query.get("genes", "").split(",")
    handler = request.app["handler"]
    result = handler.process_genes(ids)
    return web.json_response(result)
```

```python
# request_handler.py
class RequestHandler:
    def process_genes(self, ids: list[str]) -> dict:
        ...  # pure domain logic
```

This separation means `request_handler.RequestHandler` is callable from gRPC handlers, unit tests, and `python -c` ad-hoc invocations without spinning up a server.

### 7.2 CORS

REQUIRED for any service the browser will hit. Set up `aiohttp_cors` exactly once per app, apply it to every route:

```python
import aiohttp_cors

cors = aiohttp_cors.setup(
    app,
    defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    },
)
# ...for every route:
route = app.router.add_get(path, handler_fn)
cors.add(route)
```

CORS configuration MUST NOT be tightened per-route without a written reason; consumers (web-components, dev pages on alternate ports) rely on the permissive default.

### 7.3 Route registration

Every HTTP service uses **manual `aiohttp` routing** — routes are registered against a `web.Application`, either with `app.router.add_<method>(path, handler_fn)` or a `web.RouteTableDef()` plus `@routes.get(...)` decorators. Services differ only in how tightly the route table is bound to the OpenAPI spec:

- **Spec-driven** (`ds_utilities`, `sequences`) — the strongest form, and the one NEW services SHOULD follow ([§ 8](#8-openapi-conventions)). The YAML is the source of truth: the service loads it (`importlib.resources` → `yaml.safe_load`), iterates `spec["paths"]`, and registers each `operationId` (a module-level handler looked up via `globals()[operation_id]`) with `app.router.add_<method>` — so the route table can't silently drift from the documented contract. `ds_utilities` registers `get` only; `sequences` registers `get` and `post`.
- **Decorator-registered, spec doc-only** (`dscensor`) — routes are declared with `@routes.get(...)` decorators; the spec exists as documentation but is not loaded at runtime. Tolerable for a small, stable surface, but the spec and the route table can drift — prefer the spec-driven form for anything non-trivial.
- **No spec** (`linkouts`) — routes registered by hand with no OpenAPI contract at all. An AVOID for new services ([§ 8](#8-openapi-conventions), [§ 17](#17-known-deviations-from-this-spec)).

Within a single service, pick one registration mechanism; don't mix spec-driven iteration and `@routes` decorators.

### 7.4 Error response shape

HTTP error responses MUST be JSON of shape:

```json
{"error": "<human readable message>", "status": <int>}
```

returned with the matching HTTP status code. The 4xx code is the primary signal; the body's `status` field is duplicated for clients that buffer the body before reading headers.

Use the helper convention:

```python
class RequestHandler:
    def send_400_resp(self, msg: str) -> dict:
        return {"error": msg, "status": 400}

    def send_404_resp(self, msg: str) -> dict:
        return {"error": msg, "status": 404}
```

The transport layer maps the dict back to a status code:

```python
result = handler.do_thing(...)
if isinstance(result, dict) and "error" in result and "status" in result:
    return web.json_response(result, status=result["status"])
return web.json_response(result)
```

AVOID raising `aiohttp.web.HTTPBadRequest` from inside `request_handler.py` — that couples the handler to the HTTP transport. The dict-return pattern keeps the handler transport-agnostic.

Orchestration services ([§ 1.3](#1-overview)) MAY instead raise a **transport-agnostic domain exception** carrying `message` + `status` (e.g. `sequences`' `RequestError`), which the transport layer catches and renders into the same JSON shape. This is allowed — and preferred over dict-return — when a request fans out into many fallible steps (`asyncio.gather` over N records) and any one failure must abort the whole request: threading an error-or-result dict back through the gather is far messier than a fail-fast raise. The rule the AVOID above is really protecting is "no *aiohttp/transport* types in the handler"; a plain `Exception` subclass keeps that guarantee.

---

## 8. OpenAPI conventions

A service exposing more than a trivial HTTP surface SHOULD ship an OpenAPI spec as the single source of truth for its routes, and — whichever routing style it uses ([§ 7.3](#73-route-registration)) — drive its route table from that spec rather than hand-maintaining a parallel one. Shipping spec-less (as `linkouts` does) is an AVOID for new services.

For services that ship an OpenAPI spec (`ds_utilities` and `sequences` load and drive their routes from it; `dscensor` keeps it as documentation only — [§ 7.3](#73-route-registration)):

- Schema lives at `<service>/<service>/openapi/<service>/v1/<service>.yaml`, OpenAPI 3.0. One file per service. The schema MUST be inside the package directory (see [§ 4.4](#44-where-contract-files-live) for why).
- Versioned via the `v1` directory; bumping creates `v2/`, not in-place changes that break consumers.
- Loaded at runtime via `importlib.resources.files("<service>") / "openapi/<service>/v1/<service>.yaml"` — works in both editable and built-wheel installs.
- `MANIFEST.in` MUST include `recursive-include <service>/openapi/ *.yaml` and `setup.cfg` MUST set `include_package_data = true` plus the corresponding `[options.package_data]` entry so the file actually ships into site-packages.
- The Dockerfile copies the package directory (which now contains `openapi/`); no separate `COPY openapi/` line.

Path parameter naming MUST match what `aiohttp` expects: `{name}` placeholders, kebab-case for multi-word names. Query parameters use camelCase or snake_case consistently within a service (existing services are inconsistent — pick one per service and stick with it).

Schema definitions live under `components.schemas`. Define a schema once and `$ref` it from response shapes — don't inline structures.

---

## 9. gRPC conventions

gRPC appears in two roles: **servers** (the query services — `genes`, `gene_search`, `search`, `chromosome`, `chromosome_region`, `chromosome_search`, `micro_synteny_search`, `macro_synteny_blocks`, `pairwise_macro_synteny_blocks`) and **clients** (a query service or orchestration service that calls a gRPC peer — `search` calls the search-family services; `sequences` calls `genes`). `dscensor` is **not** a gRPC service — it is HTTP-only (manual `aiohttp` routing) and has no `proto/` tree and no codegen step.

### 9.1 Proto sources and the (uncommitted) generated stubs

- `.proto` sources live at `<svc>/proto/<pkg>/v1/<name>.proto` (proto3) — at the **service root**, a sibling of the package dir. They ship in the sdist via `recursive-include proto/ *.proto` ([§ 4.3](#43-manifestin)).
- The generated `*_pb2.py` / `*_pb2_grpc.py` are **never committed** (the repo `.gitignore` excludes `*_pb2.py` and `*_pb2_grpc.py`). They are generated at **build/install time** by the `BuildProtos` command ([§ 4.1](#41-setuppy)) into the *package* proto dir `<svc>/<svc>/proto/...`, so they install into site-packages and ride along in the wheel.
- protoc cannot emit relative imports and Python 3 has no implicit relative imports, so generated modules import each other by their *flat* package path (`from genes_service.v1 import genes_pb2`). To make that resolve, the package ships `<svc>/<svc>/proto/__init__.py` which appends its own dir to `sys.path`. Consumers therefore do, verbatim:

  ```python
  # isort: off
  from <svc> import proto  # noqa: F401  (runs the sys.path shim)
  from <pkg>_service.v1 import <name>_pb2, <name>_pb2_grpc
  # isort: on
  ```

For local development (editable install) the `BuildProtos` step does not populate the on-disk package dir, so generate the stubs manually once:

```bash
cd <svc>
python -m grpc_tools.protoc -Iproto \
  --python_out=<svc>/proto --grpc_python_out=<svc>/proto \
  proto/<pkg>/v1/<name>.proto ...
```

### 9.2 Build robustness (MUST read before building a gRPC service image)

The codegen build is fragile in three documented ways. New gRPC services MUST handle all three; existing ones are affected and on the migration list ([§ 17](#17-known-deviations-from-this-spec)).

1. **`pkg_resources` is gone in modern setuptools.** Do not locate grpc_tools' bundled well-known protos via `pkg_resources.resource_filename("grpc_tools", "_proto")`: setuptools ≥ 80 no longer ships `pkg_resources`, so in a clean build environment (e.g. a Docker build, where pip installs the latest setuptools) `import pkg_resources` raises `ModuleNotFoundError` and the build dies in `get_requires_for_build_wheel`. A local editable install on a box with older setuptools masks this. Use the stdlib instead:

   ```python
   from importlib import resources
   well_known_protos_include = str(resources.files("grpc_tools") / "_proto")
   ```

2. **Build isolation pulls the wrong grpcio-tools.** With PEP 517 build isolation (pip's default), `setup_requires=("grpcio-tools",)` installs the *latest* grpcio-tools into the isolated build env, ignoring the version pinned in `requirements.txt`. If that generates stubs whose protobuf **gencode** version is newer than the **runtime** `protobuf` the image installed, the service crashes on first import with `google.protobuf.runtime_version.VersionError: ... gencode X runtime Y. Runtime version cannot be older than the linked gencode version.` The Dockerfile MUST therefore install the package with **`--no-build-isolation`** so codegen uses the same pinned grpcio-tools already installed from `requirements.txt`:

   ```dockerfile
   RUN pip3 install --no-cache-dir -r requirements.txt
   RUN pip3 install --no-cache-dir --no-build-isolation .
   ```

3. **Pin protobuf/grpcio/grpcio-tools together.** `grpcio-tools` (codegen) and the runtime `protobuf` MUST come from a compatible release pair; keep them pinned in `requirements.txt` and regenerate `requirements.txt` from `requirements.in` so the gencode and runtime never drift apart.

### 9.3 gRPC servers

`grpc_server.py` mirrors `http_server.py`:

```python
async def run_grpc_server(host: str, port: int, handler) -> None:
    server = grpc.aio.server()
    <name>_pb2_grpc.add_<Service>Servicer_to_server(MyServicer(handler), server)
    server.add_insecure_port(f"{host}:{port}")
    await server.start()
    await server.wait_for_termination()
```

`--no-grpc` toggles it off; `--ghost`/`--gport` (env `GRPC_HOST`/`GRPC_PORT`) configure it. The HTTP and gRPC paths MUST share the same `request_handler.RequestHandler` instance — they are two views of the same backend. Servicers MUST NOT leak internal exceptions to the wire: catch, log, and `context.abort(grpc.StatusCode.INTERNAL, "Internal server error")` (see `genes/genes/grpc_server.py`).

### 9.4 gRPC clients

A service that *calls* gRPC keeps the client in `grpc_client.py` (query services, e.g. `search`) or `clients.py` (orchestration services, e.g. `sequences`, [§ 3.2](#32-orchestration-service-layout-the-clientspy-boundary)) — never in `request_handler.py`. The established convention opens a fresh channel per call to tolerate dynamically-(re)started upstreams, and MUST close it:

```python
from grpc.experimental import aio

async def get_gene_locations(names, address):
    # one channel per call; the context manager closes it so we don't leak a
    # channel + its resources on every request
    async with aio.insecure_channel(address) as channel:
        stub = genes_pb2_grpc.GenesStub(channel)
        try:
            reply = await stub.Get(genes_pb2.GenesGetRequest(names=list(names)))
        except Exception as e:
            logging.error(e)
            raise ServiceError(f"genes service request failed: {e}", status=502)
    return {g.name: {...} for g in reply.genes}
```

Note the `async with`: a bare `aio.insecure_channel(...)` + `await channel.channel_ready()` that is never closed leaks a channel and its resources every request, so code MUST use the context manager. Map any upstream failure to a domain `ServiceError` with an HTTP-ish `status` ([§ 7.4](#74-error-response-shape)).

---

## 10. File I/O for genomics data

Services that read FASTA / GFF / BED / VCF / BAM files MUST use `pysam`:

```python
import pysam

# FASTA (random access):     pysam.FastaFile(url).fetch(reference=seqid, start=s, end=e)
# Tabix-indexed (GFF/BED/VCF): pysam.TabixFile(url).fetch(chrom, start, end, parser=...)
# BAM/SAM/CRAM:               pysam.AlignmentFile(url).fetch(contig, start, stop)
```

AVOID rolling your own format parsers. The library is mature, fast, supports remote URLs (HTTPS, S3, FTP), and handles BGZF / tabix / fai / gzi / csi indexes correctly.

### 10.1 The `ALLOWED_URLS` allowlist

Any service that passes user-supplied URLs to `pysam` MUST gate them via an allowlist read from the `ALLOWED_URLS` env var (comma-separated prefixes):

```python
ALLOWED_URLS = os.environ.get("ALLOWED_URLS", "").split(",")

def check_url(self, url: str) -> str | dict:
    url = urllib.parse.unquote(url)
    if not any(url.startswith(p) for p in ALLOWED_URLS):
        return {"error": "url not allowed or missing query parameters", "status": 403}
    return url
```

This is the only guard against an attacker turning the service into an outbound proxy for arbitrary HTTPS or filesystem URIs.

### 10.2 SSL CA bundle (conda environments)

The conda-built `pysam` wheel links against a libcurl that doesn't trust the system CA store by default. Operators MUST set `CURL_CA_BUNDLE` and `SSL_CERT_FILE` to a valid bundle (e.g. `/etc/ssl/certs/ca-certificates.crt` on Debian) when running outside of the official Docker image. The Docker image takes care of this transparently. Document it in the service README's "running locally" section.

### 10.3 Index caching (and what pysam does *not* cache)

For **tabix-indexed** remote files (GFF/BED/VCF via `TabixFile`, BAM `.bai`/`.csi` via `AlignmentFile`), `pysam` downloads the sibling index (`.tbi`/`.csi`/`.bai`) into the **current working directory** and reuses it for the life of the process. The repo `.gitignore` excludes these (`*.tbi`, `*.fai`, `*.gzi`, `*.csi`, `*.bai`, `*.crai`) globally; do not add per-service rules. (This is also why the Dockerfiles run with `WORKDIR /` — a writable cwd for these drop-files.) If you add a handler for a new htslib index type, make sure its drop-file extension is in the global `.gitignore` — `*.bai` was missing for a while and BAM indexes leaked into working trees.

`FastaFile` is the exception, and it matters: opening a **remote FASTA re-downloads its `.fai` (and `.gzi` for bgzipped FASTA) over HTTPS on *every* open** and writes nothing to cwd. A protein/CDS `.fai` is multi-MB (one line per sequence; tens of thousands of sequences), so a cold `FastaFile(url)` open costs seconds while the subsequent `.fetch()` is sub-second. Reusing an already-open handle makes further fetches ~free, but handles are not safe to share across threads ([§ 10.5](#105-offloading-pysam-to-a-thread-pool)). The sanctioned mitigation is the local FASTA-index cache in [§ 10.6](#106-local-fasta-index-cache).

### 10.4 Strand and coordinate semantics

`pysam` returns plus-strand reference bases and tabix uses 0-based half-open coordinates. Services MUST be explicit about coordinate-system semantics in OpenAPI docstrings:

```yaml
- name: start
  description: |
    Region start, 0-based half-open per the tabix/BED convention.
```

Strand semantics (reverse-complementing minus-strand slices, flipping flank orientation) MUST live in the consumer — an orchestration service (e.g. `sequences`, which owns reverse-complement and flank math and converts the genes service's 1-based-inclusive `fmin`/`fmax` to 0-based half-open via `start - 1`), a web component, or a downstream pipeline. File-format-proxy services stay strand-agnostic so the same endpoint works for both biological and bioinformatics-tool use cases.

One coordinate subtlety the consumer MUST handle: `pysam` **silently truncates** a fetch whose `end` runs past the reference length (e.g. a downstream flank off the end of a short scaffold) — it returns fewer bases without error. A consumer that echoes the requested span in a header/record will then misreport it. Derive any reported end from the **actual** returned length (`end = start + len(seq)`), not the requested end (`sequences` does this in `_fetch_genome`).

### 10.5 Offloading pysam to a thread pool

Per [§ 6.1](#61-never-block-the-event-loop), blocking `pysam` calls in an async handler MUST be offloaded so they don't serialize the event loop. The pattern (see `ds_utilities`):

- `__main__.py` creates one **bounded** `concurrent.futures.ThreadPoolExecutor` and passes it into `run_http_server`, which stores it on `app["executor"]`. The bound is a configurable flag — `--max-workers` / `MAX_WORKERS` (default 16) — and doubles as the cap on concurrent connections to the datastore (be a polite client). Shut it down (`executor.shutdown(wait=False)`) in the `main()` `finally`.
- The transport layer awaits the handler in the pool: `await loop.run_in_executor(app["executor"], request_func, *args)` (positional args only; no kwargs — wrap with `functools.partial` if you need them).
- **Thread-safety requirement:** the handler method called this way MUST be free of shared mutable state, OR guard it. `ds_utilities`' `RequestHandler` is stateless and opens its own `pysam` file object per call, so it is safe to call from many threads with **no locking**. A single `pysam` file handle is **not** thread-safe for concurrent `.fetch()`; never share one across executor threads.
- This works because htslib releases the GIL during network/file I/O (so I/O-bound fetches genuinely overlap). It is not a fix for CPU-bound Python work.

### 10.6 Local FASTA-index cache

Because a remote `FastaFile` open re-downloads its `.fai`/`.gzi` every time ([§ 10.3](#103-index-caching-and-what-pysam-does-not-cache)), a service doing many FASTA opens against the same file SHOULD cache those index siblings on local disk and hand them to `pysam` so the open skips the re-download:

```python
fh = pysam.FastaFile(url,
                     filepath_index=local_fai,
                     filepath_index_compressed=local_gzi)  # .gzi only for .gz
```

`ds_utilities` implements this (config: `--index-cache-dir` / `INDEX_CACHE_DIR`, default a temp subdir; empty string disables). The design points worth copying:

- **Key by URL** (`sha256(url)`), download the index once, publish it **atomically** (`urllib.request.urlretrieve` to a `*.tmp`, then `os.replace`) so a partial download is never used.
- **Per-key lock** (`threading.Lock` keyed by the cache filename) so a cold-cache burst — N executor threads all hitting the same file — downloads the index once, not N times.
- **Thread-safe by construction:** each request still opens its *own* `FastaFile` (reading the shared, read-only index files is fine), so this composes with [§ 10.5](#105-offloading-pysam-to-a-thread-pool) without handle-sharing or locking on the open path.
- **Fail open:** if the index can't be fetched, fall back to a plain remote open (degrade to slow, never to broken). For a bgzipped FASTA, use the local pair only if **both** `.fai` and `.gzi` are present — never a half-cached state.
- **Graceful download SSL:** the cache downloads indexes with stdlib `urllib`, which uses the system CA bundle (so the image MUST have `ca-certificates`, [§ 13.1](#131-dockerfile)) — distinct from the `CURL_CA_BUNDLE` that pysam/libcurl needs ([§ 10.2](#102-ssl-ca-bundle-conda-environments)).
- **Bounding:** the datastore files are immutable, so the cache needs no per-entry validation, but it MUST stay bounded. A background sweep (`--index-cache-ttl` / `INDEX_CACHE_TTL`, default 86400s) deletes entries older than the TTL (re-downloaded on next use); the sweep is an `asyncio` task whose blocking `unlink` work runs in the executor ([§ 6.1](#61-never-block-the-event-loop)).

Effect (measured, 12-gene batch through `sequences` → `ds_utilities`): ~30s with neither optimization → ~7s with the executor alone → ~2.5s with executor + index cache.

---

## 11. Testing

Two flavours, both `unittest`-based, named to be discoverable:

| File | Purpose | Network? | Importable without C extensions? |
|---|---|---|---|
| `test_<unit>.py` | Unit tests for pure logic | No | Yes |
| `test.py` | Integration tests via live HTTP | Yes (`localhost:<port>`) | No (loads `pysam` etc.) |

Run from the service root:

```bash
cd myservice
python -m unittest test_<unit>    # unit
python -m unittest test           # integration (needs running server)
```

### 11.1 Unit tests

Unit tests MUST NOT import any module that pulls heavy C extensions (e.g. `pysam`) or transport libraries. Factor the testable logic into a dependency-free pure module and unit-test that in isolation. The canonical example is `sequences/sequences/fasta.py` (reverse-complement, flank math, FASTA assembly), tested by `sequences/test_fasta.py` with no `pysam`, `aiohttp`, or `grpc` import.

Use `tempfile.TemporaryDirectory()` for filesystem fixtures (see `dscensor/test.py`).

### 11.2 Integration tests

Integration tests assert on real responses from a live service. They MUST:

- Hit `http://localhost:<port>` (the service's documented default).
- Use stable upstream URLs (e.g. `https://data.legumeinfo.org/...`) so the tests don't drift with curated content changes.
- Hash large/complex responses (`hashlib.sha256(json.dumps(resp, sort_keys=True).encode()).hexdigest()`) instead of asserting on full bodies — see `ds_utilities/test.py` for the `response_hash` helper.

CI runs them after starting the service in a container.

---

## 12. Linting, formatting, pre-commit

Configured at the repo root in `.pre-commit-config.yaml`. Three hooks run on every commit:

| Hook | Config | Purpose |
|---|---|---|
| `isort` | `--profile=black` | Import ordering |
| `black` | (defaults) | Code formatting |
| `flake8` | `--max-line-length=88 --extend-ignore=E203` | Style/error linting |

`E203` is ignored because Black's slice spacing (`a[1 : 2]`) conflicts with PEP8's. Don't disable other rules without a comment in `.pre-commit-config.yaml` explaining why.

Per-file ignores go in the same `args:` block:

```yaml
args: [..., "--per-file-ignores=myservice/test.py:E501"]
```

Install once per checkout: `pre-commit install`. New PRs MUST pass all three hooks.

Python version pinned at **3.13** in `default_language_version` — bump globally when upgrading. AVOID per-service Python version pinning.

---

## 13. Docker and docker-compose

### 13.1 `Dockerfile`

Every service has a Dockerfile of this shape (per-service variation only in the marked lines):

```dockerfile
FROM python:3.13.7-slim-trixie

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    # pysam services also need: ca-certificates zlib1g-dev libbz2-dev \
    #   liblzma-dev libcurl4-openssl-dev libssl-dev
    # dscensor also needs: locales
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY INSTALL ./
COPY LICENSE ./
COPY MANIFEST.in ./
COPY README.md ./
COPY setup.cfg ./
COPY setup.py ./
COPY requirements.txt ./
COPY myservice/ ./myservice/     # the package — openapi/ rides along inside it
COPY proto/ ./proto/             # gRPC services only (proto sources, § 9.1)

# pysam/libcurl ignores the system CA store; point it at the bundle (§ 10.2)
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt   # pysam services only

RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install --no-cache-dir .        # gRPC services: add --no-build-isolation (§ 9.2)

WORKDIR /                                # writable cwd for pysam tabix drop-files (§ 10.3)

ENTRYPOINT ["python3", "-u", "-m", "myservice"]
```

Specifics that are easy to get wrong:

- **ENTRYPOINT is `["python3", "-u", "-m", "myservice"]`, not `["myservice"]`.** The bare console-script name does not work because most services mis-register it as `chromosome` ([§ 17](#17-known-deviations-from-this-spec)); `python -m` sidesteps that, and `-u` keeps stdout/stderr unbuffered so container logs are not lost.
- **There is no `COPY openapi/ ./openapi/` line.** The OpenAPI YAML lives *inside* the package ([§ 4.4](#44-where-contract-files-live)) and is copied by `COPY myservice/`. A separate top-level `COPY openapi/` does not ship the spec into the package and MUST NOT be used.
- **pysam services** add the htslib build/runtime libs and `ca-certificates` to `apt-get`, set `CURL_CA_BUNDLE`, and end on `WORKDIR /`. `ca-certificates` is needed both for `CURL_CA_BUNDLE` and for any stdlib `urllib` HTTPS the service does itself (e.g. the FASTA-index cache, [§ 10.6](#106-local-fasta-index-cache)).
- **gRPC services** install with `pip3 install --no-cache-dir --no-build-isolation .` so codegen uses the pinned grpcio-tools ([§ 9.2](#92-build-robustness-must-read-before-building-a-grpc-service-image)). They also `COPY proto/`.
- `dscensor` additionally installs `locales`. Don't expose ports in the Dockerfile — port mapping lives in compose.

### 13.2 Three-file compose pattern

Operationalised services SHOULD ship three compose files:

| File | Purpose |
|---|---|
| `compose.yaml` | base service definition (env vars only) |
| `compose.dev.yaml` | builds locally (`build: { context: . }`) |
| `compose.prod.yaml` | runs prebuilt image (`image: ghcr.io/...`) |

`compose.yaml`:

```yaml
services:
  myservice:
    environment:
      HTTP_HOST: "0.0.0.0"     # bind on all interfaces inside the container
```

`compose.dev.yaml`:

```yaml
services:
  myservice:
    build:
      context: .
    environment:
      ALLOWED_URLS: "https://data.legumeinfo.org/,..."
    ports:
      - "${PORT:-8080}:8080"
    volumes:
      - ${DATA:-./fixture}:/data  # if the service needs a fixture mount
```

`compose.prod.yaml`:

```yaml
services:
  myservice:
    image: ghcr.io/legumeinfo/microservices-myservice:1.2.3
    environment:
      ALLOWED_URLS: "https://data.legumeinfo.org/,..."
    ports:
      - "${PORT:-8080}:8080"
    restart: always
```

Run with: `docker compose -f compose.yaml -f compose.dev.yaml up`.

**Services that call siblings configure peer addresses by env var — and nothing else.** Three services make outbound calls to siblings: `search` and `macro_synteny_blocks` (gRPC clients) and the orchestration service `sequences`. All three take every peer address from an `EnvArg` flag/env var (`GENE_SEARCH_ADDR`, `CHROMOSOME_SEARCH_ADDR`, …; `GENES_ADDR`, `DSCENSOR_URL`, `DS_UTILITIES_URL`). There is **no special Docker networking** — no `host.docker.internal`, no `extra_hosts`, no host-gateway mapping. New sibling-calling services MUST follow this same pattern; do not introduce per-service networking hacks.

The deployment model these env vars assume is a **single shared Docker network** where every service is a container and they address each other by **service name on the container-internal ports** (e.g. `genes:8081`, `http://dscensor:8080`) — *not* the host-published ports. On a shared network, container→container name resolution works everywhere, including plain/rootless Linux, with zero extra configuration (which is why the leaf services — `dscensor`, `ds_utilities`, etc. — "just work": most never call a sibling at all, and the ones that do rely only on this).

So a containerized orchestration service's `compose.dev.yaml` simply defaults its peer-address env vars to the siblings' service names; `compose.prod.yaml` leaves them operator-supplied. `search`/`macro_synteny_blocks` go further and ship **no** compose at all — their addresses are entirely supplied by the deployment that runs them.

### 13.3 Port conventions

| Container internal port | What |
|---|---|
| `8080` | HTTP |
| `8081` | gRPC (when applicable) |

Host ports are overridable via `${PORT:-8080}` so multiple services can run in parallel on a dev machine without collision. The host-port assignments used across the current stack (so a full local ecosystem doesn't collide): `ds_utilities` 8080, `genes` gRPC 8081, `sequences` 8082 (container 8080), `dscensor` 8765 (container 8080), `redis-stack` 6380. Redis-backed services need a RediSearch-capable Redis (e.g. the `redis/redis-stack-server` image), not a vanilla `redis`.

---

## 14. Logging

Configured in `__main__.py` via stdlib `logging`. The standard config:

```python
log_config = {
    "format": "%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    "datefmt": "%H:%M:%S",
    "level": LOG_LEVELS[args.log_level],
}
if "log_file" in args:
    log_config["filename"] = args.log_file
logging.basicConfig(**log_config)
```

Services MUST use stdlib `logging`, not `print()`. Default level is `WARNING` — operators raise it to `INFO` or `DEBUG` via the `--log-level` flag for incident response.

AVOID logging full URLs or request bodies — they often contain user identifiers. Log path-only and short identifiers.

---

## 15. Adding a new service: checklist

1. **Pick a name.** snake_case, matching the package directory name and the `console_scripts` entry. Get `console_scripts` right ([§ 4.2](#42-setupcfg)) — do not copy the `chromosome` bug.
2. **Create the directory skeleton** per [§ 3](#3-service-layout) (and [§ 3.2](#32-orchestration-service-layout-the-clientspy-boundary) for an orchestration service — add `clients.py`).
3. **Copy a sibling's `setup.cfg`** and rename. Update `description`, `author`, `keywords`, `install_requires` (per-service, [§ 4.2](#42-setupcfg)). Use `python_requires = >=3.9,<4`.
4. **`setup.py`:** one-liner for HTTP-only services; the `BuildProtos`/`build_py` variant for gRPC servers and clients ([§ 4.1](#41-setuppy)), which also need `commands.py`, `proto/`, and the [§ 9.2](#92-build-robustness-must-read-before-building-a-grpc-service-image) build-robustness measures.
5. **Write `MANIFEST.in`** per [§ 4.3](#43-manifestin).
6. **Implement the package layout** (`__init__.py` with `__version__`, `__main__.py` per [§ 6](#6-asyncio-and-the-event-loop), `request_handler.py` for domain logic, `http_server.py` / `grpc_server.py` for transport, `clients.py` for an orchestration service).
7. **Write `<service>/openapi/<service>/v1/<service>.yaml`** (inside the package, [§ 4.4](#44-where-contract-files-live)) if using OpenAPI; `proto/<pkg>/v1/<name>.proto` (at the service root, [§ 9.1](#91-proto-sources-and-the-uncommitted-generated-stubs)) if using gRPC.
8. **Add `Dockerfile`** per [§ 13.1](#131-dockerfile) (note the pysam apt deps + `CURL_CA_BUNDLE`, the gRPC `--no-build-isolation`, and the `python3 -u -m` ENTRYPOINT).
9. **Add compose files** if operationalised. A sibling-calling service takes peer addresses purely from env vars ([§ 13.2](#132-three-file-compose-pattern)) — service-name defaults in `compose.dev.yaml`, operator-supplied in `compose.prod.yaml`. No `host.docker.internal`/`extra_hosts`.
10. **Write tests:** at minimum a `test_<core_logic>.py` unit test over a pysam-/transport-free pure module ([§ 11.1](#111-unit-tests)); `test.py` integration test once the service is wired.
11. **Verify a clean build.** Build the image from scratch (not just an editable install) — a from-scratch build is what surfaces the [§ 9.2](#92-build-robustness-must-read-before-building-a-grpc-service-image) gRPC packaging traps — then run it and smoke the index route:
    ```sh
    docker build -t microservices-<service> .        # clean build surfaces the § 9.2 gRPC traps
    docker run --rm -p 8080:8080 <env vars> microservices-<service>
    curl -s http://localhost:8080/ | head            # then exercise the real endpoints
    ```
12. **README.md** with: purpose, env vars, ports, curl examples, "running locally" instructions including CA-bundle env vars ([§ 10.2](#102-ssl-ca-bundle-conda-environments)) if pysam is used.
13. **PR description** notes any deviation from this spec, with rationale.

(Lint and the pre-push routine live in `AGENTS.md`.)

A bare-minimum service that conforms to all of the above is ~400 lines of Python plus configuration. If your draft is much more, you're probably re-implementing something that should live in `request_handler.py` only.

---

## 16. Modifying an existing service: checklist

Pre-flight (read the docs, `git log -- <service>/`, check the *Known deviations* table below) and the pre-push routine (`pre-commit`, `curl`-verify) live in `AGENTS.md`. This section is only what's specific to the change:

- Update `request_handler.py` for domain changes, OpenAPI/proto for contract changes, transport modules only for plumbing.
- Add or update unit tests in `test_<unit>.py`; add an integration test only when the change is observable over the wire.
- Bump the version in `<service>/__init__.py` per semver.

For cross-cutting changes (touching multiple services), open a tracking issue first. Cross-cutting refactors MUST update this document to keep it accurate.

---

## 17. Known deviations from this spec

As of the latest revision, the tree disagrees with this spec in the following places. New work MUST conform; existing code is on a migration backlog.

| Service | Deviation | Severity | Migration |
|---|---|---|---|
| `linkouts` | `run_http_server` uses `web.run_app(app)`; `--host`/`--port` are silently ignored | medium | Apply the same async + `AppRunner` fix used in `ds_utilities` |
| `linkouts` | Registers routes by hand with no OpenAPI spec, so the route table has no source-of-truth contract (an AVOID for new services per [§ 8](#8-openapi-conventions)) | low | Add `linkouts/linkouts/openapi/linkouts/v1/linkouts.yaml` and drive the routes from it (spec-driven, [§ 7.3](#73-route-registration)) |
| `dscensor` | Keeps its OpenAPI spec *outside* the package (`dscensor/openapi/...`, via MANIFEST `recursive-include openapi/`), contrary to [§ 4.4](#44-where-contract-files-live). The spec is documentation-only — not loaded at runtime (routes are `@routes.get` decorators) — so it can drift from the actual route table. | low | `git mv dscensor/openapi dscensor/dscensor/openapi`; change MANIFEST `recursive-include openapi/` → `dscensor/openapi/`; then drive the routes from the spec (spec-driven, [§ 7.3](#73-route-registration)) per [§ 8](#8-openapi-conventions). |
| Other OpenAPI-using services (none today; `linkouts` and the gRPC family don't use OpenAPI) | n/a — flag here pre-emptively so any future service that adds an OpenAPI YAML lands it in the right place from day one | n/a | Read [§ 4.4](#44-where-contract-files-live) before adding the YAML |
| `linkouts`, `genes`, `gene_search`, `chromosome`, `chromosome_region`, `chromosome_search`, `micro_synteny_search`, `macro_synteny_blocks`, `pairwise_macro_synteny_blocks`, `search` | CLI flags are `--hhost`/`--hport`, not `--host`/`--port` | low | Rename to `--host`/`--port`; alias the old names with `--hhost` deprecated for one release |
| `genes`, `gene_search`, `search`, `chromosome_region`, `chromosome_search`, `micro_synteny_search`, `macro_synteny_blocks`, `pairwise_macro_synteny_blocks` (8 services) | `console_scripts` registers the binary as `chromosome`, not the service name (copy-paste from `chromosome`, the only one where it's coincidentally correct) | medium | Rename the entry to the package name; tag a major version bump (breaking for ops). Masked today because every Dockerfile/ENTRYPOINT uses `python3 -u -m <svc>` ([§ 13.1](#131-dockerfile)), not the binary |
| All 9 gRPC services (`genes`, `gene_search`, `search`, `chromosome`, `chromosome_region`, `chromosome_search`, `micro_synteny_search`, `macro_synteny_blocks`, `pairwise_macro_synteny_blocks`) | `commands.py` uses `pkg_resources.resource_filename("grpc_tools", "_proto")`; setuptools ≥ 80 (what a clean Docker build pulls) no longer ships `pkg_resources`, so a from-scratch image build dies in `get_requires_for_build_wheel`. Editable installs on boxes with older setuptools mask it. | high (latent — breaks any clean rebuild) | Replace with `importlib.resources.files("grpc_tools") / "_proto"` ([§ 9.2](#92-build-robustness-must-read-before-building-a-grpc-service-image)). Already applied in `sequences` |
| All 9 gRPC services' `Dockerfile` | Install with `pip3 install .` under build isolation, so `setup_requires` pulls the *latest* grpcio-tools and can generate protobuf gencode newer than the pinned runtime `protobuf` → container crashes on import with a gencode/runtime `VersionError`. | high (latent — surfaces when upstream grpcio-tools moves ahead of the pin) | Add `--no-build-isolation` ([§ 9.2](#92-build-robustness-must-read-before-building-a-grpc-service-image)). Already applied in `sequences` |
| `search` (and the query-service gRPC clients generally) | `grpc_client.py` opens `aio.insecure_channel(...)` per call but never closes it → a channel leak per request | low | Wrap in `async with aio.insecure_channel(address) as channel:` ([§ 9.4](#94-grpc-clients)). Already applied in `sequences/clients.py` |
| `dscensor`, `ds_utilities`, `sequences` | Compose files exist; other services have none | none — by design | Compose is per-service; not every service ships as a container |

When this list shrinks to zero, this section gets deleted.

---

## 18. Glossary

- **autocontent JSON** — A single JSON object (one per cataloged asset) emitted by the `ds-curate` tooling; the input format for `dscensor`'s digraph.
- **full-yuck prefix** — A `gensp.infraspecies.gnm<N>.ann<N>` annotation prefix (e.g. `glyma.Wm82.gnm2.ann1`). The leading four dot-tokens of any LIS gene ID. Not "4-dot prefix" — that's not the team's term. ("yuck" is the team's term for a full LIS identifier; a gene yuck is e.g. `glyma.Wm82.gnm2.ann1.Glyma.08G002000`.)
- **datastore** — The LIS file hosting at `data.legumeinfo.org` (and SoyBase / PeanutBase / etc. equivalents). Read-only, BGZF + tabix indexed, accessed over HTTPS. Files are immutable (content is versioned by path), which is what makes the FASTA-index cache ([§ 10.6](#106-local-fasta-index-cache)) safe.
- **mine** — An InterMine instance (per organism: SoyMine, ChickpeaMine, ...). Source of truth for cross-gene relationships (pangenes, families, orthology). Accessed via GraphQL.
- **orchestration service** — A service that owns no datastore and composes siblings into a higher-level operation (shape 3, [§ 1](#1-overview); only `sequences` today). Adds a `clients.py` transport-out module ([§ 3.2](#32-orchestration-service-layout-the-clientspy-boundary)).
- **RediSearch** — The Redis module providing the secondary indexes (`geneIdx`, `chromosomeIdx`) the query services read. A vanilla `redis` server is insufficient; use a RediSearch-capable build (e.g. `redis/redis-stack-server`). `redis_loader` builds these indexes from GFF or a Chado database.
- **gencode / runtime (protobuf)** — The protobuf "gencode" version is stamped into generated `*_pb2.py` by `protoc`/grpcio-tools at build time; the "runtime" is the installed `protobuf` package. The runtime MUST be ≥ the gencode or import fails with a `VersionError` — the failure mode [§ 9.2](#92-build-robustness-must-read-before-building-a-grpc-service-image) guards against.

---

## 19. References

- [Conventional Commits](https://www.conventionalcommits.org/) — preferred commit message style.
- [aiohttp web reference](https://docs.aiohttp.org/en/stable/web_reference.html)
- [pysam manual](https://pysam.readthedocs.io/en/latest/)
- [pre-commit framework](https://pre-commit.com/)
- [Semantic Versioning 2.0](https://semver.org/)
