#!/usr/bin/env python

# Python
import argparse
import os
import pathlib
from collections import defaultdict
# module
from loaders import RediSearchLoader, loadFromChado, loadFromGFF


def chado(redisearch_loader, args):
  '''
  Calls the Chado loader with the relevant command-line arguments.

  Parameters:
    redisearch_loader (RediSearchLoader): The loader to use to load data into
      RediSearch.
    args (argsparse.Namespace): A namespace mapping parsed arguments to their values.
  '''

  loadFromChado(
    redisearch_loader,
    args.postgres_database,
    args.postgres_user,
    args.postgres_password,
    args.postgres_host,
    args.postgres_port,
    args.uniquename,
  )


def gff(redisearch_loader, args):
  '''
  Calls the GFF loader with the relevant command-line arguments.

  Parameters:
    redisearch_loader (RediSearchLoader): The loader to use to load data into
      RediSearch.
    args (argsparse.Namespace): A namespace mapping parsed arguments to their values.
  '''

  loadFromGFF(
    redisearch_loader,
    args.genus,
    args.species,
    args.strain,
    args.chromosome_gff,
    args.gene_gff,
    args.gfa,
  )


class EnvAction(argparse.Action):
  '''
  A class that loads argument values from environment variables, resulting in a
  value priority: command line > environment variable > default value
  '''

  def __init__(self, envvar, required=False, default=None, **kwargs):
    if envvar in os.environ:
      default = os.environ[envvar]
    if required and default is not None:
      required = False
    super(EnvAction, self)\
      .__init__(default=default, required=required, **kwargs)

  def __call__(self, parser, namespace, values, option_string=None):
    setattr(namespace, self.dest, values)


def parseArgs():
  '''
  Parses command-line arguments.

  Returns:
    argparse.Namespace: A namespace mapping parsed arguments to their values.
  '''

  # create the parser and command subparser
  parser = argparse.ArgumentParser(
    description=('Loads data from a Chado (PostreSQL) database or GFF files '
                'into a RediSearch index for use by GCV microservices.'
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  subparsers = \
    parser.add_subparsers(title='commands', dest='command', required=True)

  # Redis args
  rdb_envvar = 'REDIS_DB'
  parser.add_argument(
    '--redis-db',
    dest='redis_db',
    action=EnvAction,
    envvar=rdb_envvar,
    type=int,
    default=0,
    help=(f'The Redis database (can also be specified using the {rdb_envvar} '
          'environment variable).'))
  rpassword_envvar = 'REDIS_PASSWORD'
  parser.add_argument(
    '--redis-password',
    dest='redis_password',
    action=EnvAction,
    envvar=rpassword_envvar,
    type=str,
    default='',
    help=('The Redis password (can also be specified using the '
          f'{rpassword_envvar} environment variable).'))
  rhost_envvar = 'REDIS_HOST'
  parser.add_argument(
    '--redis-host',
    dest='redis_host',
    action=EnvAction,
    envvar=rhost_envvar,
    type=str,
    default='localhost',
    help=(f'The Redis host (can also be specified using the {rhost_envvar} '
          'environment variable).'))
  rport_envvar = 'REDIS_PORT'
  parser.add_argument(
    '--redis-port',
    dest='redis_port',
    action=EnvAction,
    envvar=rport_envvar,
    type=int,
    default=6379,
    help=(f'The Redis port (can also be specified using the {rport_envvar} '
          'environment variable).'))
  rchunksize_envvar = 'REDIS_CHUNK_SIZE'
  parser.add_argument(
    '--redis-chunksize',
    dest='redis_chunksize',
    action=EnvAction,
    envvar=rchunksize_envvar,
    type=int,
    default=100,
    help=('The chunk size to be used for Redis batch processing (can also be '
          f'specified using the {rchunksize_envvar} environment variable).'))
  parser.add_argument(
    '--no-save',
    dest='nosave',
    action='store_true',
    help='Don\'t save the Redis database to disk after loading.')
  parser.set_defaults(nosave=False)
  load_types = {
      'new': 'Will only load indexes if they have to be created first.',
      'reload': 'Will remove existing indexes before loading data.',
      'append': 'Will add data to an existing index or create a new index.',
    }
  # TODO: prevent argparse from removing line breaks in help text
  loadtype_help = ''.join([
      f'\t{type} - {description} \n '
      for type, description in load_types.items()
    ])
  loadtype_envvar = 'LOAD_TYPE'
  parser.add_argument(
    '--load-type',
    dest='load_type',
    action=EnvAction,
    envvar=loadtype_envvar,
    type=str,
    choices=list(load_types.keys()),
    default='append',
    help=(f'How the data should be loaded into Redis:\n{loadtype_help}'
          f'(can also be specified using the {loadtype_envvar} environment '
          'variable).'))

  # Chado args
  chado_parser = subparsers.add_parser(
      'chado',
      help='Load data from a Chado (PostgreSQL) database.',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
  chado_parser.set_defaults(command=chado)
  pdb_envvar = 'POSTGRES_DATABASE'
  chado_parser.add_argument(
    '--postgres-database',
    dest='postgres_database',
    action=EnvAction,
    envvar=pdb_envvar,
    type=str,
    default='chado',
    help=('The PostgreSQL database (can also be specified using the '
          f'{pdb_envvar} environment variable).'))
  puser_envvar = 'POSTGRES_USER'
  chado_parser.add_argument(
    '--postgres-user',
    dest='postgres_user',
    action=EnvAction,
    envvar=puser_envvar,
    type=str,
    default='chado',
    help=('The PostgreSQL username (can also be specified using the '
          f'{puser_envvar} environment variable).'))
  ppassword_envvar = 'POSTGRES_PASSWORD'
  chado_parser.add_argument(
    '--postgres-password',
    dest='postgres_password',
    action=EnvAction,
    envvar=ppassword_envvar,
    type=str,
    default=None,
    help=('The PostgreSQL password (can also be specified using the '
          f'{ppassword_envvar} environment variable).'))
  phost_envvar = 'POSTGRES_HOST'
  chado_parser.add_argument(
    '--postgres-host',
    dest='postgres_host',
    action=EnvAction,
    envvar=phost_envvar,
    type=str,
    default='localhost',
    help=('The PostgreSQL host (can also be specified using the '
          f'{phost_envvar} environment variable).'))
  pport_envvar = 'POSTGRES_PORT'
  chado_parser.add_argument(
    '--postgres-port',
    dest='postgres_port',
    action=EnvAction,
    envvar=pport_envvar,
    type=int,
    default=5432,
    help=('The PostgreSQL port (can also be specified using the '
          f'{pport_envvar} environment variable).'))
  chado_parser.add_argument(
    '--uniquename',
    action='store_true',
    help=('Load names from the uniquename field of the Chado feature table, '
          'otherwise use the name field.'))
  chado_parser.set_defaults(uniquename=False)

  # GFF args
  gff_parser = subparsers.add_parser(
      'gff',
      help='Load data GFF files.',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
  gff_parser.set_defaults(command=gff)
  genus_envvar = 'GENUS'
  gff_parser.add_argument(
    '--genus',
    required=True,
    action=EnvAction,
    envvar=genus_envvar,
    type=str,
    default=argparse.SUPPRESS,  # removes "(default: None)" from help text
    help=('The genus of the organism being loaded (can also be specified using '
         f'the {genus_envvar} environment variable).'))
  species_envvar = 'SPECIES'
  gff_parser.add_argument(
    '--species',
    required=True,
    action=EnvAction,
    envvar=species_envvar,
    type=str,
    default=argparse.SUPPRESS,  # removes "(default: None)" from help text
    help=('The species of the organism being loaded (can also be specified '
         f'using the {species_envvar} environment variable).'))
  strain_envvar = 'STRAIN'
  gff_parser.add_argument(
    '--strain',
    action=EnvAction,
    envvar=strain_envvar,
    type=str,
    help=('The strain of the organism being loaded (can also be specified '
         f'using the {strain_envvar} environment variable).'))
  gffgene_envvar = 'GENE_GFF_FILE'
  gff_parser.add_argument(
    '--gene-gff',
    dest='gene_gff',
    required=True,
    action=EnvAction,
    envvar=gffgene_envvar,
    type=pathlib.Path,
    default=argparse.SUPPRESS,  # removes "(default: None)" from help text
    help=('The GFF file containing gene records (can also be specified using '
         f'the {gffgene_envvar} environment variable).'))
  gffchr_envvar = 'CHR_GFF_FILE'
  gff_parser.add_argument(
    '--chromosome-gff',
    dest='chromosome_gff',
    required=True,
    action=EnvAction,
    envvar=gffchr_envvar,
    type=pathlib.Path,
    default=argparse.SUPPRESS,  # removes "(default: None)" from help text
    help=('The GFF file containing chromosome/supercontig records (can also be '
         f'specified using the {gffchr_envvar} environment variable).'))
  gfa_envvar = 'GFA_FILE'
  gff_parser.add_argument(
    '--gfa',
    required=True,
    action=EnvAction,
    envvar=gfa_envvar,
    type=pathlib.Path,
    default=argparse.SUPPRESS,  # removes "(default: None)" from help text
    help=('The GFA file containing gene-gene family associations (can also be '
         f'specified using the {gfa_envvar} environment variable).'))

  return parser.parse_args()


if __name__ == '__main__':

  # parse command-line arguments
  args = parseArgs()

  # run the specified command in the context of the RediSearch loader
  kwargs = {
      'host': args.redis_host,
      'port': args.redis_port,
      'db': args.redis_db,
      'password': args.redis_password,
      'load_type': args.load_type,
      'no_save': args.no_save,
      'chunk_size': args.chunk_size,
    }
  with RediSearchLoader(**kwargs) as loader:
    args.command(loader, args)
