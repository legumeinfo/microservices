FROM python:3.12-slim

COPY requirements.txt /tmp

RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY main.py /usr/local/bin/fasta-api.py

# htslib downloads index files to current working directory
WORKDIR /var/tmp

USER nobody

ENTRYPOINT ["uvicorn", "--host", "0.0.0.0", "fasta-api:app"]
EXPOSE 8000

# work around the following issue impacting PySAM 0.22.[01] on debian:
# https://github.com/pysam-developers/pysam/issues/1257
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
