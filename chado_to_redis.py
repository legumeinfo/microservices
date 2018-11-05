import argparse
import psycopg2 as p
import redis
from collections import defaultdict


def parseArgs():

  # create the parser
  parser = argparse.ArgumentParser(
    description='Loads data from a Chado (PostreSQL) database into a Redis database for consumption by Genome Context Viewer micro-services.',
    epilog='It is assumed that gene families are associated with genes in Chado via the featureprop table with entries of the "gene family" cvterm type. The Redis database chosen will be flushed, destroying any existing data.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  # PostgreSQL args
  parser.add_argument('--pdb', type=str, default='chado', help='The PostgreSQL database.')
  parser.add_argument('--puser', type=str, default='chado', help='The PostgreSQL username.')
  parser.add_argument('--ppassword', type=str, default=None, help='The PostgreSQL password.')
  parser.add_argument('--phost', type=str, default='localhost', help='The PostgreSQL host.')
  parser.add_argument('--pport', type=int, default=5432, help='The PostgreSQL port.')

  # Redis args
  parser.add_argument('--rdb', type=int, default=0, help='The Redis database.')
  parser.add_argument('--rpassword', type=str, default='', help='The Redis password.')
  parser.add_argument('--rhost', type=str, default='localhost', help='The Redis host.')
  parser.add_argument('--rport', type=int, default=6379, help='The Redis port.')

  # other args
  parser.add_argument('--minchromosomes', type=int, default=1, help='The minimum number of chromosomes an organism must have for it to be loaded')
  parser.add_argument('--mingenes', type=int, default=2, help='The minimum number of genes that must be on a chromosome for it to be loaded.')

  return parser.parse_args()


def connectToChado(database, user, password=None, host=None, port=None):
  print("Connecting to PostgreSQL")
  db_string = 'dbname=' + database + ' user=' + user
  if password is not None:
    db_string += ' password=' + password
  if host is not None:
    db_string += ' host=' + host
  if port is not None:
    db_string += ' port=' + str(port)
  return p.connect(db_string)


def connectToRedis(host='localhost', port=6379, db=0, password=''):
  print("Connecting to Redis")
  return redis.Redis(host=host, port=port, db=db)


def bootstrapRedis(r):
  print('Flushing the Redis database')
  r.flushdb()


def transferData(p_connection, r, minchromosomes=-1, mingenes=-1):
  print("Transferring data")
  with p_connection.cursor() as c:
    print('\tFetching cvterms')

    # get the chromsome cvterm
    query = ('SELECT cvterm_id '
             'FROM cvterm '
             'WHERE name=\'chromosome\' '
             'AND cv_id = (select cv_id from cv where name=\'sequence\');')
    c.execute(query)
    # does it exist?
    if not c.rowcount:
      raise Exception('Failed to retrieve the chromosome cvterm entry')
    chromosome_id, = c.fetchone()

    # get the supercontig cvterm
    query = ('SELECT cvterm_id '
             'FROM cvterm '
             'WHERE name=\'supercontig\' '
             'AND cv_id = (select cv_id from cv where name=\'sequence\');')
    c.execute(query)
    # does it exist?
    if not c.rowcount:
      raise Exception('Failed to retrieve the supercontig cvterm entry')
    supercontig_id, = c.fetchone()

    # get the gene cvterm
    query = ('SELECT cvterm_id '
             'FROM cvterm '
             'WHERE name=\'gene\' '
             'AND cv_id = (select cv_id from cv where name=\'sequence\');')
    c.execute(query)
    # does it exist?
    if not c.rowcount:
      raise Exception('Failed to retrieve the gene cvterm entry')
    gene_id, = c.fetchone()

    # get the gene family cvterm
    query = ('SELECT cvterm_id '
             'FROM cvterm '
             'WHERE name=\'gene family\' LIMIT 1;')
    c.execute(query)
    if not c.rowcount:
      raise Exception('Failed to retrieve the gene family cvterm entry')
    gene_family_id, = c.fetchone()

    # get the family representative cvterm
    #query = ('SELECT cvterm_id '
    #         'FROM cvterm '
    #         'WHERE name=\'family representative\' '
    #         'LIMIT 1;')
    #c.execute(query)
    #if not c.rowcount:
    #  raise Exception('Failed to retrieve the family representative cvterm entry')
    #family_representative_id, = c.fetchone()

    print('\tFetching gene family assignments')
    # get all the gene family assignments from the database
    query = ('SELECT feature_id, value '
             'FROM featureprop '
             'WHERE type_id=' + str(gene_family_id) + ';')
    c.execute(query)
    gene_families = {gene_id: 'family:' + family for (gene_id, family) in c}

    print('\tFetching organisms')
    # get all the organisms from the database
    query = ('SELECT organism_id, genus, species, common_name '
             'FROM organism;')
    c.execute(query)
    organism_keys = {}
    organisms = {}
    organism_chromosomes = {}
    for (id, genus, species, cname) in c:
      organism = 'organism:' + genus + ':' + species
      organism_keys[id] = organism
      organisms[organism] = {'commonname': cname}
      organism_chromosomes[organism + ':chromosomes'] = []

    print('\tFetching chromosomes and genes')
    # get all the chromosomes from the database
    query = ('SELECT feature_id, organism_id, name, uniquename, seqlen '
             'FROM feature '
             'WHERE type_id in (' + str(chromosome_id) + ',' + str(supercontig_id) + ');')
    c.execute(query)
    # get all the genes for each chromosome and prepare them to be transfered
    chromosomes = {}
    chromosome_genes = {}
    genes = {}
    families = defaultdict(set)
    for (chr_id, organism_id, name, uname, length) in c:
      organism = organism_keys[organism_id]
      chromosome = 'chromosome:' + uname
      with p_connection.cursor() as chr_c:
        # get the gene ids ordered by their position on the chromosome
        query = ('SELECT fl.feature_id, f.name, f.uniquename, fl.fmin, fl.fmax, fl.strand '
                 'FROM featureloc fl, feature f '
                 'WHERE fl.feature_id=f.feature_id '
                 'AND f.type_id=' + str(gene_id) + ' '
                 'AND fl.srcfeature_id=' + str(chr_id) + ' '
                 'ORDER BY fmin ASC;')
        chr_c.execute(query)
        if chr_c.rowcount < mingenes:
          continue
        organism_chromosomes[organism + ':chromosomes'].append(chromosome)
        chromosomes[chromosome] = {'name': name, 'length': length, 'organism': organism}
        chromosome_genes[chromosome + ':genes'] = []
        for i, (id, g_name, g_uname, fmin, fmax, strand) in enumerate(chr_c):
          gene = 'gene:' + g_uname
          family = gene_families.get(id, '')
          families[family].add(gene)  # this includes the null family
          chromosome_genes[chromosome + ':genes'].append(gene)
          genes[gene] = {
            'number': i,
            'name': g_name,
            'begin': fmin,
            'end': fmax,
            'orientation': '-' if strand == -1 else '+',
            'family': family,
            'chromosome': chromosome
          }

    print('\tLoading data into Redis')
    # insert each organism into Redis
    pipeline = r.pipeline()
    for o, o_data in organisms.items():
      if len(organism_chromosomes[o + ':chromosomes']) >= minchromosomes:
        pipeline.hmset(o, o_data)
        pipeline.rpush(o + ':chromosomes', *organism_chromosomes[o + ':chromosomes'])
    r.sadd('chromosomes', *chromosomes)
    for c, c_data in chromosomes.items():
      pipeline.hmset(c, c_data)
      pipeline.rpush(c + ':genes', *chromosome_genes[c + ':genes'])
      pipeline.rpush(c + ':families', *map(lambda g: genes[g]['family'], chromosome_genes[c + ':genes']))
    for g, g_data in genes.items():
      pipeline.hmset(g, g_data)
    for f, f_data in families.items():
      pipeline.sadd(f, *f_data)
    pipeline.execute()


if __name__ == '__main__':
  args = parseArgs()
  print(args.phost)
  # connect to the databases
  r_db = 'GCV'
  p_connection = connectToChado(args.pdb, args.puser, args.ppassword, args.phost, args.pport)
  r = connectToRedis(args.rhost, args.rport, args.rdb, args.rpassword)
  # bootstrap Redis
  bootstrapRedis(r)
  # transfer the relevant data from Chado to Redis
  try:
    transferData(p_connection, r, args.minchromosomes, args.mingenes)
  except Exception as e:
    print(e)
  # disconnect from the database
  p_connection.close()
