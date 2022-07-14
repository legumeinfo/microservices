# dependencies
from redis.commands.search import AsyncSearch
from redis.commands.search.query import Query


class RequestHandler:

  def __init__(self, redis_connection):
    self.redis_connection = redis_connection

  async def process(self, name):
    # connect to the index
    gene_index = AsyncSearch(self.redis_connection, index_name='geneIdx')
    # search the gene index
    query = Query(name)\
              .limit_fields('name')\
              .return_fields('name')
    result = await gene_index.search(query)
    genes = list(map(lambda d: d.name, result.docs))
    return genes
