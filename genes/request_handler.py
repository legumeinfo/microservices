# dependencies
from redisearch import Client


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
      doc = gene_index.load_document(f'gene:{name}')
      if hasattr(doc, 'name'):
        gene = {
          'name': name,
          'chromosome': doc.chromosome,
          'family': doc.family,
          'fmin': int(doc.fmin),
          'fmax': int(doc.fmax),
          'strand': int(doc.strand),
        }
        genes.append(gene)
    return genes
