# Python
from collections import defaultdict
# dependencies
from redisearch import Client, NumericFilter, Query


# adapted from re.escape in cpython re.py to escape RediSearch special characters
_special_chars_map = {i: '\\' + chr(i) for i in b'-'}
def _escapeSpecialCharacters(s):
  return s.translate(_special_chars_map)


def _stripEscapeCharacters(s):
  return s.replace('\\', '')


class RequestHandler:

  def __init__(self, redis_connection):
    self.redis_connection = redis_connection

  def parseArguments(self, query_track, matched, intermediate):
    if type(query) is not list:
      raise ValueError('query must be a list')
    matched = float(matched)  # ValueError
    intermediate = float(intermediate)  # ValueError
    if matched <= 0 or intermediate <= 0:
      raise ValueError('matched and intermediate must be positive')
    return query_track, matched, intermediate

  # TODO: use aioredis and call redisearch via .execute to prevent blocking
  # https://redislabs.com/blog/beyond-the-cache-with-python/
  async def process(self, query_track, matched, intermediate):
    # connect to the index
    gene_index = Client('geneIdx', conn=self.redis_connection)
    chromosome_index = Client('chromosomeIdx', conn=self.redis_connection)
    # search the gene index
    # TODO: is there a way to query for all genes exactly at once?
    families = set(map(_escapeSpecialCharacters, query_track))
    families.discard('')
    chromosome_match_indices = defaultdict(list)
    for family in families:
      # count how many genes are in the family
      query = Query(family)\
                .limit_fields('family')\
                .verbatim()\
                .paging(0, 0)
      result = gene_index.search(query)
      num_genes = result.total
      # get the genes
      query = Query(family)\
                .limit_fields('family')\
                .verbatim()\
                .return_fields('chromosome', 'index')\
                .paging(0, num_genes)
      result = gene_index.search(query)
      for d in result.docs:
        chromosome_match_indices[d.chromosome].append(int(d.index))
    # compute islands and gaps
    blocks = defaultdict(list)
    for chromosome_name, indices in chromosome_match_indices.items():
      indices.sort()
      block = [indices[0]]
      for i in indices[1:]:
        # match is close enough to previous match to add to block
        if (intermediate < 1 and (i-block[-1])/len(query_track) <= intermediate) or \
        (intermediate >= 1 and i-block[-1] <= intermediate-1):
          block.append(i)
        # match is too far away from previous match
        else:
          # save block if it's big enough
          if (matched < 1 and len(block)/len(query_track) >= matched) or \
          (matched >= 1 and len(block) >= matched):
            blocks[chromosome_name].append(block)
          # start a new block with the current match
          block = [i]
      # save last block if it's big enough
      if (matched < 1 and len(block)/len(query_track) >= matched) or \
      (matched >= 1 and len(block) >= matched):
        blocks[chromosome_name].append(block)
    # fetch result tracks
    families = set()
    tracks = []
    for chromosome_name, blocks in blocks.items():
      stripped_chromosome_name = _stripEscapeCharacters(chromosome_name)
      query = Query(chromosome_name)\
                .limit_fields('name')\
                .verbatim()\
                .return_fields('genus', 'species')
      result = chromosome_index.search(query)
      chromosome = result.docs[0]
      for block in blocks:
        first = block[0]
        last = block[-1]
        num_genes = last-first+1
        query = Query(chromosome_name)\
                  .limit_fields('chromosome')\
                  .verbatim()\
                  .add_filter(NumericFilter('index', first, last))\
                  .sort_by('index')\
                  .return_fields('name', 'family')\
                  .paging(0, num_genes)
        result = gene_index.search(query)
        # format and return
        track = {
            'name': stripped_chromosome_name,
            'genus': chromosome.genus,
            'species': chromosome.species,
            'genes': [],
            'families': [],
          }
        for doc in result.docs:
          track['genes'].append(_stripEscapeCharacters(doc.name))
          track['families'].append(_stripEscapeCharacters(doc.family))
        tracks.append(track)
    return tracks
