FROM python:3.13.7-alpine3.21 AS builder

RUN apk add --no-cache \
  gcc \
  musl-dev \
  postgresql-dev

WORKDIR /app

COPY INSTALL ./
COPY LICENSE ./
COPY MANIFEST.in ./
COPY README.md ./
COPY setup.cfg ./
COPY setup.py ./
COPY requirements.txt ./
COPY redis_loader/ ./redis_loader/

# install the package dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# install (and implicitly build) the package
RUN pip3 install --no-cache-dir .

COPY ./docker-entrypoint-initdb.d/ /docker-entrypoint-initdb.d/
COPY ./entrypoint.sh /entrypoint.sh

WORKDIR /app

ENTRYPOINT ["/entrypoint.sh"]
