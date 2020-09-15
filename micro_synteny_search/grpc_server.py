# dependencies
from grpc.experimental import aio
# module
import microsyntenysearch_pb2
import microsyntenysearch_pb2_grpc


class MicroSyntenySearch(microsyntenysearch_pb2_grpc.MicroSyntenySearchServicer):

  def __init__(self, handler):
    self.handler = handler

  async def Search(self, request, context):
    tracks = await self.handler.process(request.query, request.matched, request.intermediate)
    return microsyntenysearch_pb2.SearchReply(tracks=tracks)


async def run_grpc_server(host, port, handler):
  server = aio.server()
  server.add_insecure_port(f'{host}:{port}')
  servicer = MicroSyntenySearch(handler)
  microsyntenysearch_pb2_grpc.add_MicroSyntenySearchServicer_to_server(servicer, server)
  await server.start()
  await server.wait_for_termination()
