# dependencies
import grpc
from grpc.experimental import aio

# module
# from search.proto.search_service.v1 import search_pb2
# from search.proto.search_service.v1 import search_pb2_grpc
# NOTE: the following imports are a temporary workaround for a known protobuf
# bug; the commented imports above should be used when the bug is fixed:
# https://github.com/protocolbuffers/protobuf/issues/10075
from search import proto  # noqa: F401
from search_service.v1 import search_pb2
from search_service.v1 import search_pb2_grpc


class Search(search_pb2_grpc.SearchServicer):
    def __init__(self, handler):
        self.handler = handler

    # the method that actually handles requests
    async def _search(self, request, context):
        results = await self.handler.process(request.query)
        reply = search_pb2.SearchReply()
        if "genes" in results:
            reply.genes.extend(results["genes"])
        if "regions" in results:
            reply.regions.extend(results["regions"])
        return reply

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
            await context.abort(grpc.StatusCode.INTERNAL, "Internal server error")


async def run_grpc_server(host, port, query_parser):
    server = aio.server()
    server.add_insecure_port(f"{host}:{port}")
    servicer = Search(query_parser)
    search_pb2_grpc.add_SearchServicer_to_server(servicer, server)
    await server.start()
    await server.wait_for_termination()
    # TODO: what about teardown? server.stop(None)
