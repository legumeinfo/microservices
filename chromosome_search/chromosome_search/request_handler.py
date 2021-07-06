# dependencies
from redisearch import Query
# module
from chromosome_search.aioredisearch import Client


class RequestHandler:

  def __init__(self, redis_connection):
    self.redis_connection = redis_connection

  async def process(self, name):
    # connect to the index
    chromosome_index = Client('chromosomeIdx', conn=self.redis_connection)
    # search the chromosome index
    query = Query(name)\
              .limit_fields('name')\
              .return_fields('name')
    result = await chromosome_index.search(query)
    chromosomes = list(map(lambda d: d.name, result.docs))
    return chromosomes
