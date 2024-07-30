# Python
import logging

# isort: split

# dependencies
from grpc.experimental import aio

# isort: split

# module
# isort: off
# from macro_synteny_paf.proto.genes_service.v1
#   import genes_pb2
# from macro_synteny_paf.proto.genes_service.v1
#   import genes_pb2_grpc
# from macro_synteny_paf.proto.chromosome_service.v1
#   import chromosome_pb2
# from macro_synteny_paf.proto.chromosome_service.v1
#   import chromosome_pb2_grpc
# from macro_synteny_paf.proto.macrosyntenyblocks_service.v1
#   import macrosyntenyblocks_pb2
# from macro_synteny_paf.proto.macrosyntenyblocks_service.v1
#   import macrosyntenyblocks_pb2_grpc
# NOTE: the following imports are a temporary workaround for a known protobuf
# bug; the commented imports above should be used when the bug is fixed:
# https://github.com/protocolbuffers/protobuf/issues/10075
from macro_synteny_paf import proto  # noqa: F401
from genes_service.v1 import genes_pb2, genes_pb2_grpc
from chromosome_service.v1 import chromosome_pb2, chromosome_pb2_grpc
from macrosyntenyblocks_service.v1 import macrosyntenyblocks_pb2, macrosyntenyblocks_pb2_grpc

# isort: on


async def getGenes(
    gene_names,
    address,
):
    # fetch channel every time to support dynamic services
    channel = aio.insecure_channel(address)
    await channel.channel_ready()
    stub = genes_pb2_grpc.GenesStub(channel)
    try:
        result = await stub.Get(
            genes_pb2.GenesGetRequest(
                names=gene_names,
            )
        )
        return result.genes
    except Exception as e:
        logging.error(e)
        return None

async def getChromosome(
    chromosome_name,
    address,
):
    # fetch channel every time to support dynamic services
    channel = aio.insecure_channel(address)
    await channel.channel_ready()
    stub = chromosome_pb2_grpc.ChromosomeStub(channel)
    try:
        result = await stub.Get(
            chromosome_pb2.ChromosomeGetRequest(
                name=chromosome_name,
            )
        )
        return result.chromosome
    except Exception as e:
        logging.error(e)
        return None

async def getChromosomeLength(
    chromosome_name,
    address,
):
    # fetch channel every time to support dynamic services
    channel = aio.insecure_channel(address)
    await channel.channel_ready()
    stub = chromosome_pb2_grpc.ChromosomeStub(channel)
    try:
        result = await stub.Get(
            chromosome_pb2.ChromosomeGetRequest(
                name=chromosome_name,
            )
        )
        return result.chromosome.length
    except Exception as e:
        logging.error(e)
        return None

async def computeMacroSyntenyBlocks(
    chromosome,
    matched,
    intermediate,
    mask,
    targets,
    metrics,
    chromosome_genes,
    chromosome_length,
    address,
):
    # fetch channel every time to support dynamic services
    channel = aio.insecure_channel(address)
    await channel.channel_ready()
    stub = macrosyntenyblocks_pb2_grpc.MacroSyntenyBlocksStub(channel)
    try:
        result = await stub.Compute(
            macrosyntenyblocks_pb2.MacroSyntenyBlocksComputeRequest(
                chromosome=chromosome,
                matched=matched,
                intermediate=intermediate,
                mask=mask,
                targets=targets,
                optionalMetrics=metrics,
                chromosomeGenes=chromosome_genes,
                chromosomeLength=chromosome_length,
            )
        )
        return result.blocks
    except Exception as e:
        logging.error(e)
        return None
