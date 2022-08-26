# dependencies
import grpc
from grpc.experimental import aio
# module
from gene_search.proto.genesearch_service.v1 import genesearch_pb2
from gene_search.proto.genesearch_service.v1 import genesearch_pb2_grpc


class GeneSearch(genesearch_pb2_grpc.GeneSearchServicer):

  def __init__(self, handler):
    self.handler = handler

  # create a context done callback that raises the given exception
  def _exceptionCallbackFactory(self, exception):
    def exceptionCallback(call):
      raise exception
    return exceptionCallback

  # the method that actually handles requests
  async def _search(self, request, context):
    genes = await self.handler.process(request.query)
    return genesearch_pb2.GeneSearchReply(genes=genes)

  # implements the service's API
  async def Search(self, request, context):
    # subvert the gRPC exception handler via a try/except block
    try:
      return await self._search(request, context)
    # let errors we raised go by
    except aio.AbortError as e:
      raise e
    # raise an internal error to prevent non-gRPC info from being sent to users
    except Exception as e:
      # raise the exception after aborting so it gets logged
      # NOTE: gRPC docs says abort should raise an error but it doesn't...
      context.add_done_callback(self._exceptionCallbackFactory(e))
      # return a gRPC INTERNAL error
      await context.abort(grpc.StatusCode.INTERNAL, 'Internal server error')


async def run_grpc_server(host, port, handler):
  server = aio.server()
  server.add_insecure_port(f'{host}:{port}')
  servicer = GeneSearch(handler)
  genesearch_pb2_grpc.add_GeneSearchServicer_to_server(servicer, server)
  await server.start()
  await server.wait_for_termination()
  # TODO: what about teardown? server.stop(None)
