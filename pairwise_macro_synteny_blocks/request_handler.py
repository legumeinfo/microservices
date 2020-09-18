# Python
from collections import defaultdict
from itertools import chain
# dependencies
from redisearch import Client


class RequestHandler:

  def __init__(self, redis_connection):
    self.redis_connection = redis_connection

  def parseArguments(self, chromosome, target, matched, intermediate, mask):
    iter(chromosome)  # TypeError if not iterable
    if target is None:
      raise ValueError('target is required')
    matched = int(matched)  # ValueError
    intermediate = int(intermediate)  # ValueError
    if matched <= 0 or intermediate <= 0:
      raise ValueError('matched and intermediate must be positive')
    if mask is not None:
      mask = int(mask)
      if mask <= 0:
        raise ValueError('mask must be positive')
    else:
      mask = float('inf')
    return chromosome, target, matched, intermediate, mask

  # given a query chromosome and a target chromosome as ordered lists of
  # functional annotations, the function computes a gene index pair for each
  # pair of query-target indexes that have the same annotation
  def _chromosomesToIndexPairs(self, query_chromosome, target_chromosome, mask):

    # make a dictionary that maps query chromosome families to gene indices
    query_family_index_map = defaultdict(list)
    masked_families = set()
    for i, f in enumerate(query_chromosome):
      if f != '':
        query_family_index_map[f].append(i)
        if len(query_family_index_map[f]) > mask:
          masked_families.add(f)
    # remove families that have too many members
    for f in masked_families:
      del query_family_index_map[f]

    # count each family's number of occurrence on the target chromosome
    target_family_counts = defaultdict(int)
    for f in target_chromosome:
      target_family_counts[f] += 1

    # create a gene index pair for each pair of query-target indexes that have
    # matching annotations
    pairs = []
    for i, f in enumerate(target_chromosome):
      if target_family_counts[f] <= mask and f in query_family_index_map:
        pairs.extend(map(lambda n: (i, n), query_family_index_map[f]))

    return pairs

  # given a set of index pair DAG path endpoints, the graph edges (pointers),
  # the path scores from the graph construction recurrence, and the minimum path
  # length (matched), the function greedily generates chains (longest paths) in
  # highest score first order
  def _indexBlocksViaIndexPathTraceback(self, path_ends, pointers, scores, matched):
    path_ends.sort(reverse=True)
    for _, end in path_ends:
      if end in pointers:  # note: singletons aren't in pointers
        if scores[end] < matched:
          break
        begin = end
        while begin in pointers:
          begin = pointers.pop(begin)
        length = scores[end] - scores[begin] + 1
        if length >= matched:
          yield (begin, end)

  # "constructs" a DAG using the index pairs as nodes and computes longest
  # forward (f_) and reverse (r_) oriented paths (blocks) using a recurrence
  # relation similar to that of DAGchainer
  def _indexPairsToIndexBlocks(self, pairs, intermediate, matched):
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
        # the query and target must agree on the ordering
        # n1 <= m1 is always true
        d1 = n1 - m1
        # forward blocks
        if m2 < n2:
          d2 = n2 - m2
          # are the nodes close enough to be in the same path?
          if d1 <= intermediate and d2 <= intermediate:
            s = f_scores[p2] + 1
            if s > f_scores[p1] or (s == f_scores[p1] and p2[0] == p2[1]):  # in case trivial block ends on gene family with multiple successive copies
              f_scores[p1]   = s
              f_pointers[p1] = p2
        # reverse blocks
        elif m2 > n2:
          d2 = m2 - n2
          # are the nodes close enough to be in the same path?
          if d1 <= intermediate and d2 <= intermediate:
            s = r_scores[p2] + 1
            if s > r_scores[p1]:
              r_scores[p1]   = s
              r_pointers[p1] = p2
        # if this node is too far away then all remaining nodes are too
        if d1 > intermediate:
          break
      f_path_ends.append((f_scores[p1], p1))
      r_path_ends.append((r_scores[p1], p1))
    # traceback longest paths and get endpoints
    f = self._indexBlocksViaIndexPathTraceback(f_path_ends, f_pointers, f_scores, matched)
    r = self._indexBlocksViaIndexPathTraceback(r_path_ends, r_pointers, r_scores, matched)
    return chain(f, r)

  # TODO: use aioredis and call redisearch via .execute to prevent blocking
  # https://redislabs.com/blog/beyond-the-cache-with-python/
  async def process(self, query_chromosome, target, matched, intermediate, mask):

    start_time  = time.time()

    # connect to the indexes
    chromosome_index = Client('chromosomeIdx', conn=self.redis_connection)
    gene_index = Client('geneIdx', conn=self.redis_connection)

    # check if the target chromosome exists
    target_doc_id = f'chromosome:{target}'
    target_doc = chromosome_index.load_document(target_doc_id)
    # exit if the target chromosome wasn't found
    if not hasattr(target_doc, 'name'):
      return None

    # count how many genes are on the target chromosome
    num_genes = self.redis_connection.llen(f'{target_doc_id}:genes')
    # exit if there aren't enough genes to construct even a single block
    if num_genes < matched:
      return []

    # get the functional annotations of the genes on the target chromosome
    target_chromosome = self.redis_connection.lrange(f'{target_doc_id}:families', 0, -1)

    # compute gene index pairs based on matching annotations
    index_pairs = self._chromosomesToIndexPairs(query_chromosome, target_chromosome, mask)

    # exit if there aren't enough pairs to construct even a single block that
    # satisfies the matched requirement
    if len(index_pairs) < matched:
      return []

    # index blocks from the index pairs
    index_blocks = self._indexPairsToIndexBlocks(index_pairs, intermediate, matched)

    # convert the index blocks into output blocks
    blocks = []
    for begin_pair, end_pair in index_blocks:
      # determine the query start/stop indexes and block orientation based on
      # the query index values
      query_start_index, query_stop_index, orientation = \
          (begin_pair[1], end_pair[1], '+') \
        if begin_pair[1] < end_pair[1] else \
          (end_pair[1], begin_pair[1], '-')
      # get the physical locations of the target start gene
      begin_target_index = begin_pair[0]
      l = self.redis_connection.llen(f'{target_doc_id}:fmins')
      start_fmin = self.redis_connection.lindex(f'{target_doc_id}:fmins', begin_target_index)
      start_fmax = self.redis_connection.lindex(f'{target_doc_id}:fmaxs', begin_target_index)
      fmin = min(int(start_fmin), int(start_fmax))
      # get the physical locations of the target end gene
      end_target_index = begin_pair[0]
      end_fmin = self.redis_connection.lindex(f'{target_doc_id}:fmins', end_target_index)
      end_fmax = self.redis_connection.lindex(f'{target_doc_id}:fmaxs', end_target_index)
      fmax = max(int(end_fmin), int(end_fmax))
      # make and save the block
      block = {
          'i': query_start_index,
          'j': query_stop_index,
          'fmin': fmin,
          'fmax': fmax,
          'orientation': orientation
        }
      blocks.append(block)

    end_time = time.time()
    print(f'total: {end_time-start_time}')

    return blocks
