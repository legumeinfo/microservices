# Python
import asyncio
# dependencies
from redisearch import Client, Query
# module
from grpc_client import computePairwiseMacroSyntenyBlocks


def _grpcBlockToDictBlock(grpc_block):
  dict_block = {
      'i': grpc_block.i,
      'j': grpc_block.j,
      'fmin': grpc_block.fmin,
      'fmax': grpc_block.fmax,
      'orientation': grpc_block.orientation,
    }
  return dict_block


class RequestHandler:

  def __init__(self, redis_connection, pairwise_address):
    self.redis_connection = redis_connection
    self.pairwise_address = pairwise_address

  def parseArguments(self, chromosome, matched, intermediate, mask, targets):
    if type(chromosome) is not list:
      raise ValueError('query must be a list')
    if type(targets) is not list:
      raise ValueError('targets must be a list')
    matched = int(matched)  # ValueError
    intermediate = int(intermediate)  # ValueError
    if matched <= 0 or intermediate <= 0:
      raise ValueError('matched and intermediate must be positive')
    if mask is not None:
      mask = int(mask)
      if mask <= 0:
        raise ValueError('mask must be positive')
    else:
      mask = float('inf')
    return chromosome, matched, intermediate, mask, targets

  # TODO: use aioredis and call redisearch via .execute to prevent blocking
  # https://redislabs.com/blog/beyond-the-cache-with-python/
  async def process(self, chromosome, matched, intermediate, mask, targets, grpc_decode=False):
    # connect to the index
    chromosome_index = Client('chromosomeIdx', conn=self.redis_connection)
    # get all chromosome names if no targets are specified
    # TODO: is it worth just pulling in all the chromosome objects now?
    if not targets:
      # count how many chromosomes there are
      query = Query('*').paging(0, 0)
      result = chromosome_index.search(query)
      num_chromosomes = result.total
      # get all the chromosomes
      query = Query('*')\
                .return_fields('name')\
                .paging(0, num_chromosomes)
      result = chromosome_index.search(query)
      targets = list(map(lambda doc: doc.name, result.docs))
    # compute blocks for each chromosome
    blocks = await asyncio.gather(*[
        computePairwiseMacroSyntenyBlocks(chromosome, name, matched, intermediate, mask, self.pairwise_address)
        for name in targets
      ])
    target_blocks = []
    # get the chromosome for each chromosome that returned blocks
    for i, i_blocks in enumerate(blocks):
      if i_blocks:  # false for None or []
        name = targets[i]
        doc = chromosome_index.load_document(f'chromosome:{name}')
        i_chromosome_blocks = {
            'chromosome': name,
            'genus': doc.genus,
            'species': doc.species,
          }
        if grpc_decode:
          i_chromosome_blocks['blocks'] = list(map(_grpcBlockToDictBlock, i_blocks))
        else:
          i_chromosome_blocks['blocks'] = i_blocks
        target_blocks.append(i_chromosome_blocks)
    return target_blocks
