FROM python:3.13.7-slim-trixie

# install gcc and other build requirements
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY INSTALL ./
COPY LICENSE ./
COPY MANIFEST.in ./
COPY README.md ./
COPY setup.cfg ./
COPY setup.py ./
COPY requirements.txt ./
COPY genes/ ./genes/
COPY proto/ ./proto/

# install the package dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# install (and implicitly build) the package. --no-build-isolation makes the
# proto codegen use the pinned grpcio-tools from requirements.txt, not the latest
# one a default isolated build would pull in (which can generate *_pb2 gencode
# newer than the pinned protobuf runtime → crash on import). See ARCHITECTURE §9.2.
RUN pip3 install --no-cache-dir --no-build-isolation .

WORKDIR /

ENTRYPOINT ["python3", "-u", "-m", "genes"]
