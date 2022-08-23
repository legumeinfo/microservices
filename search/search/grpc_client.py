# Python
import logging
# dependencies
from grpc.experimental import aio
# module
from search.proto.genesearch_service.v1 import genesearch_pb2
from search.proto.genesearch_service.v1 import genesearch_pb2_grpc
from search.proto.chromosomesearch_service.v1 import chromosomesearch_pb2
from search.proto.chromosomesearch_service.v1 import chromosomesearch_pb2_grpc
from search.proto.chromosomeregion_service.v1 import chromosomeregion_pb2
from search.proto.chromosomeregion_service.v1 import chromosomeregion_pb2_grpc


async def gene_search(query, address):
  # fetch channel every time to support dynamic services
  channel = aio.insecure_channel(address)
  await channel.channel_ready()
  stub = genesearch_pb2_grpc.GeneSearchStub(channel)
  try:
    results = await stub.Search(genesearch_pb2.GeneSearchRequest(query=query))
    return results.genes
  except Exception as e:
    logging.error(e)
    return []


async def chromosome_search(query, address):
  # fetch channel every time to support dynamic services
  channel = aio.insecure_channel(address)
  await channel.channel_ready()
  stub = chromosomesearch_pb2_grpc.ChromosomeSearchStub(channel)
  try:
    results = await stub.Search(chromosomesearch_pb2.ChromosomeSearchRequest(query=query))
    return results.chromosomes
  except Exception as e:
    logging.error(e)
    return []


async def chromosome_region(chromosome, start, stop, address):
  # fetch channel every time to support dynamic services
  channel = aio.insecure_channel(address)
  await channel.channel_ready()
  stub = chromosomeregion_pb2_grpc.ChromosomeRegionStub(channel)
  try:
    response = await stub.Get(chromosomeregion_pb2.ChromosomeRegionGetRequest(chromosome=chromosome, start=start, stop=stop))
    return [response.region]
  except Exception as e:
    logging.error(e)
    return []
