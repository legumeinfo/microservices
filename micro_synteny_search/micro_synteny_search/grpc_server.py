# dependencies
import grpc
from grpc.experimental import aio

# module
# from micro_synteny_search.proto.microsyntenysearch_service.v1
#   import microsyntenysearch_pb2
# from micro_synteny_search.proto.microsyntenysearch_service.v1
#   import microsyntenysearch_pb2_grpc
# from micro_synteny_search.proto.track.v1 import track_pb2
# NOTE: the following imports are a temporary workaround for a known protobuf
# bug; the commented imports above should be used when the bug is fixed:
# https://github.com/protocolbuffers/protobuf/issues/10075
from micro_synteny_search import proto  # noqa: F401
from microsyntenysearch_service.v1 import microsyntenysearch_pb2
from microsyntenysearch_service.v1 import microsyntenysearch_pb2_grpc
from track.v1 import track_pb2


class MicroSyntenySearch(microsyntenysearch_pb2_grpc.MicroSyntenySearchServicer):
    def __init__(self, handler):
        self.handler = handler

    # create a context done callback that raises the given exception
    def _exceptionCallbackFactory(self, exception):
        def exceptionCallback(call):
            raise exception

        return exceptionCallback

    # the method that actually handles requests
    async def _search(self, request, context):
        query = request.query
        matched = request.matched
        intermediate = request.intermediate
        try:
            self.handler.parseArguments(query, matched, intermediate)
        except Exception:
            # raise a gRPC INVALID ARGUMENT error
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Required arguments are missing or have invalid values",
            )
        tracks = await self.handler.process(query, matched, intermediate)
        track_messages = list(
            map(
                lambda t: track_pb2.MicroTrack(
                    name=t["name"],
                    track=track_pb2.Track(
                        genus=t["genus"],
                        species=t["species"],
                        genes=t["genes"],
                        families=t["families"],
                    ),
                ),
                tracks,
            )
        )
        return microsyntenysearch_pb2.MicroSyntenySearchReply(tracks=track_messages)

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


async def run_grpc_server(host, port, handler):
    server = aio.server()
    server.add_insecure_port(f"{host}:{port}")
    servicer = MicroSyntenySearch(handler)
    microsyntenysearch_pb2_grpc.add_MicroSyntenySearchServicer_to_server(
        servicer, server
    )
    await server.start()
    await server.wait_for_termination()
    # TODO: what about teardown? server.stop(None)
