# Python
import logging

# isort: split

# dependencies
from grpc.experimental import aio

# isort: split

# module
# isort: off
# from macro_synteny_blocks.proto.pairwisemacrosyntenyblocks_service.v1
#   import pairwisemacrosyntenyblocks_pb2
# from macro_synteny_blocks.proto.pairwisemacrosyntenyblocks_service.v1
#   import pairwisemacrosyntenyblocks_pb2_grpc
# NOTE: the following imports are a temporary workaround for a known protobuf
# bug; the commented imports above should be used when the bug is fixed:
# https://github.com/protocolbuffers/protobuf/issues/10075
from macro_synteny_blocks import proto  # noqa: F401
from pairwisemacrosyntenyblocks_service.v1 import (
    pairwisemacrosyntenyblocks_pb2,
    pairwisemacrosyntenyblocks_pb2_grpc,
)
from chromosome_service.v1 import chromosome_pb2, chromosome_pb2_grpc
from genes_service.v1 import genes_pb2, genes_pb2_grpc

# isort: on


async def getChromosome(chromosome_name, address):
    """
    Fetch chromosome data from the chromosome microservice.

    Parameters:
        chromosome_name (str): Name of the chromosome to fetch.
        address (str): Address of the chromosome microservice.

    Returns:
        tuple: (gene_families list, gene_names list, chromosome_length), or None if not found.
    """
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
        return (
            list(result.chromosome.track.families),
            list(result.chromosome.track.genes),
            result.chromosome.length
        )
    except Exception as e:
        logging.error(e)
        return None


async def getGenes(gene_names, address):
    """
    Fetch gene data from the genes microservice.

    Parameters:
        gene_names (list): List of gene names to fetch.
        address (str): Address of the genes microservice.

    Returns:
        list: Gene objects with fmin/fmax positions, or None if error.
    """
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
    identity=None,
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
                identity=identity,
            )
        )
        return result.blocks
    except Exception as e:
        logging.error(e)
        return None
