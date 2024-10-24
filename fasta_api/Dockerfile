FROM python:3.10-slim-buster

WORKDIR /app

COPY INSTALL ./
COPY LICENSE ./
COPY MANIFEST.in ./
COPY README.md ./
COPY setup.cfg ./
COPY setup.py ./
COPY fasta_api ./fasta_api/

RUN pip3 install --no-cache-dir .

WORKDIR /

ENTRYPOINT ["python3", "-u", "-m", "fasta_api"]
