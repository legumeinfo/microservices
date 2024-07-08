# dependencies
import grpc
from grpc.experimental import aio

# isort: split

# module
# isort: off
# from macro_synteny_paf.proto.macrosyntenypaf_service.v1
#   import macrosyntenypaf_pb2
# from macro_synteny_paf.proto.macrosyntenypaf_service.v1
#   import macrosyntenypaf_pb2_grpc
# NOTE: the following imports are a temporary workaround for a known protobuf
# bug; the commented imports above should be used when the bug is fixed:
# https://github.com/protocolbuffers/protobuf/issues/10075
from macro_synteny_paf import proto  # noqa: F401
from macrosyntenypaf_service.v1 import (
    macrosyntenypaf_pb2,
    macrosyntenypaf_pb2_grpc,
)

# isort: on


class MacroSyntenyPaf(macrosyntenypaf_pb2_grpc.MacroSyntenyPafServicer):
    def __init__(self, handler):
        self.handler = handler

    # create a context done callback that raises the given exception
    def _exceptionCallbackFactory(self, exception):
        def exceptionCallback(call):
            raise exception

        return exceptionCallback

    # the method that actually handles requests
    async def _compute(self, request, context):
        # required parameters
        chromosome = request.chromosome
        matched = request.matched
        intermediate = request.intermediate
        # optional parameters
        mask = request.mask or None
        targets = request.targets or None
        metrics = request.optionalMetrics or None
        chromosome_genes = request.chromosomeGenes or None
        chromosome_length = request.chromosomeLength or None
        try:
            (
                chromosome,
                matched,
                intermediate,
                mask,
                targets,
                metrics,
                chromosome_genes,
                chromosome_length,
            ) = self.handler.parseArguments(
                chromosome,
                matched,
                intermediate,
                mask,
                targets,
                metrics,
                chromosome_genes,
                chromosome_length,
            )
        except Exception:
            # raise a gRPC INVALID ARGUMENT error
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Required arguments are missing or given arguments have invalid values",
            )
        blocks = await self.handler.process(
            chromosome,
            matched,
            intermediate,
            mask,
            targets,
            metrics,
            chromosome_genes,
            chromosome_length,
        )
        return macrosyntenypaf_pb2.MacroSyntenyPafComputeReply(blocks=blocks)

    # implements the service's API
    async def Compute(self, request, context):
        # subvert the gRPC exception handler via a try/except block
        try:
            return await self._compute(request, context)
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
    servicer = MacroSyntenyPaf(handler)
    macrosyntenypaf_pb2_grpc.add_MacroSyntenyPafServicer_to_server(
        servicer, server
    )
    await server.start()
    await server.wait_for_termination()
    # TODO: what about teardown? server.stop(None)
