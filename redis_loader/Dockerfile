FROM python:3.13.7-alpine3.22 AS builder

RUN apk add --no-cache \
  gcc \
  musl-dev \
  postgresql-dev

WORKDIR /app

COPY LICENSE ./
COPY README.md ./
COPY pyproject.toml ./
COPY requirements.txt ./
COPY redis_loader/ ./redis_loader/

# install the package dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# install the package
RUN pip3 install --no-cache-dir .

COPY ./docker-entrypoint-initdb.d/ /docker-entrypoint-initdb.d/
COPY ./entrypoint.sh /entrypoint.sh

WORKDIR /app

ENTRYPOINT ["/entrypoint.sh"]
