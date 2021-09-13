FROM python:3.9-slim-buster

WORKDIR /app

COPY INSTALL ./
COPY LICENSE ./
COPY MANIFEST.in ./
COPY README.md ./
COPY setup.cfg ./
COPY setup.py ./
COPY macro_synteny_blocks/ ./macro_synteny_blocks/

RUN pip install --no-cache-dir .

WORKDIR /

ENTRYPOINT ["python3", "-u", "-m", "macro_synteny_blocks"]
