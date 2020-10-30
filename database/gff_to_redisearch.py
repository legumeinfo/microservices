#!/usr/bin/env python

# Python
import argparse
import os
import re
import sys
from collections import defaultdict
# dependencies
import redisearch
import gffutils
# module
from database import connectToRedis


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
    description='Loads data from a chromosomal GFF file, an annotation (gene) GFF file, and a GFA file into a RediSearch index for use by the GCV search microservices.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  # organism args
  genus_envvar = 'GENUS'
  parser.add_argument('--genus', action=EnvArg, required=True, envvar=genus_envvar, type=str, default=None, help=f'The genus of the organism being loaded (can also be specified using the {genus_envvar} environment variable).')
  species_envvar = 'SPECIES'
  parser.add_argument('--species', action=EnvArg, required=True, envvar=species_envvar, type=str, default=None, help=f'The species of the organism being loaded (can also be specified using the {species_envvar} environment variable).')
  
  # GFF/GFA file args
  gffgene_envvar = 'GENE_GFF_FILE'
  parser.add_argument('--gffgene', action=EnvArg, required=True, envvar=gffgene_envvar, type=str, default=None, help=f'The GFF file containing gene records (can also be specified using the {gffgene_envvar} environment variable).')
  gffchr_envvar = 'CHR_GFF_FILE'
  parser.add_argument('--gffchr', action=EnvArg, required=True, envvar=gffchr_envvar, type=str, default=None, help=f'The GFF file containing chromosome/supercontig records (can also be specified using the {gffchr_envvar} environment variable).')
  gfa_envvar = 'GFA_FILE'
  parser.add_argument('--gfa', action=EnvArg, required=True, envvar=gfa_envvar, type=str, default=None, help=f'The GFA file containing gene-gene family associations (can also be specified using the {gfa_envvar} environment variable).')
  
  # Redis args
  rdb_envvar = 'REDIS_DB'
  parser.add_argument('--rdb', action=EnvArg, envvar=rdb_envvar, type=int, default=0, help=f'The Redis database (can also be specified using the {rdb_envvar} environment variable).')
  rpassword_envvar = 'REDIS_PASSWORD'
  parser.add_argument('--rpassword', action=EnvArg, envvar=rpassword_envvar, type=str, default='', help=f'The Redis password (can also be specified using the {rpassword_envvar} environment variable).')
  rhost_envvar = 'REDIS_HOST'
  parser.add_argument('--rhost', action=EnvArg, envvar=rhost_envvar, type=str, default='localhost', help=f'The Redis host (can also be specified using the {rhost_envvar} environment variable).')
  rport_envvar = 'REDIS_PORT'
  parser.add_argument('--rport', action=EnvArg, envvar=rport_envvar, type=int, default=6379, help=f'The Redis port (can also be specified using the {rport_envvar} environment variable).')
  rchunksize_envvar = 'REDIS_CHUNK_SIZE'
  parser.add_argument('--rchunksize', action=EnvArg, envvar=rchunksize_envvar, type=int, default=100, help=f'The chunk size to be used for Redis batch processing (can also be specified using the {rchunksize_envvar} environment variable).')
  parser.add_argument('--no-reload', dest='noreload', action='store_true', help='Don\'t load a search index if it already exists.')
  parser.set_defaults(noreload=False)
  parser.add_argument('--no-save', dest='nosave', action='store_true', help='Don\'t save the Redis database to disk after loading.')
  parser.set_defaults(nosave=False)

  return parser.parse_args()


def _replacePreviousPrintLine(newline):
  sys.stdout.write('\033[F') # back to previous line
  sys.stdout.write('\033[K') # clear line
  print(newline)


def transferChromosomes(gffchr_file, redis_connection, chunk_size, noreload):

  print('Loading chromosomes...')

  # prepare RediSearch
  indexName = 'chromosomeIdx'
  chromosome_index = redisearch.Client(indexName, conn=redis_connection)
  # TODO: there should be an extend argparse flag that prevents deletion
  try:
    chromosome_index.info()
    if noreload:  # previous line will error if index doesn't exist
      print(f'\t"{indexName}" already exists in RediSearch')
      return
    msg = '\tClearing index... {}'
    print(msg.format(''))
    chromosome_index.drop_index()
    _replacePreviousPrintLine(msg.format('done'))
  except Exception as e:
    print(e)
  fields = [
      redisearch.TextField('name'),
      redisearch.NumericField('length'),
      redisearch.TextField('genus'),
      redisearch.TextField('species'),
    ]
  chromosome_index.create_index(fields)
  indexer = chromosome_index.batch_indexer(chunk_size=chunk_size)

  with gffchr_file.cursor() as c:

    # get all the chromosomes
    msg = '\tLoading chromosomes... {}'
    print(msg.format(''))
    name = 'uniquename' if uniquename else 'name'
    query = (f'SELECT feature_id, {name}, organism_id, seqlen '
             'FROM feature '
             'WHERE type_id=' + str(chromosome_id) + ';')
    #         'OR type_id=' + str(supercontig_id) + ';')
    c.execute(query)
    _replacePreviousPrintLine(msg.format('done'))

    # index the chromosomes
    msg = '\tIndexing chromosomes... {}'
    print(msg.format(''))
    chromosome_id_name_map = {}
    for (chr_id, chr_name, chr_organism_id, chr_length,) in c:
      chromosome_id_name_map[chr_id] = chr_name
      organism = organism_id_map[chr_organism_id]
      indexer.add_document(
        f'chromosome:{chr_name}',
        name=chr_name,
        length=chr_length,
        genus=organism['genus'],
        species=organism['species'],
      )
    indexer.commit()
    _replacePreviousPrintLine(msg.format('done'))

    return chromosome_id_name_map


def transferGenes(gffgene_file, redis_connection, chunk_size, noreload, chromosome_id_name_map):

  print('Loading genes...')
  # prepare RediSearch
  indexName = 'geneIdx'
  interval_index = redisearch.Client(indexName, conn=redis_connection)
  # TODO: there should be an extend argparse flag that prevents deletion
  try:
    interval_index.info()
    if noreload:  # previous line will error if index doesn't exist
      print(f'\t"{indexName}" already exists in RediSearch')
      return
    msg = '\tClearing index... {}'
    print(msg.format(''))
    interval_index.drop_index()
    _replacePreviousPrintLine(msg.format('done'))
  except Exception as e:
    print(e)
  fields = [
      redisearch.TextField('chromosome'),
      redisearch.TextField('name'),
      redisearch.NumericField('fmin'),
      redisearch.NumericField('fmax'),
      redisearch.TextField('family'),
      redisearch.NumericField('strand'),
      redisearch.NumericField('index', sortable=True),
    ]
  interval_index.create_index(fields)
  indexer = interval_index.batch_indexer(chunk_size=chunk_size)

  with gffgene_file.cursor() as c:

    # get all the genes
    msg = '\tLoading genes... {}'
    print(msg.format(''))
    name = 'uniquename' if uniquename else 'name'
    query = (f'SELECT fl.srcfeature_id, f.feature_id, f.{name}, fl.fmin, fl.fmax, fl.strand '
             'FROM featureloc fl, feature f '
             'WHERE fl.feature_id=f.feature_id '
             'AND f.type_id=' + str(gene_id) + ';')
    c.execute(query)
    _replacePreviousPrintLine(msg.format('done'))

    # prepare genes for indexing
    msg = '\tProcessing genes... {}'
    print(msg.format(''))
    chromosome_genes = defaultdict(list)
    for (chr_id, g_id, g_name, g_start, g_end, g_strand,) in c:
      if chr_id in chromosome_id_name_map:
        gene = {
            'name': g_name,
            'fmin': g_start,
            'fmax': g_end,
            'strand': g_strand,
            'family': gene_id_family_map.get(g_id, ''),
          }
        chromosome_genes[chr_id].append(gene)
    _replacePreviousPrintLine(msg.format('done'))

    # index the genes
    msg = '\tIndexing genes... {}'
    print(msg.format(''))
    pipeline = redis_connection.pipeline()
    for chr_id, genes in chromosome_genes.items():
      chr_name = chromosome_id_name_map[chr_id]
      genes.sort(key=lambda g: g['fmin'])
      # RediSearch
      for (j, gene) in enumerate(genes):
        gene_name = gene['name']
        indexer.add_document(
          f'gene:{gene_name}',
          chromosome=chr_name,
          name=gene['name'],
          fmin=gene['fmin'],
          fmax=gene['fmax'],
          strand= gene['strand'],
          family=gene['family'],
          index=j,
        )
      # Redis
      pipeline.delete(f'chromosome:{chr_name}:genes')
      pipeline.rpush(f'chromosome:{chr_name}:genes', *map(lambda g: g['name'], genes))
      pipeline.delete(f'chromosome:{chr_name}:families')
      pipeline.rpush(f'chromosome:{chr_name}:families', *map(lambda g: g['family'], genes))
      pipeline.delete(f'chromosome:{chr_name}:fmins')
      pipeline.rpush(f'chromosome:{chr_name}:fmins', *map(lambda g: g['fmin'], genes))
      pipeline.delete(f'chromosome:{chr_name}:fmaxs')
      pipeline.rpush(f'chromosome:{chr_name}:fmaxs', *map(lambda g: g['fmax'], genes))
    indexer.commit()
    pipeline.execute()
    _replacePreviousPrintLine(msg.format('done'))


#def transferData(gffchr_db, gffgene_db, gfa_db, redis_connection, chunk_size, noreload, nosave):

  # chromosome_id_name_map = transferChromosomes(gffchr_file, redis_connection, chunk_size, noreload)
  # transferGenes(gffgene_file, gfa_file, redis_connection, chunk_size, noreload, chromosome_id_name_map)
  # # manually save the data
  # if not nosave:
  #   redis_connection.save()

  

if __name__ == '__main__':
  args = parseArgs()
  
  # create chromosome SQLLite database from chromosomal GFF file
  msg = 'Loading chromosomal GFF...{}'
  print(msg.format(''))
  try:
    gffchr_db = gffutils.create_db(args.gffchr, dbfn='gffchr.db', force=True, keep_order=True)
  except Exception as e:
    _replacePreviousPrintLine(msg.format('failed'))
    exit(e)
  _replacePreviousPrintLine(msg.format('done'))
  # create gene SQLLite database from gene GFF file
  msg = 'Loading gene GFF...{}'
  print(msg.format(''))
  try:
    gffgene_db = gffutils.create_db(args.gffgene, dbfn='gffgene.db', force=True, keep_order=True)
  except Exception as e:
    _replacePreviousPrintLine(msg.format('failed'))
    exit(e)
  _replacePreviousPrintLine(msg.format('done'))
  # create gene family SQLLite database from GFA file
  msg = 'Loading gene family GFA...{}'
  print(msg.format(''))
  try:
    gfa_db = gffutils.create_db(args.gfa, dbfn='gfa.db', force=True, keep_order=True)
  except Exception as e:
    _replacePreviousPrintLine(msg.format('failed'))
    exit(e)
  _replacePreviousPrintLine(msg.format('done'))
  # connect to the redis database
  redis_connection = None
  msg = 'Connecting to Redis...{}'
  print(msg.format(''))
  try:
    redis_connection = connectToRedis(args.rhost, args.rport, args.rdb, args.rpassword)
  except Exception as e:
    _replacePreviousPrintLine(msg.format('failed'))
    exit(e)
  _replacePreviousPrintLine(msg.format('done'))
  # transfer the relevant data from the files to Redis
  try:
    transferData(gffchr_file, gffgene_file, gfa_file, redis_connection, args.rchunksize, args.noreload, args.nosave)
  except Exception as e:
    print(e)


