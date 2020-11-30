# dependencies
from grpc.experimental import aio
# module
from services import chromosomesearch_pb2
from services import chromosomesearch_pb2_grpc


class ChromosomeSearch(chromosomesearch_pb2_grpc.ChromosomeSearchServicer):

  def __init__(self, handler):
    self.handler = handler

  async def Search(self, request, context):
    chromosomes = await self.handler.process(request.query)
    return chromosomesearch_pb2.ChromosomeSearchReply(chromosomes=chromosomes)


async def run_grpc_server(host, port, handler):
  server = aio.server()
  server.add_insecure_port(f'{host}:{port}')
  servicer = ChromosomeSearch(handler)
  chromosomesearch_pb2_grpc.add_ChromosomeSearchServicer_to_server(servicer, server)
  await server.start()
  await server.wait_for_termination()
