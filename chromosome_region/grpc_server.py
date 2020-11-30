# dependencies
import grpc
from grpc.experimental import aio
# module
from services import chromosomeregion_pb2
from services import chromosomeregion_pb2_grpc
from structures import region_pb2


class ChromosomeRegion(chromosomeregion_pb2_grpc.ChromosomeRegionServicer):

  def __init__(self, handler):
    self.handler = handler

  async def Get(self, request, context):
    region = await self.handler.process(request.chromosome, request.start, request.stop)
    if region is None:
      # raise a gRPC NOT FOUND error
      await context.abort(grpc.StatusCode.NOT_FOUND, 'Region not found')
    region_message = region_pb2.Region(gene=region['gene'], neighbors=region['neighbors'])
    return chromosomeregion_pb2.ChromosomeRegionGetReply(region=region_message)


async def run_grpc_server(host, port, handler):
  server = aio.server()
  server.add_insecure_port(f'{host}:{port}')
  servicer = ChromosomeRegion(handler)
  chromosomeregion_pb2_grpc.add_ChromosomeRegionServicer_to_server(servicer, server)
  await server.start()
  await server.wait_for_termination()
