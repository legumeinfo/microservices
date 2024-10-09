# DSCensor
Provide Web Facing RESTFUL API of LIS-Datastore Formatted Nodes

# Setup

Generate a set of DSCensor nodes using LIS-autocontent. This will be in "./autocontent" by default.

[Generate DSCensor Nodes](https://github.com/legumeinfo/LIS-autocontent)

The "./autocontent" directory will be read by the app when docker compose is run.

# Docker

Run local development build from cwd.

`sudo docker compose -f ./compose.dev.yaml up`

Run production build from tagged image.

`sudo docker compose -f ./compose.prod.yaml up`

# Develop

Install pre-commit hooks before developing. The github will force you to subscribe on PR if you don't so please do!

`pre-commit install`
