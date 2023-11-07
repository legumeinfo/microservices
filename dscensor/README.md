# DSCensor
Process LIS Datastore and Provide Web Facing RESTFUL API

# Run

Run the application using aiohttp.web

`python -m aiohttp.web dscensor.app:create_app`

# Docker

Build the docker container locally

`sudo docker build -t dscensor-openapi .`

Run the container

`sudo docker run -p 127.0.0.1:8080:8080 dscensor-openapi`

# Develop

Install pre-commit hooks before developing

`pre-commit install`
