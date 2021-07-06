# dependencies
from grpc.experimental import aio
# module
from macro_synteny_blocks.services import pairwisemacrosyntenyblocks_pb2
from macro_synteny_blocks.services import pairwisemacrosyntenyblocks_pb2_grpc


async def computePairwiseMacroSyntenyBlocks(chromosome, target, matched, intermediate, mask, metrics, address):
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
        optionalMetrics=metrics
      ))
    return result.blocks
  except:
    return None
