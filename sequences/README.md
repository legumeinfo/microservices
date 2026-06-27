# sequences

A microservice that takes a list of gene IDs (full yucks, e.g.
`glyma.Wm82.gnm2.ann1.Glyma.08G002000`) and returns their **protein**, **CDS**,
or **genomic** sequences assembled into a single downloadable FASTA file.

`sequences` is an *orchestration* service — it doesn't read files itself. It
composes three existing services:

- **genes** (gRPC) — resolves each gene's chromosome, coordinates, and strand
  (used only for `type=genome`).
- **dscensor** (HTTP `/files/{prefix}`) — resolves the canonical protein / CDS /
  genome FASTA URLs for an annotation prefix.
- **ds_utilities** (HTTP `/fasta/fetch`) — fetches the actual sequence bytes
  (this endpoint is consumed unchanged).

The genome path additionally owns the strand-aware flank math and the
reverse-complement of minus-strand records — logic that intentionally does not
live in `ds_utilities`.

## Endpoints

```
GET  /seq/{yucks}?type=protein|cds|genome&up=0&down=0
POST /seq          {"yucks": [...], "type": "genome", "up": 0, "down": 0}
```

`{yucks}` is a comma-separated list of gene IDs. `type` defaults to `protein`.
`up` / `down` are upstream / downstream flank lengths in bases (0..10000), and
only apply to `type=genome`. Both responses return `text/x-fasta` as a file
download (`Content-Disposition: attachment`). If **any** requested gene can't be
resolved the whole request fails (4xx) — no partial FASTA is returned.

## Configuration

Set via flags or environment variables (env var in parentheses):

- `--genes-address` (`GENES_ADDR`) — gRPC `host:port` of the genes service. *Required.*
- `--dscensor-url` (`DSCENSOR_URL`) — base URL of dscensor. *Required.*
- `--ds-utilities-url` (`DS_UTILITIES_URL`) — base URL of ds_utilities. *Required.*
- `--host` (`HTTP_HOST`), `--port` (`HTTP_PORT`) — HTTP server bind. Default
  `127.0.0.1:8080`.
- `--log-level` (`LOG_LEVEL`), `--log-file` (`LOG_FILE`).

`ds_utilities`' own `ALLOWED_URLS` allowlist still governs which FASTA URLs can
be fetched — `sequences` reaches the files only through it.

## Install

```
$ python3 -m venv sequences_env
$ source ./sequences_env/bin/activate
(sequences_env)$ pip install -r requirements.txt
(sequences_env)$ pip install .
(sequences_env)$ GENES_ADDR=localhost:8081 \
    DSCENSOR_URL=http://localhost:8765 \
    DS_UTILITIES_URL=http://localhost:8080 \
    sequences --host 0.0.0.0 --port 8082
```

> Note: `pip install .` (not `python setup.py install`) so the gRPC client stubs
> for the genes service are generated from `proto/` at build time.

## Docker

```
docker compose -f compose.yaml -f compose.dev.yaml up
```

## Example

```
curl "http://localhost:8082/seq/glyma.Wm82.gnm2.ann1.Glyma.08G002000,glyma.Wm82.gnm2.ann1.Glyma.08G003000?type=protein" > out.faa

curl "http://localhost:8082/seq/glyma.Wm82.gnm2.ann1.Glyma.08G002000?type=genome&up=1000&down=500" > out.fna

curl -X POST http://localhost:8082/seq \
  -H 'Content-Type: application/json' \
  -d '{"yucks":["glyma.Wm82.gnm2.ann1.Glyma.08G002000"],"type":"cds"}' > out.fna
```

## Development

Install pre-commit hooks before developing:

```
pre-commit install
```
