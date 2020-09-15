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

  # TODO: use aioredis and call redisearch via .execute to prevent blocking
  # https://redislabs.com/blog/beyond-the-cache-with-python/
  async def process(self, chromosome, start, stop):
    # connect to the index
    gene_index = Client('geneIdx', conn=self.redis_connection)
    # count how many genes fall into the chromosome interval
    escaped_chromosome = _escapeSpecialCharacters(chromosome)
    query = Query(escaped_chromosome)\
              .limit_fields('chromosome')\
              .verbatim()\
              .add_filter(NumericFilter('fmin', start, stop))\
              .add_filter(NumericFilter('fmax', start, stop))\
              .paging(0, 0)
    result = gene_index.search(query)
    if result.total == 0:
      return None
    # compute the number of flanking genes and retrieve only the center gene
    neighbors = result.total//2
    query = Query(escaped_chromosome)\
              .limit_fields('chromosome')\
              .verbatim()\
              .add_filter(NumericFilter('fmin', start, stop))\
              .add_filter(NumericFilter('fmax', start, stop))\
              .sort_by('fmin')\
              .return_fields('name')\
              .paging(neighbors, 1)
    result = gene_index.search(query)
    gene = _stripEscapeCharacters(result.docs[0].name)
    return {'gene': gene, 'neighbors': neighbors}
