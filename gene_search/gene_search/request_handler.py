# dependencies
from redisearch import Query
# module
from gene_search.aioredisearch import Client


class RequestHandler:

  def __init__(self, redis_connection):
    self.redis_connection = redis_connection

  async def process(self, name):
    # connect to the index
    gene_index = Client('geneIdx', conn=self.redis_connection)
    # search the gene index
    query = Query(name)\
              .limit_fields('name')\
              .return_fields('name')
    result = await gene_index.search(query)
    genes = list(map(lambda d: d.name, result.docs))
    return genes
