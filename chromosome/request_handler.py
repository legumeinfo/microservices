# module
from aioredisearch import Client


class RequestHandler:

  def __init__(self, redis_connection):
    self.redis_connection = redis_connection

  async def process(self, name):
    # connect to the index
    chromosome_index = Client('chromosomeIdx', conn=self.redis_connection)
    # get the chromosome
    chromosome_doc = await chromosome_index.load_document(f'chromosome:{name}')
    if not hasattr(chromosome_doc, 'name'):
      return None
    # get the chromosome gene names
    genes = await self.redis_connection.lrange(f'chromosome:{name}:genes', 0, -1)
    # get the chromosome gene families
    families = await self.redis_connection.lrange(f'chromosome:{name}:families', 0, -1)
    # build the chromosome
    chromosome = {
        'length': int(chromosome_doc.length),
        'genus': chromosome_doc.genus,
        'species': chromosome_doc.species,
        'genes': genes,
        'families': families,
      }
    return chromosome
