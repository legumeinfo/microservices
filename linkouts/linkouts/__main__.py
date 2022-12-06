#!/usr/bin/env python

# Python
import argparse
import asyncio
import logging
import os
import uvloop
# module
import linkouts
from linkouts.http_server import run_http_server
from linkouts.request_handler import RequestHandler

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
    prog=linkouts.__name__,
    description='A microservice that returns the hyperlink info objects corresponding to the given gene id.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
    '--version',
    action='version',
    version=f'%(prog)s {linkouts.__version__}',
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
  hhost_envvar = 'HTTP_HOST'
  parser.add_argument('--hhost', action=EnvArg, envvar=hhost_envvar, type=str, default='127.0.0.1', help=f'The HTTP server host (can also be specified using the {hhost_envvar} environment variable).')
  hport_envvar = 'HTTP_PORT'
  parser.add_argument('--hport', action=EnvArg, envvar=hport_envvar, type=str, default='8880', help=f'The HTTP server port (can also be specified using the {hport_envvar} environment variable).')
  lglob_root_envvar = ''
  parser.add_argument('--lglob_root', action=EnvArg, envvar=lglob_root_envvar, type=str, default='/data', help=f'The root folder to be searched for linkouts.*.yml files containing linkout specifications')

  return parser.parse_args()


# the main coroutine that starts the various program tasks
def main_coroutine(args):
  tasks = []
  handler = RequestHandler(args.lglob_root)
  run_http_server(args.hhost, args.hport, handler)

def main():

  # parse the command line arguments / environment variables
  args = parseArgs()

  # initialize asyncio
  #uvloop.install()
  loop = uvloop.new_event_loop()
  asyncio.set_event_loop(loop)

  # run the program
  main_coroutine(args)

# the asyncio exception handler that will initiate a shutdown
def handleException(loop, context):
  msg = context.get('exception', context['message'])
  logging.critical(f'Caught exception: {msg}')
  logging.info('Shutting down')
  asyncio.create_task(shutdown(loop))


if __name__ == '__main__':
  main()
