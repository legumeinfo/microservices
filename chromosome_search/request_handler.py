# dependencies
from redisearch import Client, Query


class RequestHandler:

  def __init__(self, redis_connection):
    self.redis_connection = redis_connection

  # TODO: use aioredis and call redisearch via .execute to prevent blocking
  # https://redislabs.com/blog/beyond-the-cache-with-python/
  async def process(self, name):
    # connect to the index
    chromosome_index = Client('chromosomeIdx', conn=self.redis_connection)
    # search the chromosome index
    query = Query(name)\
              .limit_fields('name')\
              .return_fields('name')
    result = chromosome_index.search(query)
    chromosomes = list(map(lambda d: d.name, result.docs))
    return chromosomes
