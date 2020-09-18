# Python
import bisect
# dependencies
from redisearch import Client


class RequestHandler:

  def __init__(self, redis_connection):
    self.redis_connection = redis_connection

  # TODO: use aioredis and call redisearch via .execute to prevent blocking
  # https://redislabs.com/blog/beyond-the-cache-with-python/
  async def process(self, chromosome, start, stop):
    # connect to the index
    chromosome_index = Client('chromosomeIdx', conn=self.redis_connection)
    # get the chromosome
    chromosome_doc_id = f'chromosome:{chromosome}'
    chromosome_doc = chromosome_index.load_document(chromosome_doc_id)
    if not hasattr(chromosome_doc, 'name'):
      return None
    # TODO: make these requests asynchronously
    # get the chromosome gene locations
    fmins = list(map(int, self.redis_connection.lrange(f'{chromosome_doc_id}:fmins', 0, -1)))
    fmaxs = list(map(int, self.redis_connection.lrange(f'{chromosome_doc_id}:fmaxs', 0, -1)))
    # find the index bounds using binary search
    i = bisect.bisect_left(fmins, start)
    j = bisect.bisect_right(fmaxs, stop)
    # compute the number of flanking genes and retrieve only the center gene
    neighbors = j-i
    center = (i+j)//2
    gene = self.redis_connection.lindex(f'{chromosome_doc_id}:genes', center)
    return {'gene': gene, 'neighbors': neighbors}
