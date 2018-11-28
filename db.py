# This file contains a web-framework agnostic implementation of the GCV
# services built on a Redis database.
import aioredis
import functools
from collections import defaultdict
from itertools import chain


# database stuff

# the database driver
r = None


# sets up and takes down the database connection
async def db_engine(*args):
  global r
  # TODO: update to use parameters, i.e. host, db, password
  # TODO: add middleware that converts non-string types automatically
  r = await aioredis.create_redis('/run/redis/redis.sock', encoding='utf-8')
  yield
  r.close()
  await r.wait_closed()
  r = None


# a decorator that ensures that the database driver has been setup before the
# decorated function attempts to use it.
def requires_r(func):
  @functools.wraps(func)
  async def wrapper(*args, **kwargs):
    if r is None:
      raise NameError("Database driver undefined.")
    return await func(*args, **kwargs)
  return wrapper


# helper functions

# families - a set of family ids to retrieve gene identifiers for
@requires_r
async def getFamilyGenes(families):
  pipeline = r.pipeline()
  for f in families:
    pipeline.smembers(f)
  return await pipeline.execute()


# takes a gene from the db and an id and formats in the manner expected by the
# API user.
# id - a gene id
# g - the gene corresponding to the id
def formatGene(id, g):
  return {
    'name': g['name'],
    'id': id,
    'fmin': g['begin'],
    'fmax': g['end'],
    'strand': -1 if g['orientation'] == '-' else 1,
    'family': g['family']
  }


def splitLocation(l):
  fmin, fmax = l.split(":")
  return int(fmin), int(fmax)


def formatLocation(l):
  fmin, fmax = splitLocation(l)
  return {'fmin': fmin, 'fmax': fmax}


def removePrefix(prefix, string):
  return string[len(prefix):]


def removeSuffix(suffix, string):
  return string[:-len(suffix)]


def cleanGenes(genes):
  for g in genes:
    g['id'] = removePrefix('gene:', g['id'])
    g['family'] = removePrefix('family:', g['family'])


def cleanTrack(track):
  track['chromosome_id'] = removePrefix('chromosome:', track['chromosome_id'])
  cleanGenes(track['genes'])


def cleanMacro():
  pass


# creates a track for the given gene by flanking it with neighbors on either
# side.
# gene - id of the gene at the center of the query context
# neighbors - the number of neighbors that should flank the query gene on either side
@requires_r
async def geneToTrack(gene, neighbors):
  # fetch the data
  i, chromosome_id = await r.hmget('gene:' + gene, 'number', 'chromosome')
  if i is None or chromosome_id is None:
    return None
  chromosome = await r.hgetall(chromosome_id)
  genus, species = chromosome['organism'].split(':')[1:]
  length = await r.llen(chromosome_id + ':genes')
  start = max(0, int(i)-neighbors)
  stop = min(int(i)+neighbors, length-1)
  gene_ids = await r.lrange(chromosome_id + ':genes', start, stop)
  pipeline = r.pipeline()
  for g in gene_ids:
    pipeline.hgetall(g)
  genes = await pipeline.execute()
  # format and return
  track = {
    'genus': genus,
    'species': species,
    'species_id': chromosome['organism'],
    'chromosome_name': chromosome['name'],
    'chromosome_id': chromosome_id,
    'genes': list(map(lambda e: formatGene(*e), zip(gene_ids, genes)))
  }
  cleanTrack(track)
  return track


# given a set of graph path endpoints, the graph edges (pointers), the path
# scores from the graph construction recurrence, and the minimum path length
# (minsize), the function greedily generates chains (longest paths) in highest
# score first order.
def macroSyntenyTraceback(path_ends, pointers, scores, minsize):
  path_ends.sort(reverse=True)
  for _, end in path_ends:
    if end in pointers:  # note: singletons aren't in pointers
      if scores[end] < minsize:
        break
      begin = end
      while begin in pointers:
        begin = pointers.pop(begin)
      length = scores[end] - scores[begin] + 1
      if length >= minsize:
        yield (begin, end)


# "constructs" a DAG and computes longest forward (f_) and reverse (r_) oriented
# paths (blocks) using a recurrence relation similar to that of DAGchainer
def positionPairsToBlockPositions(pairs, maxinsert, minsize):
  f_path_ends = []  # orders path end nodes longest to shortest
  f_pointers = {}  # points to the previous node (pair) in a path
  f_scores = {}  # the length of the longest path ending at each node
  r_path_ends = []
  r_pointers = {}
  r_scores = {}
  # iterate nodes (pairs), assumed to be in DAG order ((0, 0), (0, 1), (2, 1), (2, 3), ...)
  for i, p1 in enumerate(pairs):
    n1, n2 = p1
    f_scores[p1] = r_scores[p1] = 1
    # iterate preceding nodes in DAG from closest to furtherest
    for j in reversed(range(i)):
      m1, m2 = p2 = pairs[j]
      # the query and chromosome must agree on the ordering
      # n1 <= m1 is always true
      d1 = n1 - m1
      # forward blocks
      if m2 < n2:
        d2 = n2 - m2
        # are the nodes close enough to be in the same path?
        if d1 <= maxinsert and d2 <= maxinsert:
          s = f_scores[p2] + 1
          if s > f_scores[p1] or (s == f_scores[p1] and p2[0] == p2[1]):  # in case trivial block ends on gene family with multiple successive copies
            f_scores[p1]   = s
            f_pointers[p1] = p2
      # reverse blocks
      elif m2 > n2:
        d2 = m2 - n2
        # are the nodes close enough to be in the same path?
        if d1 <= maxinsert and d2 <= maxinsert:
          s = r_scores[p2] + 1
          if s > r_scores[p1]:
            r_scores[p1]   = s
            r_pointers[p1] = p2
      # if this node is too far away then all remaining nodes are too
      if d1 > maxinsert:
        break
    f_path_ends.append((f_scores[p1], p1))
    r_path_ends.append((r_scores[p1], p1))
  # traceback longest paths and get endpoints
  f = macroSyntenyTraceback(f_path_ends, f_pointers, f_scores, minsize)
  r = macroSyntenyTraceback(r_path_ends, r_pointers, r_scores, minsize)
  return chain(f, r)


# database API

# creates a track for each given gene by flanking it with neighbors on either
# side.
# genes - list of gene ids
# neighbors - number of neighbors that should flank each gene
async def genesToTracks(genes, neighbors):
  families = set()
  tracks = {'groups': []}
  for g in genes:
    track = await geneToTrack(g, neighbors)
    if track is None:
      continue
    families.update(map(lambda g: g['family'], track['genes']))
    tracks['groups'].append(track)
  families.discard('')
  tracks['families'] = list(map(lambda f: {'id': f, 'name': f}, families))
  return tracks



# families - an ordered list of gene family ids representing the query context
# min_matched - the number of families that must match in each block
# max_intermediate - the max number of intermediate genes allowed between any two matched genes
@requires_r
async def searchMicroSyntenyTracks(families, min_matched, max_intermediate):
  # get all genes of the query families
  families = list(map(lambda f: 'family:' + f, families))
  family_gene_ids = await getFamilyGenes(set(families))
  pipeline = r.pipeline()
  for gene_ids in family_gene_ids:
    for g in gene_ids:
      pipeline.hmget(g, 'chromosome', 'number')
  genes = await pipeline.execute()
  # bin the gene numbers by chromosome
  chromosome_nums = defaultdict(list)
  for chromosome, number in genes:
    chromosome_nums[chromosome].append(int(number))
  # compute islands and gaps
  blocks = defaultdict(list)
  for c, nums in chromosome_nums.items():
    nums.sort()
    block = []
    for n in nums:
      if not block or n-block[-1] <= max_intermediate-1:
        block.append(n)
      else:
        if len(block) >= min_matched:
          blocks[c].append(block)
        block = []
    if len(block) >= min_matched:
      blocks[c].append(block)
  # fetch result tracks
  families = set()
  tracks = {'groups': []}
  for c, blocks in blocks.items():
    chromosome = await r.hgetall(c)
    genus, species = chromosome['organism'].split(':')[1:]
    for b in blocks:
      first = b[0]
      last = b[-1]
      gene_ids = await r.lrange(c + ':genes', first, last)
      pipeline = r.pipeline()
      for g in gene_ids:
        pipeline.hgetall(g)
      genes = await pipeline.execute()
      # format and return
      track = {
        'genus': genus,
        'species': species,
        'species_id': chromosome['organism'],
        'chromosome_name': chromosome['name'],
        'chromosome_id': c,
        'genes': list(map(lambda e: formatGene(*e), zip(gene_ids, genes)))
      }
      cleanTrack(track)
      families.update(map(lambda g: g['family'], track['genes']))
      tracks['groups'].append(track)
  families.discard('')
  tracks['families'] = list(map(lambda f: {'id': f, 'name': f}, families))
  return tracks


# chromosome - the id of the query chromosome
# results - the ids of the chromosomes that the we want results for
@requires_r
async def macroSyntenyTracks(chromosome, matched=20, maxinsert=10, results=[], familymask=10):

  # make a dictionary that maps families to query gene numbers
  family_num_map = defaultdict(list)
  mask = set()
  for i, f in enumerate(chromosome):
    if f != '':
      f = 'family:' + f
      family_num_map[f].append(i)
      if len(family_num_map[f]) > familymask:
          mask.add(f)
  # remove families that have too many members
  for f in mask:
    del family_num_map[f]

  # get all families for each chromosome
  #chromosomes = map(lambda r: 'chromosome:'+r+':families', results) if results else r.keys('chromosome:*:families')
  chromosomes = []
  if results:
    chromosomes = map(lambda r: 'chromosome:', results)
  else:
    chromosomes =  await r.smembers('chromosomes')
  # NOTE: This pipeline is slower than pyredis...
  pipeline = r.pipeline()
  for c in chromosomes:
    pipeline.llen(c + ':families')
  lengths = await pipeline.execute()
  filtered_chromosomes = []
  family_pipeline = r.pipeline()
  location_pipeline = r.pipeline()
  for c, l in zip(chromosomes, lengths):
    if l < matched:
      continue
    filtered_chromosomes.append(c)
    family_pipeline.lrange(c + ':families', 0, -1)
    location_pipeline.lrange(c + ':locations', 0, -1)
  chromosomes_as_families = await family_pipeline.execute()
  chromosomes_as_locations = await location_pipeline.execute()

  # generate gene position pairs based on matching families and compute blocks
  tracks = []
  for c, families, locations in zip(filtered_chromosomes, chromosomes_as_families, chromosomes_as_locations):
    # count each family's occurrence in the chromosome
    c_family_counts = defaultdict(int)
    for f in families:
      c_family_counts[f] += 1
    pairs = []
    # create a gene number pair for matching gene families
    for i, f in enumerate(families):
      if c_family_counts[f] > familymask or f not in family_num_map:
        continue
      pairs.extend(map(lambda n: (i, n), family_num_map[f]))
    if len(pairs) < matched:
      continue
    block_positions = positionPairsToBlockPositions(pairs, maxinsert, matched)
    blocks = []
    paths = []
    end_genes = []
    trivial_catcher = []
    # convert the block positions into blocks
    for begin, end in block_positions:
      query_start, query_stop, orientation = (begin[1], end[1], '+') \
        if begin[1] < end[1] else (end[1], begin[1], '-')
      begin_loc = locations[begin[0]]
      end_loc = locations[end[0]]
      start = min(splitLocation(begin_loc))
      stop = max(splitLocation(end_loc))
      blocks.append({
        'query_start': query_start,
        'query_stop': query_stop,
        'start': start,
        'stop': stop,
        'orientation': orientation
      })
    if len(blocks) == 0:
      continue
    chromosome = await r.hgetall(c)
    genus, species = removePrefix('organism:', chromosome['organism']).split(":")
    tracks.append({
      'chromosome': chromosome['name'],
      'genus': genus,
      'species': species,
      'blocks': blocks
    })
  return tracks


# chromosome - id of the chromosome you want to find genes on
# families - a list of gene family ids that you want to find all occurrences of on the chromosome
@requires_r
async def globalPlot(chromosome, families):
  families = list(map(lambda f: 'family:' + f, families))
  # get all genes of the query families
  family_gene_ids = await getFamilyGenes(set(families))
  pipeline = r.pipeline()
  for gene_ids in family_gene_ids:
    for g in gene_ids:
      pipeline.hmget(g, 'chromosome')
  genes = await pipeline.execute()
  # filter the genes not on the query chromosome
  chromosome_gene_ids = []
  for id, (c, ) in zip(chain(*family_gene_ids), genes):
    if c == 'chromosome:'+chromosome:
      chromosome_gene_ids.append(id)
  # get the query chromosome's genes' information
  pipeline = r.pipeline()
  for g in chromosome_gene_ids:
    pipeline.hgetall(g)
  genes = await pipeline.execute()
  group_genes = list(map(lambda e: formatGene(*e), zip(chromosome_gene_ids, genes)))
  cleanGenes(group_genes)
  return group_genes


# chromosome - id of the chromosome you want to get
@requires_r
async def getChromosome(chromosome):
  chromosome = 'chromosome:' + chromosome
  length = await r.hget(chromosome, 'length')
  if length is None:
    return None
  genes = await r.lrange(chromosome + ':genes', 0, -1)
  families = await r.lrange(chromosome + ':families', 0, -1)
  locations = await r.lrange(chromosome + ':locations', 0, -1)
  return {
    'length': int(length),
    'genes': list(map(lambda g: removePrefix('gene:', g), genes)),
    'families': list(map(lambda f: removePrefix('family:', f), families)),
    'locations': list(map(lambda l: formatLocation(l), locations))
  }
