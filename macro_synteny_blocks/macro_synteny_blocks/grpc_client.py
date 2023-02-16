# Python
import logging

# dependencies
from grpc.experimental import aio

# module
# from macro_synteny_blocks.proto.pairwisemacrosyntenyblocks_service.v1
#   import pairwisemacrosyntenyblocks_pb2
# from macro_synteny_blocks.proto.pairwisemacrosyntenyblocks_service.v1
#   import pairwisemacrosyntenyblocks_pb2_grpc
# NOTE: the following imports are a temporary workaround for a known protobuf
# bug; the commented imports above should be used when the bug is fixed:
# https://github.com/protocolbuffers/protobuf/issues/10075
from macro_synteny_blocks import proto  # noqa: F401
from pairwisemacrosyntenyblocks_service.v1 import pairwisemacrosyntenyblocks_pb2
from pairwisemacrosyntenyblocks_service.v1 import pairwisemacrosyntenyblocks_pb2_grpc


async def computePairwiseMacroSyntenyBlocks(
    chromosome,
    target,
    matched,
    intermediate,
    mask,
    metrics,
    chromosome_genes,
    chromosome_length,
    address,
):
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
                chromosomeGenes=chromosome_genes,
                chromosomeLength=chromosome_length,
            )
        )
        return result.blocks
    except Exception as e:
        logging.error(e)
        return None
