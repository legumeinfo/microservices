# dependencies
from redisearch import Client, Query


class RequestHandler:

  def __init__(self, redis_connection):
    self.redis_connection = redis_connection

  # TODO: use aioredis and call redisearch via .execute to prevent blocking
  # https://redislabs.com/blog/beyond-the-cache-with-python/
  async def process(self, name):
    # connect to the indexes
    chromosome_index = Client('chromosomeIdx', conn=self.redis_connection)
    gene_index = Client('geneIdx', conn=self.redis_connection)
    # get the chromosome
    query = Query(name)\
              .limit_fields('name')\
              .verbatim()
    result = chromosome_index.search(query)
    if result.total == 0:
      return None
    chromosome_doc = result.docs[0]
    chromosome = {
        'length': chromosome_doc.length,
        'genus': chromosome_doc.genus,
        'species': chromosome_doc.species,
        'genes': [],
        'families': [],
      }
    # count how many genes are on the chromosome
    query = Query(name)\
              .limit_fields('chromosome')\
              .verbatim()\
              .paging(0, 0)
    result = gene_index.search(query)
    num_genes = result.total
    # get the chromosome genes
    query = Query(name)\
              .limit_fields('chromosome')\
              .verbatim()\
              .sort_by('fmin')\
              .return_fields('name', 'family')\
              .paging(0, num_genes)
    result = gene_index.search(query)
    # TODO: query.sort_by('fmin') doesn't work
    #gene_docs = sorted(result.docs, key=lambda doc: int(doc.fmin))
    #for doc in gene_docs:
    for doc in result.docs:
      chromosome['genes'].append(doc.name)
      chromosome['families'].append(doc.family)
    return chromosome
