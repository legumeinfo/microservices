FROM python:3.11.1-slim-buster

# install gcc and other build requirements
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    apt-get install -y --no-install-recommends git-all && \
    apt-get install -y --no-install-recommends locales && \
    rm -rf /var/lib/apt/lists/*

ADD . /app

WORKDIR /app

# checkout set tag later after fetch
#RUN git remote add github-upstream https://github.com/legumeinfo/DSCensor.git
#RUN git fetch github-upstream
#RUN git checkout github-upstream/openapi
RUN git fetch origin
RUN git checkout origin/openapi
RUN git submodule update --init

# install the package dependencies
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install lis-autocontent

# Set the locale
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8 
ENV LANGUAGE en_US:en 
ENV LC_ALL en_US.UTF-8

#RUN python ./LIS-autocontent/setup.py install

# populate objects for graphDB
RUN lis-autocontent populate-dscensor --from_github ./datastore-metadata/ --taxa_list ./jekyll-legumeinfo/_data/taxon_list.yml --nodes_out ./autocontent

# install (and implicitly build) the package

CMD ["python", "-m", "aiohttp.web", "-H", "0.0.0.0", "dscensor.app:create_app"]
EXPOSE 8080
