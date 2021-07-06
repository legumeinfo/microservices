# Python
import asyncio
# dependencies
from redisearch import Query
# module
from macro_synteny_blocks.aioredisearch import Client
from macro_synteny_blocks.grpc_client import computePairwiseMacroSyntenyBlocks


class RequestHandler:

  def __init__(self, redis_connection, pairwise_address):
    self.redis_connection = redis_connection
    self.pairwise_address = pairwise_address

  def parseArguments(self, chromosome, matched, intermediate, mask, targets, metrics):
    iter(chromosome)  # TypeError if not iterable
    iter(targets)  # TypeError if not iterable
    iter(metrics)  # TypeError if not iterable
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
    return chromosome, matched, intermediate, mask, targets, metrics

  def _grpcBlockToDictBlock(self, grpc_block):
    dict_block = {
        'i': grpc_block.i,
        'j': grpc_block.j,
        'fmin': grpc_block.fmin,
        'fmax': grpc_block.fmax,
        'orientation': grpc_block.orientation,
      }
    if grpc_block.optionalMetrics:
      dict_block['optionalMetrics'] = list(grpc_block.optionalMetrics)
    return dict_block

  async def _getTargets(self, targets, chromosome_index):
    if targets:
      return targets
    # count how many chromosomes there are
    query = Query('*').paging(0, 0)
    result = await chromosome_index.search(query)
    num_chromosomes = result.total
    # get all the chromosomes
    query = Query('*')\
              .return_fields('name')\
              .paging(0, num_chromosomes)
    result = await chromosome_index.search(query)
    return list(map(lambda doc: doc.name, result.docs))


  async def _computePairwiseBlocks(self, chromosome, target, matched, intermediate, mask, metrics, chromosome_index, grpc_decode):
    # compute the blocks for the target chromosome
    blocks = await computePairwiseMacroSyntenyBlocks(chromosome, target, matched, intermediate, mask, metrics, self.pairwise_address)
    if not blocks:  # true for None or []
      return None
    # fetch the chromosome object
    doc = await chromosome_index.load_document(f'chromosome:{target}')
    blocks_object = {
        'chromosome': target,
        'genus': doc.genus,
        'species': doc.species,
      }
    # decode the blocks if not outputting gRPC
    if grpc_decode:
      blocks_object['blocks'] = list(map(self._grpcBlockToDictBlock, blocks))
    else:
      blocks_object['blocks'] = blocks
    return blocks_object

  async def process(self, chromosome, matched, intermediate, mask, targets, metrics, grpc_decode=False):
    # connect to the index
    chromosome_index = Client('chromosomeIdx', conn=self.redis_connection)
    # get all chromosome names if no targets are specified
    targets = await self._getTargets(targets, chromosome_index)
    # compute blocks for each chromosome
    target_blocks = await asyncio.gather(*[
        self._computePairwiseBlocks(chromosome, name, matched, intermediate, mask, metrics, chromosome_index, grpc_decode)
        for name in targets
      ])
    # remove the targets that didn't return any blocks
    filtered_target_blocks = list(filter(lambda b: b is not None, target_blocks))
    return filtered_target_blocks
