# dependencies
from grpc.experimental import aio
# module
from search.proto.search_service.v1 import search_pb2
from search.proto.search_service.v1 import search_pb2_grpc


class Search(search_pb2_grpc.SearchServicer):

  def __init__(self, handler):
    self.handler = handler

  async def Search(self, request, context):
    results = await self.handler.process(request.query)
    reply = search_pb2.SearchReply()
    if 'genes' in results:
        reply.genes.extend(results['genes'])
    if 'regions' in results:
        reply.regions.extend(results['regions'])
    return reply


async def run_grpc_server(host, port, query_parser):
  server = aio.server()
  server.add_insecure_port(f'{host}:{port}')
  servicer = Search(query_parser)
  search_pb2_grpc.add_SearchServicer_to_server(servicer, server)
  await server.start()
  await server.wait_for_termination()
