FROM python:3.10-slim-buster

WORKDIR /app

COPY INSTALL ./
COPY LICENSE ./
COPY MANIFEST.in ./
COPY README.md ./
COPY setup.cfg ./
COPY setup.py ./
COPY requirements.txt ./
COPY fasta_api ./fasta_api/

# set for most recent pysam, pysam issue #1257
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# install the package dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# install (and implicitly build) the package
RUN pip3 install --no-cache-dir .

WORKDIR /

ENTRYPOINT ["python3", "-u", "-m", "fasta_api"]
