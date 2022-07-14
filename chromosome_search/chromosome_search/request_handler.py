# dependencies
from redis.commands.search import AsyncSearch
from redis.commands.search.query import Query


class RequestHandler:

  def __init__(self, redis_connection):
    self.redis_connection = redis_connection

  async def process(self, name):
    # connect to the index
    chromosome_index = AsyncSearch(self.redis_connection, index_name='chromosomeIdx')
    # search the chromosome index
    query = Query(name)\
              .limit_fields('name')\
              .return_fields('name')
    result = await chromosome_index.search(query)
    chromosomes = list(map(lambda d: d.name, result.docs))
    return chromosomes
