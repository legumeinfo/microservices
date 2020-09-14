# dependencies
import grpc
from grpc.experimental import aio
# module
import chromosome_pb2
import chromosome_pb2_grpc


class Chromosome(chromosome_pb2_grpc.ChromosomeServicer):

  def __init__(self, handler):
    self.handler = handler

  async def Get(self, request, context):
    chromosome = await self.handler.process(request.chromosome)
    if chromosome is None:
      # raise a gRPC NOT FOUND error
      await context.abort(grpc.StatusCode.NOT_FOUND, 'Chromosome not found')
    return chromosome_pb2.GetReply(length=chromosome.length, genus=chromosome.genus, species=chromosome.species, genes=chromosome.gnes, families=chromosome.families)


async def run_grpc_server(host, port, handler):
  server = aio.server()
  server.add_insecure_port(f'{host}:{port}')
  servicer = Chromosome(handler)
  chromosome_pb2_grpc.add_ChromosomeServicer_to_server(servicer, server)
  await server.start()
  await server.wait_for_termination()
