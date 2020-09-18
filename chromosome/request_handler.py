# dependencies
from redisearch import Client


class RequestHandler:

  def __init__(self, redis_connection):
    self.redis_connection = redis_connection

  # TODO: use aioredis and call redisearch via .execute to prevent blocking
  # https://redislabs.com/blog/beyond-the-cache-with-python/
  async def process(self, name):
    # connect to the index
    chromosome_index = Client('chromosomeIdx', conn=self.redis_connection)
    # get the chromosome
    chromosome_doc = chromosome_index.load_document(f'chromosome:{name}')
    if not hasattr(chromosome_doc, 'name'):
      return None
    # TODO: make these requests asynchronously
    # get the chromosome gene names
    genes = self.redis_connection.lrange(f'chromosome:{name}:genes', 0, -1)
    # get the chromosome gene families
    families = self.redis_connection.lrange(f'chromosome:{name}:families', 0, -1)
    # build the chromosome
    chromosome = {
        'length': chromosome_doc.length,
        'genus': chromosome_doc.genus,
        'species': chromosome_doc.species,
        'genes': genes,
        'families': families,
      }
    return chromosome
