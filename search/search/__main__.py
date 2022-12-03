#!/usr/bin/env python

# Python
import argparse
import asyncio
import logging
import os
import signal
# dependencies
import uvloop
# module
import search
from search.grpc_server import run_grpc_server
from search.http_server import run_http_server
from search.query_parser import makeQueryParser
from search.request_handler import RequestHandler


LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
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
    prog=search.__name__,
    description='A microservice for resolving search queries.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
    '--version',
    action='version',
    version=f'%(prog)s {search.__version__}',
  )

  # logging args
  loglevel_envvar = 'LOG_LEVEL'
  parser.add_argument(
    '--log-level',
    dest='log_level',
    action=EnvArg,
    envvar=loglevel_envvar,
    type=str,
    choices=list(LOG_LEVELS.keys()),
    default='WARNING',
    help=('What level of events should be logged (can also be specified using '
          f'the {loglevel_envvar} environment variable).'))
  logfile_envvar = 'LOG_FILE'
  parser.add_argument(
    '--log-file',
    dest='log_file',
    action=EnvArg,
    default=argparse.SUPPRESS,  # removes "(default: None)" from help text
    envvar=logfile_envvar,
    type=str,
    help=('The file events should be logged in (can also be specified using '
          f'the {logfile_envvar} environment variable).'))

  # Async HTTP args
  parser.add_argument('--no-http', dest='nohttp', action='store_true', help='Don\'t run the HTTP server.')
  parser.set_defaults(nohttp=False)
  hhost_envvar = 'HTTP_HOST'
  parser.add_argument('--hhost', action=EnvArg, envvar=hhost_envvar, type=str, default='localhost', help=f'The HTTP server host (can also be specified using the {hhost_envvar} environment variable).')
  hport_envvar = 'HTTP_PORT'
  parser.add_argument('--hport', action=EnvArg, envvar=hport_envvar, type=str, default='8080', help=f'The HTTP server port (can also be specified using the {hport_envvar} environment variable).')

  # gRPC args
  parser.add_argument('--no-grpc', dest='nogrpc', action='store_true', help='Don\'t run the gRPC server.')
  parser.set_defaults(nogrpc=False)
  ghost_envvar = 'GRPC_HOST'
  parser.add_argument('--ghost', action=EnvArg, envvar=ghost_envvar, type=str, default='[::]', help=f'The gRPC server host (can also be specified using the {ghost_envvar} environment variable).')
  gport_envvar = 'GRPC_PORT'
  parser.add_argument('--gport', action=EnvArg, envvar=gport_envvar, type=str, default='8081', help=f'The gRPC server port (can also be specified using the {gport_envvar} environment variable).')

  # Inter-microservice communication args
  geneaddr_envvar = 'GENE_SEARCH_ADDR'
  parser.add_argument('--geneaddr', action=EnvArg, envvar=geneaddr_envvar, type=str, required=True, help=f'The address of the gene search microservice (can also be specified using the {geneaddr_envvar} environment variable).')
  chromosomeaddr_envvar = 'CHROMOSOME_SEARCH_ADDR'
  parser.add_argument('--chromosomeaddr', action=EnvArg, envvar=chromosomeaddr_envvar, type=str, required=True, help=f'The address of the chromosome search microservice (can also be specified using the {chromosomeaddr_envvar} environment variable).')
  regionaddr_envvar = 'CHROMOSOME_REGION_ADDR'
  parser.add_argument('--regionaddr', action=EnvArg, envvar=regionaddr_envvar, type=str, required=True, help=f'The address of the chromosome region microservice (can also be specified using the {regionaddr_envvar} environment variable).')

  # query parser args
  parser.add_argument('--chars', type=str, default='._-', help='Special characters allowed in gene and chromosome names.')

  return parser.parse_args()


# graceful shutdown
async def shutdown(loop, signal=None):
  # report what signal (if any) initiated the shutdown
  if signal:
    logging.info(f'Received exit signal {signal.name}')
  # cancel all running tasks (they know how to cleanup themselves)
  logging.info('Cancelling outstanding tasks')
  tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
  [task.cancel() for task in tasks]
  await asyncio.gather(*tasks, return_exceptions=True)
  # stop the asyncio loop
  loop.stop()


# the asyncio exception handler that will initiate a shutdown
def handleException(loop, context):
  msg = context.get('exception', context['message'])
  logging.critical(f'Caught exception: {msg}')
  logging.info('Shutting down')
  asyncio.create_task(shutdown(loop))


def main():

  # parse the command line arguments / environment variables
  args = parseArgs()
  if args.nohttp and args.nogrpc:
    exit('--no-http and --no-grpc can\'t both be given')

  # setup logging
  log_config = {
      'format': '%(asctime)s,%(msecs)d %(levelname)s: %(message)s',
      'datefmt': '%H:%M:%S',
      'level': LOG_LEVELS[args.log_level],
    }
  if 'log_file' in args:
    log_config['filename'] = args.log_file
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
    # create the query parser
    query_parser = makeQueryParser(args.chars)
    # create the request handler
    handler = RequestHandler(query_parser, args.geneaddr, args.chromosomeaddr, args.regionaddr)
    # start the HTTP server
    if not args.nohttp:
      loop.create_task(run_http_server(args.hhost, args.hport, handler))
    # start the gRPC server
    if not args.nogrpc:
      loop.create_task(run_grpc_server(args.ghost, args.gport, handler))
    # run the main loop
    loop.run_forever()
  # catch exceptions not handled by asyncio
  except Exception as e:
    context = {'exception': e, 'message': str(e)}
    loop.call_exception_handler(context)
  # finalize the shutdown
  finally:
    loop.close()
    logging.info('Successfully shutdown.')


if __name__ == '__main__':
  main()
