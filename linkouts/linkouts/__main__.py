#!/usr/bin/env python

# Python
import argparse
import asyncio
import os
import uvloop
# module
import linkouts
from linkouts.http_server import run_http_server
from linkouts.request_handler import RequestHandler


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
    prog=linkouts.__name__,
    description='A microservice that returns the hyperlink info objects corresponding to the given gene id.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
    '--version',
    action='version',
    version=f'%(prog)s {linkouts.__version__}',
  )

  # Async HTTP args
  hhost_envvar = 'HTTP_HOST'
  parser.add_argument('--hhost', action=EnvArg, envvar=hhost_envvar, type=str, default='127.0.0.1', help=f'The HTTP server host (can also be specified using the {hhost_envvar} environment variable).')
  hport_envvar = 'HTTP_PORT'
  parser.add_argument('--hport', action=EnvArg, envvar=hport_envvar, type=str, default='8880', help=f'The HTTP server port (can also be specified using the {hport_envvar} environment variable).')
  lglob_root_envvar = ''
  parser.add_argument('--lglob_root', action=EnvArg, envvar=lglob_root_envvar, type=str, default='/data', help=f'The root folder to be searched for README.*.yml files containing linkout specifications')

  return parser.parse_args()


# the main coroutine that starts the various program tasks
def main_coroutine(args):
  tasks = []
  handler = RequestHandler(args.lglob_root)
  #http_task = asyncio.create_task(run_http_server(args.hhost, args.hport, handler))
  run_http_server(args.hhost, args.hport, handler)
  #tasks.append(http_task)
  #await asyncio.gather(*tasks)


def main():

  # parse the command line arguments / environment variables
  args = parseArgs()

  # initialize asyncio
  uvloop.install()
  #loop = asyncio.get_event_loop()

  # run the program
  #loop.create_task(main_coroutine(args))
  main_coroutine(args)
  #loop.run_forever()


if __name__ == '__main__':
  main()
