FROM python:3.13.7-slim-trixie

# install gcc and other build requirements
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    apt-get install -y --no-install-recommends locales && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY INSTALL ./
COPY LICENSE ./
COPY MANIFEST.in ./
COPY README.md ./
COPY setup.cfg ./
COPY setup.py ./
COPY requirements.txt ./
COPY dscensor/ ./dscensor/
COPY openapi/ ./openapi/

# Python 3.13 base images no longer ship setuptools by default, and
# rororo→openapi-core→openapi-spec-validator==0.4.0 imports `pkg_resources`
# at module load. That module was removed in setuptools 81; pin <81 to
# keep it around. (See requirements.txt for the full rationale.)
RUN pip3 install --no-cache-dir 'setuptools<81'

# install the package dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# install (and implicitly build) the package
RUN pip3 install --no-cache-dir .

WORKDIR /

ENTRYPOINT ["python3", "-u", "-m", "dscensor"]
