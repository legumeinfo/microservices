# Python
import codecs
import csv
from collections import defaultdict
# dependencies
import gffutils
import gzip
from urllib.request import urlopen, urlparse


def transferChromosomes(redisearch_loader, genus, species, chromosome_gff):
  '''
  Loads chromosomes from a GFF file into a RediSearch database.

  Parameters:
    redisearch_loader (RediSearchLoader): The loader to use to load data into
      RediSearch.
    genus (str): The genus of the chromosomes being loaded.
    species (str): The species of the chromosomes being loaded.
    chromosome_gff (str): The local path or URL to the GFF to load chromosomes from.

  Returns:
    set[str]: A set containing the names of all the chromosomes that were
      loaded.
  '''

  # create chromosome SQLLite database from chromosomal GFF file
  gffchr_db = \
    gffutils.create_db(
      chromosome_gff,
      ':memory:',
      force=True,
      keep_order=True,
    )

  # index the chromosomes
  chromosome_names = set()
  for chr in gffchr_db.features_of_type(('chromosome','supercontig'), order_by='attributes'):
    name = chr.seqid
    length = chr.end
    chromosome_names.add(name)
    redisearch_loader.indexChromosome(name, length, genus, species)

  return chromosome_names


def transferGenes(redisearch_loader, gene_gff, gfa, chromosome_names):
  '''
  Loads genes from a GFF file into a RediSearch database.

  Parameters:
    redisearch_loader (RediSearchLoader): The loader to use to load data into
      RediSearch.
    gene_gff (str): The local path or URL to the GFF to load genes from.
    gfa (str): The local path or URL to a GFA file containing gene family
      associations for the genes being loaded.
    chromosome_names (set[str]): A containing the names of all the chromosomes
      that have been loaded.
  '''

  # create gene SQLLite database from gene GFF file
  gffgene_db = \
    gffutils.create_db(gene_gff, ':memory:', force=True, keep_order=True)

  # index all the genes in the db
  gene_lookup = dict()
  chromosome_genes = defaultdict(list)
  for gffgene in gffgene_db.features_of_type('gene', order_by='attributes'):
        chr_name = gffgene.seqid
        if chr_name in chromosome_names:
          strand = 0
          if gffgene.strand == '+':
            strand = 1
          if gffgene.strand == '-':
            strand = -1
          gene = {
            'name': gffgene.id,
            'fmin': gffgene.start,
            'fmax': gffgene.end,
            'strand': strand,
            'family': '',
          }
          gene_lookup[gffgene.id] = gene
          chromosome_genes[chr_name].append(gene)
  # deal with family assignments (for non-orphans) from GFA
  with (open(gfa, 'rb') if urlparse(gfa).scheme == ''
                        else urlopen(gfa)) as fileobj:
    tsv = gzip.GzipFile(fileobj=fileobj) if gfa.endswith("gz") else fileobj
    for line in csv.reader(codecs.iterdecode(tsv, 'utf-8'), delimiter="\t"):
      # skip comment and metadata lines
      if line[0].startswith('#') or line[0] == 'ScoreMeaning':
        continue
      gene_id = line[0]
      if gene_id in gene_lookup:
        gene = gene_lookup[gene_id]
        genefamily_id = line[1]
        gene['family'] = genefamily_id

  # index the genes
  for chr_name, genes in chromosome_genes.items():
    redisearch_loader.indexChromosomeGenes(chr_name, genes)


def loadFromGFF(redisearch_loader, genus, species, strain, chromosome_gff,
gene_gff, gfa):
  '''
  Loads data from a GFF files into a RediSearch database.

  Parameters:
    redisearch_loader (RediSearchLoader): The loader to use to load data into
      RediSearch.
    genus (str): The genus of the data being loaded.
    species (str): The species of the data being loaded.
    strain (str): The strain of the data being loaded.
    chromosome_gff (pathlib.Path): The path to the GFF to load chromosomes from.
    gene_gff (pathlib.Path): The path to the GFF to load genes from.
    gfa (pathlib.Path): The path to a GFA file containing gene family
      associations for the genes being loaded.
  '''

  # HACK the species to contain the strain name if given
  if strain is not None:
    species += ':' + strain
  chromosome_names = \
    transferChromosomes(redisearch_loader, genus, species, chromosome_gff)
  transferGenes(redisearch_loader, gene_gff, gfa, chromosome_names)
