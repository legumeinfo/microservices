# dependencies
from grpc.experimental import aio
# module
from macro_synteny_blocks.proto.pairwisemacrosyntenyblocks_service.v1 import pairwisemacrosyntenyblocks_pb2
from macro_synteny_blocks.proto.pairwisemacrosyntenyblocks_service.v1 import pairwisemacrosyntenyblocks_pb2_grpc


async def computePairwiseMacroSyntenyBlocks(chromosome, target, matched, intermediate, mask, metrics, min_chromosome_genes, min_chromosome_length, address):
  # fetch channel every time to support dynamic services
  channel = aio.insecure_channel(address)
  await channel.channel_ready()
  stub = pairwisemacrosyntenyblocks_pb2_grpc.PairwiseMacroSyntenyBlocksStub(channel)
  try:
    result = await stub.Compute(
      pairwisemacrosyntenyblocks_pb2.PairwiseMacroSyntenyBlocksComputeRequest(
        chromosome=chromosome,
        target=target,
        matched=matched,
        intermediate=intermediate,
        mask=mask,
        optionalMetrics=metrics,
        optionalChromosomeGenes=min_chromosome_genes,
        optionalChromosomeLength=min_chromosome_length,
      ))
    return result.blocks
  except Exception as e:
    print(e)
    return None
