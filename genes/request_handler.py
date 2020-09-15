# dependencies
from redisearch import Client, Query


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
  async def process(self, names):
    # connect to the index
    gene_index = Client('geneIdx', conn=self.redis_connection)
    # search the gene index
    # TODO: is there a way to query for all genes exactly at once?
    genes = []
    for name in names:
      escaped_name = _escapeSpecialCharacters(name)
      query = Query(escaped_name)\
                .limit_fields('name')\
                .verbatim()\
                .return_fields('chromosome', 'fmin', 'fmax', 'family', 'strand')
      result = gene_index.search(query)
      for d in result.docs:
        gene = {
          'name': name,
          'chromosome': _stripEscapeCharacters(d.chromosome),
          'family': _stripEscapeCharacters(d.family),
          'fmin': int(d.fmin),
          'fmax': int(d.fmax),
          'strand': int(d.strand),
        }
        genes.append(gene)
    return genes
