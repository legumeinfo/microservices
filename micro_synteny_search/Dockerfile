FROM python:3.9-slim-buster

WORKDIR /app

COPY INSTALL ./
COPY LICENSE ./
COPY MANIFEST.in ./
COPY README.md ./
COPY setup.cfg ./
COPY setup.py ./
COPY micro_synteny_search/ ./micro_synteny_search/

RUN pip install --no-cache-dir .

COPY . .

ENTRYPOINT ["python3", "-u", "-m", "micro_synteny_search"]
