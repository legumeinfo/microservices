# dependencies
from grpc.experimental import aio
# module
import genes_pb2
import genes_pb2_grpc


class Genes(genes_pb2_grpc.GenesServicer):

  def __init__(self, handler):
    self.handler = handler

  async def Search(self, request, context):
    genes = await self.handler.process(request.genes)
    return genes_pb2.GetReply(genes=genes)


async def run_grpc_server(host, port, handler):
  server = aio.server()
  server.add_insecure_port(f'{host}:{port}')
  servicer = Genes(handler)
  genes_pb2_grpc.add_GenesServicer_to_server(servicer, server)
  await server.start()
  await server.wait_for_termination()
