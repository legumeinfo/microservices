FROM python:3.13.7-slim-trixie

# install gcc and other build requirements
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY LICENSE ./
COPY README.md ./
COPY pyproject.toml ./
COPY requirements.txt ./
COPY search/ ./search/
COPY proto/ ./proto/

# install the package dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# generate the gRPC modules into the package; grpcio-tools, from requirements.txt,
# supplies protobuf's well-known types itself
RUN python3 -m grpc_tools.protoc --proto_path=proto \
      --python_out=search/proto --grpc_python_out=search/proto \
      $(find proto -name '*.proto')

# install the package itself; its dependencies are installed above
RUN pip3 install --no-cache-dir --no-deps .

WORKDIR /

# fail the build, not the container, if the generated modules don't load
RUN python3 -c "import search.grpc_server"

ENTRYPOINT ["python3", "-u", "-m", "search"]
