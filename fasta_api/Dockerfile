FROM python:3.13.7-slim-trixie

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev \
    libbz2-dev \
    liblzma-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

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
