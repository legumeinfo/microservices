FROM python:3.11.1-slim-buster

# install gcc and other build requirements
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    apt-get install -y --no-install-recommends locales && \
    rm -rf /var/lib/apt/lists/*

ADD . /app

WORKDIR /app

# install the package dependencies
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install lis-autocontent

# Set the locale
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8 
ENV LANGUAGE en_US:en 
ENV LC_ALL en_US.UTF-8

# install (and implicitly build) the package

CMD ["dscensor"]
EXPOSE 8080
