#!/usr/bin/env python

# Python
import argparse
import asyncio
import logging
import os
import signal

import aiohttp

# dependencies
import uvloop

# module
import dscensor
from dscensor.http_server import run_http_server
from dscensor.request_handler import RequestHandler

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


# a class that loads argument values from command line variables, resulting in a
# value priority: command line > environment variable > default value
class EnvArg(argparse.Action):
    def __init__(self, envvar, required=False, default=None, **kwargs):
        if envvar in os.environ:
            default = os.environ[envvar]
        if required and default is not None:
            required = False
        super(EnvArg, self).__init__(default=default, required=required, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


def parseArgs():
    # create the parser
    parser = argparse.ArgumentParser(
        prog=dscensor.__name__,
        description="""A Microservice that provides data for the DSCensor Web App.""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {dscensor.__version__}",
    )

    # logging args
    loglevel_envvar = "LOG_LEVEL"
    parser.add_argument(
        "--log-level",
        dest="log_level",
        action=EnvArg,
        envvar=loglevel_envvar,
        type=str,
        choices=list(LOG_LEVELS.keys()),
        default="WARNING",
        help=f"""
        What level of events should be logged (can also be specified using the
        {loglevel_envvar} environment variable).
        """,
    )
    logfile_envvar = "LOG_FILE"
    parser.add_argument(
        "--log-file",
        dest="log_file",
        action=EnvArg,
        default=argparse.SUPPRESS,  # removes "(default: None)" from help text
        envvar=logfile_envvar,
        type=str,
        help=f"""
        The file events should be logged in (can also be specified using the
        {logfile_envvar} environment variable).
        """,
    )

    # Async HTTP args
    host_envvar = "HTTP_HOST"
    parser.add_argument(
        "--host",
        action=EnvArg,
        envvar=host_envvar,
        type=str,
        default="127.0.0.1",
        help=f"""
        The HTTP server host (can also be specified using the {host_envvar} environment
        variable).
        """,
    )
    port_envvar = "HTTP_PORT"
    parser.add_argument(
        "--port",
        action=EnvArg,
        envvar=port_envvar,
        type=str,
        default="8880",
        help=f"""
        The HTTP server port (can also be specified using the {port_envvar} environment
        variable).
        """,
    )
    nodes_envvar = "NODES"
    parser.add_argument(
        "--nodes",
        action=EnvArg,
        envvar=nodes_envvar,
        type=str,
        default="./autocontent",
        help=f"""
        TODO (can also be specified using the {nodes_envvar} environment variable).
        """,
    )

    return parser.parse_args()


# graceful shutdown
async def shutdown(loop, signal=None):
    # report what signal (if any) initiated the shutdown
    if signal:
        logging.info(f"Received exit signal {signal.name}")
    # cancel all running tasks (they know how to cleanup themselves)
    logging.info("Cancelling outstanding tasks")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    # stop the asyncio loop
    loop.stop()


# the asyncio exception handler that will initiate a shutdown
def handleException(loop, context):
    msg = context.get("exception", context["message"])
    logging.critical(f"Caught exception: {msg}")
    logging.info("Shutting down")
    asyncio.create_task(shutdown(loop))


def main():
    # parse the command line arguments / environment variables
    args = parseArgs()

    # setup logging
    log_config = {
        "format": "%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
        "datefmt": "%H:%M:%S",
        "level": LOG_LEVELS[args.log_level],
    }
    if "log_file" in args:
        log_config["filename"] = args.log_file
    logging.basicConfig(**log_config)

    # initialize asyncio
    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)

    # setup asyncio exception handling
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: loop.create_task(shutdown(loop, signal=s))
        )
    loop.set_exception_handler(handleException)

    # run the program
    try:
        handler = RequestHandler(args.nodes)
        loop.create_task(run_http_server(args.host, args.port, handler))
        loop.run_forever()
    # catch exceptions not handled by asyncio
    except Exception as e:
        context = {"exception": e, "message": str(e)}
        loop.call_exception_handler(context)
    # finalize the shutdown
    finally:
        loop.close()
        logging.info("Successfully shutdown.")


if __name__ == "__main__":
    main()
