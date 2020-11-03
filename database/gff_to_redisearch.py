#!/usr/bin/env python

# Python
import argparse
import os
import re
import sys
import csv
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
  strain_envvar = 'STRAIN'
  parser.add_argument('--strain', action=EnvArg, required=False, envvar=strain_envvar, type=str, default=None, help=f'The strain of the organism being loaded (can also be specified using the {strain_envvar} environment variable).')
  
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
  parser.add_argument('--extend', dest='extend', action='store_true', help='Extend the existing data in the Redis database rather than replacing.');
  parser.set_defaults(extend=False)

  return parser.parse_args()


def _replacePreviousPrintLine(newline):
  sys.stdout.write('\033[F') # back to previous line
  sys.stdout.write('\033[K') # clear line
  print(newline)


def transferChromosomes(genus, species, gffchr_db, redis_connection, chunk_size, noreload, extend):

  print('Loading chromosomes...')
  # prepare RediSearch
  indexName = 'chromosomeIdx'
  chromosome_index = redisearch.Client(indexName, conn=redis_connection)
  try:
    chromosome_index.info()
    if noreload:  # previous line will error if index doesn't exist
      print(f'\t"{indexName}" already exists in RediSearch')
      return
  except Exception as e:
    print(e)
  if (extend==False):
    try:
      msg = '\tClearing chromosome index... {}'
      print(msg.format(''))
      chromosome_index.drop_index()
      _replacePreviousPrintLine(msg.format('done'))
      fields = [
        redisearch.TextField('name'),
        redisearch.NumericField('length'),
        redisearch.TextField('genus'),
        redisearch.TextField('species'),
      ]
      chromosome_index.create_index(fields)
    except Exception as e:
      exit(e)
  indexer = chromosome_index.batch_indexer(chunk_size=chunk_size)

  # index the chromosomes
  msg = '\tIndexing chromosomes... {}'
  print(msg.format(''))
  chromosome_names = []
  for chr in gffchr_db.features_of_type('chromosome', order_by='attributes'):
    chr_name = chr.seqid
    chr_length = chr.end
    chromosome_names.append(chr_name)
    indexer.add_document(
      f'chromosome:{chr_name}',
      name=chr_name,
      length=chr_length,
      genus=genus,
      species=species,
    )
    indexer.commit()
  _replacePreviousPrintLine(msg.format('done'))
  return chromosome_names


def transferGenes(gffgene_db, gfa_file, redis_connection, chunk_size, noreload, extend, chromosome_names):

  print('Loading gene families and genes...')
  # prepare RediSearch
  indexName = 'geneIdx'
  interval_index = redisearch.Client(indexName, conn=redis_connection)
  try:
    interval_index.info()
    if noreload:  # previous line will error if index doesn't exist
      print(f'\t"{indexName}" already exists in RediSearch')
      return
  except Exception as e:
    print(e)
  if (extend==False):
    msg = '\tClearing index... {}'
    print(msg.format(''))
    interval_index.drop_index()
    _replacePreviousPrintLine(msg.format('done'))
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

  # index the genes by going through the GFA file line by line
  # msg = '\tProcessing genes... {}'
  # print(msg.format(''))
  chromosome_genes = defaultdict(list)
  msg = '\tParsing GFA file... {}'
  print(msg.format(''))
  try:
    with gfa_file as tsv:
      for line in csv.reader(tsv, delimiter="\t"):
        if (line[0]=="ScoreMeaning"): # metadata
          continue
        if (line[0].startswith("#")): # comment
          continue
        gene_id = line[0]
        genefamily_id=line[1]
        try:
          gffgene = gffgene_db[gene_id]
          chr_name = gffgene.seqid
          if chr_name in chromosome_names:
            strand = 0
            if (gffgene.strand=='+'):
              strand = +1
            if (gffgene.strand=='-'):
              strand = -1
            gene = {
              'name': gffgene.id,
              'fmin': gffgene.start,
              'fmax': gffgene.end,
              'strand': strand,
              'family': genefamily_id,
            }
            chromosome_genes[chr_name].append(gene)
        except Exception as e:
          # gene missing from GFF file
          continue
  except Exception as e:
    _replacePreviousPrintLine(msg.format('failed'))
    exit(e)
  _replacePreviousPrintLine(msg.format('done'))

  # index the genes
  msg = '\tIndexing genes... {}'
  print(msg.format(''))
  pipeline = redis_connection.pipeline()
  for chr_name, genes in chromosome_genes.items():
    genes.sort(key=lambda g: g['fmin'])
    # RediSearch
    for (j, gene) in enumerate(genes):
      gene_name = gene['name']
      indexer.add_document(
        f'gene:{gene_name}',
        chromosome = chr_name,
        name = gene['name'],
        fmin = gene['fmin'],
        fmax = gene['fmax'],
        strand = gene['strand'],
        family = gene['family'],
        index = j,
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


def transferData(genus, species, gffchr_db, gffgene_db, gfa_file, redis_connection, chunk_size, noreload, extend, nosave):

  chromosome_names = transferChromosomes(genus, species, gffchr_db, redis_connection, chunk_size, noreload, extend)
  transferGenes(gffgene_db, gfa_file, redis_connection, chunk_size, noreload, extend, chromosome_names)
  # manually save the data
  if not nosave:
    redis_connection.save()
  

if __name__ == '__main__':
  args = parseArgs()

  print("===== "+args.genus+" "+args.species+" "+args.strain+" =====")
  
  # create chromosome SQLLite database from chromosomal GFF file
  gffchr_db = None
  msg = 'Creating chromosome GFF database...{}'
  print(msg.format(''))
  try:
    gffchr_db = gffutils.create_db(args.gffchr, ':memory:', force=True, keep_order=True)
  except Exception as e:
    _replacePreviousPrintLine(msg.format('failed'))
    exit(e)
  _replacePreviousPrintLine(msg.format('done'))
  # create gene SQLLite database from gene GFF file
  gffgene_db = None
  msg = 'Creating gene GFF database...{}'
  print(msg.format(''))
  try:
    gffgene_db = gffutils.create_db(args.gffgene, ':memory:', force=True, keep_order=True)
  except Exception as e:
    _replacePreviousPrintLine(msg.format('failed'))
    exit(e)
  _replacePreviousPrintLine(msg.format('done'))
  # create gene family GFA file object
  gfa_file = None
  msg = 'Reading gene family GFA file...{}'
  print(msg.format(''))
  try:
    gfa_file = open(args.gfa, "r")
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
  # HACK the species to contain the strain name if given
  genus = args.genus
  species = args.species
  if (args.strain!=None):
    species = species+'_'+args.strain
  # transfer the relevant data from the files to Redis
  try:
    transferData(genus, species, gffchr_db, gffgene_db, gfa_file, redis_connection, args.rchunksize, args.noreload, args.extend, args.nosave)
  except Exception as e:
    print(e)


