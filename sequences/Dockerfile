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
COPY sequences/ ./sequences/
COPY proto/ ./proto/

# install the package dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# install (and implicitly build) the package. --no-build-isolation makes the
# proto codegen use the grpcio-tools pinned in requirements.txt instead of the
# latest one a default isolated build would pull in; otherwise the generated
# *_pb2 gencode can outrun the pinned protobuf runtime and the service crashes
# on import with a Protobuf gencode/runtime version error.
RUN pip3 install --no-cache-dir --no-build-isolation .

WORKDIR /

ENTRYPOINT ["python3", "-u", "-m", "sequences"]
