# Docker

Run local development build from cwd.

`docker compose -f compose.yaml -f compose.dev.yaml up`

Run production build from tagged image.

`docker compose -f compose.yaml -f compose.prod.yaml up`

# Development

## Install Pre-commit Hooks

Install pre-commit hooks before developing. The github will force you to subscribe on PR if you don't so please do!

`pre-commit install`

## install fasta_api
```
$ python3 -m venv fasta_api_env
$ source ./fasta_api_env/bin/activate
(fasta_api_env)$ pip install -r requirements.txt
(fasta_api_env)$ python ./setup.py install
(fasta_api_env)$ fasta_api
======== Running on http://0.0.0.0:8080 ========
(Press CTRL+C to quit)
```

## Testing

In another terminal, manually enter the following command:
```
$ curl http://localhost:8080/fasta/references?url=https://data.legumeinfo.org/Glycine/max/genomes/Wm82.gnm2.DTC4/glyma.Wm82.gnm2.DTC4.genome_main.fna.gz
```

## ALLOWED_URLS

In production, the `ALLOWED_URLS` environment variable can be set to a comma-separated list of target URL prefixes to allow.
If the requested URL begins with any of the URLs in the list, the request will be allowed; otherwise, an HTTP 403 status code will result.

```
$ export ALLOWED_URLS='https://data.legumeinfo.org/,https://data.soybase.org/';fasta_api
```

## API documentation

See `localhost:8080/help` for routes.
