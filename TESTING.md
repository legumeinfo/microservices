# Testing
In each microservice's directory, run:

```
./run-tests.sh
```

It expects [gcv-docker-compose]() to be the parent directory. Wherever that repo is on your machine:

```
GCV_DOCKER_COMPOSE=/home/mrbean/github/gcv-docker-compose ./run-tests.sh
```

File structure overview:

```
<some-service>/
├── tests/
│   ├── test_<some-class>.py
│   └── conftest.py        # Fixtures
├── pytest.ini             # Configuration
├── requirements-test.txt  # Test dependencies
└── Dockerfile.test        # Docker image for running tests
```