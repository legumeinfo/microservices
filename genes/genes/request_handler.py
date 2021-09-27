# dependencies
#from redisearch import Client
from genes.aioredisearch import Client


class RequestHandler:

  def __init__(self, redis_connection):
    self.redis_connection = redis_connection

  def _geneDocToDict(self, gene_doc):
    return {
      'name': gene_doc.name,
      'chromosome': gene_doc.chromosome,
      'family': gene_doc.family or '',
      'fmin': int(gene_doc.fmin),
      'fmax': int(gene_doc.fmax),
      'strand': int(gene_doc.strand),
    }

  async def process(self, names):
    # connect to the index
    gene_index = Client('geneIdx', conn=self.redis_connection)
    # get the genes from the index
    gene_ids = map(lambda name: f'gene:{name}', names)
    docs = await gene_index.get(*gene_ids)
    genes = list(map(self._geneDocToDict, filter(lambda d: d is not None, docs)))
    return genes
