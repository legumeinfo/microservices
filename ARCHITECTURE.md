# Microservices: architecture and engineering conventions

**Audience.** Engineers (human and AI) contributing to this monorepo. Read this before adding a new service or making cross-cutting changes. Skim it before non-trivial edits to an existing one.

**Status of this document.** It describes the *target* conventions — what new code MUST do and what existing code SHOULD eventually look like. Where the current tree disagrees with the spec, the inconsistencies are catalogued in the "Known deviations" section at the end so the gap is explicit, not folkloric.

**Normative language.**
- **MUST / MUST NOT** — required. Code that violates this should not merge.
- **SHOULD / SHOULD NOT** — strongly recommended. Deviations need rationale in the PR description.
- **MAY** — discretionary; no policy attached.
- **AVOID** — pattern present in the tree that is now considered a mistake. Don't propagate it.

---

## 1. Overview

This repository hosts a family of Python microservices for the Legume Information System (LIS) and adjacent AgBio databases. They sit between the LIS datastore (FASTA / GFF / BED / VCF / BAM / Redis) and the consumer-facing UI components in the [`web-components`](https://github.com/legumeinfo/web-components) repo.

Two service shapes exist:

1. **File-format proxy services.** Wrap `pysam` over remote indexed files in the LIS datastore. Examples: `ds_utilities`, `linkouts`. HTTP-only, generally stateless.
2. **Query services.** Backed by Redis (built by `redis_loader`) or by a static catalog. Examples: `genes`, `gene_search`, `chromosome`, `chromosome_search`, `chromosome_region`, `micro_synteny_search`, `macro_synteny_blocks`, `pairwise_macro_synteny_blocks`, `search`, `dscensor`. Most expose both HTTP and gRPC.

Both shapes follow the same packaging / CLI / asyncio / linting conventions detailed below.

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
└── <service-name>/          ← one directory per service (see § 3)

Note: OpenAPI specs and protobuf definitions live INSIDE the per-service
package directory (`<service>/<service>/openapi/...` and `<service>/proto/...`),
not at the repo root. See § 3 and § 4.4.
```

### 2.1 New top-level directories

A new top-level directory MUST be one of:
- A service (per § 3)
- `data/` content (fixtures, never service-specific runtime state)
- `openapi/` or `proto/` if the service contracts live there
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
├── setup.py                 ← REQUIRED — minimal: `setuptools.setup()`
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

---

## 4. Packaging

### 4.1 `setup.py`

MUST be exactly:

```python
#!/usr/bin/env python
import setuptools

setuptools.setup()
```

AVOID running side effects in `setup.py` (file copies, code generation, network calls). Put all packaging metadata in `setup.cfg` and shipped-file selection in `MANIFEST.in`.

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
    aiohttp
    aiohttp-cors
    uvloop
    pyyaml
    # ...service-specific deps

[options.entry_points]
console_scripts =
    myservice = myservice.__main__:main
```

The `console_scripts` entry MUST match the package name. (A current bug in `genes/setup.cfg` ships the binary as `chromosome` — don't copy that.)

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
    # for libraries that take a file path string (e.g. rororo's setup_openapi):
    #   api_path = str(api_path)
    # for libraries that accept a Traversable (yaml.safe_load):
    #   with api_path.open("r") as f:
    #       spec = yaml.safe_load(f)
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
# do NOT add `COPY openapi/ ./openapi/` — that's the old broken pattern
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

---

## 7. HTTP server

Each HTTP-exposing service has a `http_server.py` whose entry point is:

```python
async def run_http_server(host: str, port: int, handler) -> None:
    ...
```

It MUST:

1. Build the `aiohttp.web.Application` and store the handler under `app["handler"]`.
2. Register CORS via `aiohttp_cors` with permissive defaults (see § 7.2).
3. Wire routes (manually or from OpenAPI, see § 7.3).
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

### 7.3 Two routing styles, both valid

The codebase has two coexisting patterns:

- **OpenAPI-driven via `rororo`** (`dscensor`). The YAML is the source of truth; `setup_openapi(app, api_path, operations, ...)` wires routes and validates parameters automatically. Operations are registered via `@operations.register("operationId")`.
- **Manual aiohttp routing** (`ds_utilities`, `linkouts`, all gRPC-paired services). Routes are added explicitly with `app.router.add_get(path, handler_fn)`. Some services (`ds_utilities`) iterate an OpenAPI YAML to discover the path / `operationId` mapping but still register manually.

NEW services SHOULD use rororo when they expose a non-trivial REST surface — the OpenAPI-as-source-of-truth model removes a class of param-parsing bugs. The manual style is acceptable for narrow surfaces (≤3 endpoints) or services that have evolved organically.

Whichever pattern you pick, do NOT mix them in the same service.

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

---

## 8. OpenAPI conventions

For services that use OpenAPI (dscensor, ds_utilities):

- Schema lives at `<service>/<service>/openapi/<service>/v1/<service>.yaml`, OpenAPI 3.0. One file per service. The schema MUST be inside the package directory (see § 4.4 for why).
- Versioned via the `v1` directory; bumping creates `v2/`, not in-place changes that break consumers.
- Loaded at runtime via `importlib.resources.files("<service>") / "openapi/<service>/v1/<service>.yaml"` — works in both editable and built-wheel installs.
- `MANIFEST.in` MUST include `recursive-include <service>/openapi/ *.yaml` and `setup.cfg` MUST set `include_package_data = true` plus the corresponding `[options.package_data]` entry so the file actually ships into site-packages.
- The Dockerfile copies the package directory (which now contains `openapi/`); no separate `COPY openapi/` line.

Path parameter naming MUST match what `aiohttp` / `rororo` expect: `{name}` placeholders, kebab-case for multi-word names. Query parameters use camelCase or snake_case consistently within a service (existing services are inconsistent — pick one per service and stick with it).

Schema definitions live under `components.schemas`. Define a schema once and `$ref` it from response shapes — don't inline structures.

---

## 9. gRPC conventions

For services that expose gRPC (the "Query services" listed in § 1):

- Protobuf at `proto/<service>/v1/<service>.proto`, proto3.
- Generated stubs live at the *consumer* side, not committed in the package directory. (See dscensor's `Dockerfile` for the build step.)
- `grpc_server.py` mirrors `http_server.py`:

  ```python
  async def run_grpc_server(host: str, port: int, handler) -> None:
      server = grpc.aio.server()
      <service>_pb2_grpc.add_<Service>Servicer_to_server(MyServicer(handler), server)
      server.add_insecure_port(f"{host}:{port}")
      await server.start()
  ```
- `--no-grpc` toggles it off; `--ghost`/`--gport` (env `GRPC_HOST`/`GRPC_PORT`) configure it.

The HTTP and gRPC paths MUST share the same `request_handler.RequestHandler` instance — they are two views of the same backend.

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
        return {"error": "url not allowed", "status": 403}
    return url
```

This is the only guard against an attacker turning the service into an outbound proxy for arbitrary HTTPS or filesystem URIs.

### 10.2 SSL CA bundle (conda environments)

The conda-built `pysam` wheel links against a libcurl that doesn't trust the system CA store by default. Operators MUST set `CURL_CA_BUNDLE` and `SSL_CERT_FILE` to a valid bundle (e.g. `/etc/ssl/certs/ca-certificates.crt` on Debian) when running outside of the official Docker image. The Docker image takes care of this transparently. Document it in the service README's "running locally" section.

### 10.3 Index caching

`pysam` writes sibling index files (`.tbi`, `.fai`, `.gzi`, `.csi`) into the current working directory when it fetches them on demand from a remote URL. The repo `.gitignore` excludes these globally; do not add per-service rules.

### 10.4 Strand and coordinate semantics

`pysam` returns plus-strand reference bases and tabix uses 0-based half-open coordinates. Services MUST be explicit about coordinate-system semantics in OpenAPI docstrings:

```yaml
- name: start
  description: |
    Region start, 0-based half-open per the tabix/BED convention.
```

Strand semantics (reverse-complementing minus-strand slices, flipping flank orientation) MUST live in the consumer (web component, downstream pipeline). File-format-proxy services stay strand-agnostic so the same endpoint works for both biological and bioinformatics-tool use cases.

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

Unit tests MUST NOT import any module that pulls heavy C extensions (e.g. `pysam`). Factor the testable logic into a pysam-free module (see `ds_utilities/ds_utilities/bed_lookup.py` for the pattern) so CI can run unit tests without installing the extension.

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

Every service has a Dockerfile of this shape (no per-service variation beyond the COPY lines):

```dockerfile
FROM python:3.13.7-slim-trixie

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY INSTALL ./
COPY LICENSE ./
COPY MANIFEST.in ./
COPY README.md ./
COPY setup.cfg ./
COPY setup.py ./
COPY requirements.txt ./
COPY myservice/ ./myservice/
COPY openapi/ ./openapi/        # if using OpenAPI
COPY proto/ ./proto/            # if using gRPC

RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install --no-cache-dir .

ENTRYPOINT ["myservice"]
```

Add `locales` to `apt-get install` if the service needs them (dscensor does; ds_utilities doesn't). Don't expose ports in the Dockerfile — port mapping lives in compose.

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

### 13.3 Port conventions

| Container internal port | What |
|---|---|
| `8080` | HTTP |
| `8081` | gRPC (when applicable) |

Host ports are overridable via `${PORT:-8080}` so multiple services can run in parallel on a dev machine without collision.

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

1. **Pick a name.** snake_case, matching the package directory name and the `console_scripts` entry.
2. **Create the directory skeleton** per § 3.
3. **Copy a sibling's `setup.cfg`** and rename. Update `description`, `author`, `keywords`, `install_requires`.
4. **Copy `setup.py`** — it stays a one-liner.
5. **Write `MANIFEST.in`** per § 4.3.
6. **Implement the package layout** (`__init__.py` with `__version__`, `__main__.py` per § 6, `request_handler.py` for domain logic, `http_server.py` / `grpc_server.py` for transport).
7. **Write `openapi/<service>/v1/<service>.yaml`** if using OpenAPI; `proto/<service>/v1/<service>.proto` if using gRPC.
8. **Add `Dockerfile`** per § 13.1.
9. **Add compose files** if operationalised.
10. **Write tests:** at minimum a `test_<core_logic>.py` unit test; `test.py` integration test once the service is wired.
11. **Run `pre-commit run --all-files`** before pushing.
12. **README.md** with: purpose, env vars, ports, curl examples, "running locally" instructions including CA-bundle env vars (§ 10.2) if pysam is used.
13. **PR description** notes any deviation from this spec, with rationale.

A bare-minimum service that conforms to all of the above is ~400 lines of Python plus configuration. If your draft is much more, you're probably re-implementing something that should live in `request_handler.py` only.

---

## 16. Modifying an existing service: checklist

Before any change:

1. Read this document.
2. Read the service's `README.md`.
3. `git log -- <service>/` for recent context.
4. Check the "Known deviations" table (§ 17) to see if the file you're touching is on the migration list.

For the change itself:

- Update `request_handler.py` for domain changes, OpenAPI/proto for contract changes, transport modules only for plumbing.
- Add or update unit tests in `test_<unit>.py`; add an integration test only when the change is observable over the wire.
- Bump the version in `<service>/__init__.py` per semver.
- Run `pre-commit run --all-files`.
- Verify behavior end-to-end with `curl` against a locally running service.

For cross-cutting changes (touching multiple services), open a tracking issue first. Cross-cutting refactors MUST update this document to keep it accurate.

---

## 17. Known deviations from this spec

As of the latest revision, the tree disagrees with this spec in the following places. New work MUST conform; existing code is on a migration backlog.

| Service | Deviation | Severity | Migration |
|---|---|---|---|
| `linkouts` | `run_http_server` uses `web.run_app(app)`; `--host`/`--port` are silently ignored | medium | Apply the same async + `AppRunner` fix used in `ds_utilities` |
| `dscensor` | OpenAPI YAML lives at `dscensor/openapi/dscensor/v1/dscensor.yaml` (outside the package), and `http_server.py` loads it via `Path(__file__).parent.parent / "openapi/..."`. Works only in editable installs and inside the current `Dockerfile` (which copies the openapi tree to `/app/openapi/` *and* runs `python -m dscensor` with `WORKDIR=/`). A plain `pip install .` into a venv puts the package in site-packages but leaves `openapi/` behind in the source dir, and the runtime path `Path(__file__).parent.parent / "openapi/..."` resolves to `/usr/local/lib/python3.13/site-packages/openapi/...` which doesn't exist — startup blows up with `FileNotFoundError`. | medium (latent, current Docker workflow happens to mask it) | Apply the same `importlib.resources`-based fix used in `ds_utilities`: `git mv dscensor/openapi dscensor/dscensor/openapi`; switch the runtime path lookup to `str(resources.files("dscensor") / "openapi/dscensor/v1/dscensor.yaml")`; add `[options.package_data]` for `dscensor = openapi/dscensor/v1/*.yaml` (`include_package_data` is already true); change MANIFEST `recursive-include` from `openapi/` to `dscensor/openapi/`; drop `COPY openapi/ ./openapi/` from the `Dockerfile`. See § 4.4 for the full recipe. |
| Other OpenAPI-using services (none today; `linkouts` and the gRPC family don't use OpenAPI) | n/a — flag here pre-emptively so any future service that adds an OpenAPI YAML lands it in the right place from day one | n/a | Read § 4.4 before adding the YAML |
| `linkouts`, `genes`, `gene_search`, `chromosome`, `chromosome_region`, `chromosome_search`, `micro_synteny_search`, `macro_synteny_blocks`, `pairwise_macro_synteny_blocks`, `search` | CLI flags are `--hhost`/`--hport`, not `--host`/`--port` | low | Rename to `--host`/`--port`; alias the old names with `--hhost` deprecated for one release |
| `genes/setup.cfg` | `console_scripts` entry registers the binary as `chromosome`, not `genes` | medium | Rename the binary; tag a major version bump (breaking for ops) |
| `dscensor` | Uses `rororo` (OpenAPI-driven) while most others use manual aiohttp routing | none — by design | Codified in § 7.3 as an acceptable alternative pattern |
| `dscensor` and `ds_utilities` only | Compose files exist; other services have none | none — by design | Compose is per-service; not every service ships as a container |

When this list shrinks to zero, this section gets deleted.

---

## 18. Glossary

- **autocontent JSON** — A single JSON object (one per cataloged asset) emitted by the `ds-curate` tooling; the input format for `dscensor`'s digraph.
- **full-yuck prefix** — A `gensp.infraspecies.gnm<N>.ann<N>` annotation prefix (e.g. `glyma.Wm82.gnm2.ann1`). The leading four dot-tokens of any LIS gene ID. Not "4-dot prefix" — that's not the team's term.
- **datastore** — The LIS file hosting at `data.legumeinfo.org` (and SoyBase / PeanutBase / etc. equivalents). Read-only, BGZF + tabix indexed, accessed over HTTPS.
- **mine** — An InterMine instance (per organism: SoyMine, ChickpeaMine, ...). Source of truth for cross-gene relationships (pangenes, families, orthology). Accessed via GraphQL.

---

## 19. References

- [Conventional Commits](https://www.conventionalcommits.org/) — preferred commit message style.
- [aiohttp web reference](https://docs.aiohttp.org/en/stable/web_reference.html)
- [rororo OpenAPI integration](https://rororo.readthedocs.io/en/latest/openapi.html)
- [pysam manual](https://pysam.readthedocs.io/en/latest/)
- [pre-commit framework](https://pre-commit.com/)
- [Semantic Versioning 2.0](https://semver.org/)
