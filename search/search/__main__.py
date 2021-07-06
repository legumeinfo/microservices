#!/usr/bin/env python

# Python
import argparse
import asyncio
import os
import uvloop
# module
import search
from search.grpc_server import run_grpc_server
from search.http_server import run_http_server
from search.query_parser import makeQueryParser
from search.request_handler import RequestHandler


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
    description='A microservice for resolving GCV search queries.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
    '--version',
    action='version',
    version=f'%(prog)s {search.__version__}',
  )

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


async def main_coroutine(args):
  query_parser = makeQueryParser(args.chars)
  handler = RequestHandler(query_parser, args.geneaddr, args.chromosomeaddr, args.regionaddr)
  tasks = []
  if not args.nohttp:
    http_coro = run_http_server(args.hhost, args.hport, handler)
    http_task = asyncio.create_task(http_coro)
    tasks.append(http_task)
  if not args.nogrpc:
    grpc_coro = run_grpc_server(args.ghost, args.gport, handler)
    grpc_task = asyncio.create_task(grpc_coro)
    tasks.append(grpc_task)
  await asyncio.gather(*tasks)


def main():

  # parse the command line arguments / environment variables
  args = parseArgs()
  if args.nohttp and args.nogrpc:
    exit('--no-http and --no-grpc can\'t both be given')

  # initialize asyncio
  uvloop.install()
  loop = asyncio.get_event_loop()

  # run the program
  loop.create_task(main_coroutine(args))
  loop.run_forever()


if __name__ == '__main__':
  main()
