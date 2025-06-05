FROM python:3.13.4

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
COPY chromosome/ ./chromosome/
COPY proto/ ./proto/

# install the package dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# install (and implicitly build) the package
RUN pip3 install --no-cache-dir .

WORKDIR /

ENTRYPOINT ["python3", "-u", "-m", "chromosome"]
