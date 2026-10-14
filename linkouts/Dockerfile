FROM python:3.13.7-slim-trixie

WORKDIR /app

COPY LICENSE ./
COPY README.md ./
COPY pyproject.toml ./
COPY linkouts/ ./linkouts/

# install the package
RUN pip3 install --no-cache-dir .

WORKDIR /

ENTRYPOINT ["python3", "-u", "-m", "linkouts"]
