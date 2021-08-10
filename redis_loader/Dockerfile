FROM python:3.9-alpine AS builder

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
COPY redis_loader/ ./redis_loader/

RUN pip3 install --no-cache-dir .

FROM python:3.9-alpine3.12

RUN apk add --no-cache libpq

COPY --from=builder /usr/local/lib/python3.9/site-packages/ /usr/local/lib/python3.9/site-packages/

WORKDIR /app

ENTRYPOINT ["python", "-m", "redis_loader"]
