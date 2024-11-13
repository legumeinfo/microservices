
Minimal example of a partial [FastAPI](https://fastapi.tiangolo.com/)-generated API for querying a BGZF-compressed & faidx-indexed FASTA file using [pysam](https://pysam.readthedocs.io/).

## Example

```
$ python3 -m venv fasta_api_env
$ source ./fasta_api_env/bin/activate
(fasta_api_env)$ pip install -r requirements.txt
(fasta_api_env)$ python ./setup.py install
(fasta_api_env)$ fasta_api
======== Running on http://0.0.0.0:8080 ========
(Press CTRL+C to quit)
```

In another terminal, manually enter the following command:
```
$ curl localhost:8080/fasta/references/https%3A%2F%2Fdata.legumeinfo.org%2FGlycine%2Fmax%2Fgenomes%2FWm82.gnm2.DTC4%2Fglyma.Wm82.gnm2.DTC4.genome_main.fna.gz
```

## ALLOWED_URLS

In production, the `ALLOWED_URLS` environment variable can be set to a comma-separated list of target URL prefixes to allow.
If the requested URL begins with any of the URLs in the list, the request will be allowed; otherwise, an HTTP 403 status code will result.

```
$ export ALLOWED_URLS='https://data.legumeinfo.org/,https://www.soybase.org/data/v2/';fasta_api
```

## API documentation

See localhost:8080/help for routes.
