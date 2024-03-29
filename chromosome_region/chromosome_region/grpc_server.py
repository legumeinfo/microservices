# dependencies
import grpc
from grpc.experimental import aio

# isort: split

# module
# isort: off
# from chromosome_region.proto.chromosomeregion_service.v1 import chromosomeregion_pb2
# from chromosome_region.proto.chromosomeregion_service.v1
#   import chromosomeregion_pb2_grpc
# from chromosome_region.proto.region.v1 import region_pb2
# NOTE: the following imports are a temporary workaround for a known protobuf
# bug; the commented imports above should be used when the bug is fixed:
# https://github.com/protocolbuffers/protobuf/issues/10075
from chromosome_region import proto  # noqa: F401
from chromosomeregion_service.v1 import chromosomeregion_pb2, chromosomeregion_pb2_grpc
from region.v1 import region_pb2

# isort: on


class ChromosomeRegion(chromosomeregion_pb2_grpc.ChromosomeRegionServicer):
    def __init__(self, handler):
        self.handler = handler

    # create a context done callback that raises the given exception
    def _exceptionCallbackFactory(self, exception):
        def exceptionCallback(call):
            raise exception

        return exceptionCallback

    # the method that actually handles requests
    async def _get(self, request, context):
        region = await self.handler.process(
            request.chromosome, request.start, request.stop
        )
        if region is None:
            # raise a gRPC NOT FOUND error
            await context.abort(grpc.StatusCode.NOT_FOUND, "Region not found")
        region_message = region_pb2.Region(
            gene=region["gene"], neighbors=region["neighbors"]
        )
        return chromosomeregion_pb2.ChromosomeRegionGetReply(region=region_message)

    # implements the service's API
    async def Get(self, request, context):
        # subvert the gRPC exception handler via a try/except block
        try:
            return await self._get(request, context)
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
    servicer = ChromosomeRegion(handler)
    chromosomeregion_pb2_grpc.add_ChromosomeRegionServicer_to_server(servicer, server)
    await server.start()
    await server.wait_for_termination()
    # TODO: what about teardown? server.stop(None)
