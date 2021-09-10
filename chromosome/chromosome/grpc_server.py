# dependencies
import grpc
from grpc.experimental import aio
# module
import chromosome
from chromosome.proto.chromosome_service.v1 import chromosome_pb2
from chromosome.proto.chromosome_service.v1 import chromosome_pb2_grpc
from chromosome.proto.track.v1 import track_pb2


class Chromosome(chromosome_pb2_grpc.ChromosomeServicer):

  def __init__(self, handler):
    self.handler = handler

  async def Get(self, request, context):
    chromosome = await self.handler.process(request.name)
    if chromosome is None:
      # raise a gRPC NOT FOUND error
      await context.abort(grpc.StatusCode.NOT_FOUND, 'Chromosome not found')
    return chromosome_pb2.ChromosomeGetReply(
      chromosome=track_pb2.Chromosome(
        length=chromosome['length'],
        track=track_pb2.Track(
          genus=chromosome['genus'],
          species=chromosome['species'],
          genes=chromosome['genes'],
          families=chromosome['families']
        )
      )
    )


async def run_grpc_server(host, port, handler):
  server = aio.server()
  server.add_insecure_port(f'{host}:{port}')
  servicer = Chromosome(handler)
  chromosome_pb2_grpc.add_ChromosomeServicer_to_server(servicer, server)
  await server.start()
  await server.wait_for_termination()
