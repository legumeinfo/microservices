# Docker

Run local development build from cwd.

`docker compose -f compose.yaml -f compose.dev.yaml up`

Run production build from tagged image.

`docker compose -f compose.yaml -f compose.prod.yaml up`

# Development

## Install Pre-commit Hooks

Install pre-commit hooks before developing. The github will force you to subscribe on PR if you don't so please do!

`pre-commit install`

## install ds_utilities
```
$ python3 -m venv ds_utilities_env
$ source ./ds_utilities_env/bin/activate
(ds_utilities_env)$ pip install -r requirements.txt
(ds_utilities_env)$ python ./setup.py install
(ds_utilities_env)$ ds_utilities
======== Running on http://0.0.0.0:8080 ========
(Press CTRL+C to quit)
```

## Testing

In another terminal, manually enter the following command (ensure `/` is encoded as `%2F`):
```
curl "http://localhost:8080/fasta/references/https:%2F%2Fdata.legumeinfo.org%2FGlycine%2Fmax%2Fgenomes%2FWm82.gnm2.DTC4%2Fglyma.Wm82.gnm2.DTC4.genome_main.fna.gz"
curl "http://localhost:8080/fasta/fetch/glyma.Wm82.gnm2.Gm01:0-25/https:%2F%2Fdata.legumeinfo.org%2FGlycine%2Fmax%2Fgenomes%2FWm82.gnm2.DTC4%2Fglyma.Wm82.gnm2.DTC4.genome_main.fna.gz"
```

## ALLOWED_URLS

In production, the `ALLOWED_URLS` environment variable can be set to a comma-separated list of target URL prefixes to allow.
If the requested URL begins with any of the URLs in the list, the request will be allowed; otherwise, an HTTP 403 status code will result.

```
$ export ALLOWED_URLS='https://data.legumeinfo.org/,https://data.soybase.org/';ds_utilities
```

## Performance tuning

pysam's file I/O is synchronous and, for remote files, dominated by network
round-trips. Two knobs keep concurrent requests from serializing:

- `--max-workers` / `MAX_WORKERS` (default `16`) — size of the thread pool the
  blocking pysam calls are offloaded to. htslib releases the GIL during I/O, so
  this also bounds the number of concurrent connections to the datastore.
- `--index-cache-dir` / `INDEX_CACHE_DIR` (default a `ds_utilities-index-cache`
  directory under the system temp dir) — where remote FASTA index siblings
  (`.fai`/`.gzi`) are cached. Opening a remote FASTA otherwise re-downloads its
  index (a protein/CDS `.fai` can be several MB) on every request; caching it
  once and reusing it via pysam's `filepath_index` makes repeated opens of the
  same file cheap. Set to an empty string to disable. The cache assumes the
  datastore files are immutable (their indexes never change) and is not
  size-bounded, so point it at ephemeral storage or clear it periodically.

## API documentation

See `localhost:8080/help` for routes.
