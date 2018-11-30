import core.database as db
from core.utils import removePrefix, splitLocation
from collections import defaultdict
from itertools import chain


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


# chromosome - the id of the query chromosome
# results - the ids of the chromosomes that the we want results for
async def macroSyntenyTracks(chromosome, matched=20, maxinsert=10, results=[], familymask=10):
  r = db.getInterface()

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
