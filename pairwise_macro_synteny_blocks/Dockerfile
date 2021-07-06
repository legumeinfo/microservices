FROM python:3.9-slim-buster

WORKDIR /app

COPY INSTALL ./
COPY LICENSE ./
COPY MANIFEST.in ./
COPY README.md ./
COPY setup.cfg ./
COPY setup.py ./
COPY pairwise_macro_synteny_blocks/ ./pairwise_macro_synteny_blocks/

RUN pip install --no-cache-dir .

COPY . .

ENTRYPOINT ["python3", "-m", "pairwise_macro_synteny_blocks"]
