# GCV Microservices
This repository contains a microservices implementation of the
[Genome Context Viewer](https://github.com/legumeinfo/lis_context_viewer) server.
Rather than interacting directly with a
[Chado](http://gmod.org/wiki/Chado_-_Getting_Started) database, scripts are
provided to load the relevant data from Chado into a Redis database to
improve performance (see the
[Wiki](https://github.com/legumeinfo/lis_gcv_microservices/wiki/Redis-Schema)
for a description of the schema).


## Installation
The server is implement in [Python 3](https://www.python.org/).
As such, the easiest way to install the server is inside of a
[Python Virtual Environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

Once Python and Python Virtual Environments are installed, create and activate a
new Python virtual environment as follows:

    $ virtualenv venv
    $ . ./venv/bin/active

Your command line should now look like this:

    (venv) $

All the dependencies required to run the server can now be installed in the
virtual environment as follows:

    (venv) $ pip install -r requirements.txt


## Loading Data
The Redis database can be populated from an existing Chado database.
To do so, use `chado_to_redis.py`. For example:

    (venv) $ python chado_to_redis.py 


## Running the Server
To run the server, activate the virtual environment and then run the application
script:

    (venv) $ python app.py

Currently, the port is hard coded the `1234` and the application is configured
to connect to the Redis database via the Unix socket `/run/redis/redis.sock`.
These settings will be made configurable in the future.

When you are done using the application, you can exit the Python virtual
environment you closing your terminal or with the following command:

    (venv) $ deactivate
