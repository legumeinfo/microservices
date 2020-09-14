# dependencies
from redisearch import Client, Query


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
      query = Query(name)\
                .limit_fields('name')\
                .verbatim()
      result = gene_index.search(query)
      for d in result.docs:
        gene = {
          'name': d.name,
          'chromosome': d.chromosome,
          'family': d.family,
          'fmin': d.fmin,
          'fmax': d.fmax,
          'strand': d.strand,
        }
        genes.append(gene)
    return genes
