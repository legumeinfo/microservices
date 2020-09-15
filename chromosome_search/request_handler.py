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
  async def process(self, name):
    # connect to the index
    chromosome_index = Client('chromosomeIdx', conn=self.redis_connection)
    # search the chromosome index
    escaped_name = _escapeSpecialCharacters(name)
    query = Query(escaped_name)\
              .limit_fields('name')\
              .return_fields('name')
    result = chromosome_index.search(query)
    chromosomes = list(map(lambda d: _stripEscapeCharacters(d.name), result.docs))
    return chromosomes
