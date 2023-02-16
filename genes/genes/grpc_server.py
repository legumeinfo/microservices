# dependencies
import grpc
from grpc.experimental import aio

# isort: split

# module
# isort: off
# from genes.proto.genes_service.v1 import genes_pb2
# from genes.proto.genes_service.v1 import genes_pb2_grpc
# from genes.proto.gene.v1 import gene_pb2
# NOTE: the following imports are a temporary workaround for a known protobuf
# bug; the commented imports above should be used when the bug is fixed:
# https://github.com/protocolbuffers/protobuf/issues/10075
from genes import proto  # noqa: F401
from genes_service.v1 import genes_pb2, genes_pb2_grpc
from gene.v1 import gene_pb2

# isort: on


class Genes(genes_pb2_grpc.GenesServicer):
    def __init__(self, handler):
        self.handler = handler

    # create a context done callback that raises the given exception
    def _exceptionCallbackFactory(self, exception):
        def exceptionCallback(call):
            raise exception

        return exceptionCallback

    # the method that actually handles requests
    async def _get(self, request, context):
        genes = await self.handler.process(request.names)
        gene_messages = list(
            map(
                lambda g: gene_pb2.Gene(
                    name=g["name"],
                    fmin=g["fmin"],
                    fmax=g["fmax"],
                    strand=g["strand"],
                    family=g["family"],
                    chromosome=g["chromosome"],
                ),
                genes,
            )
        )
        return genes_pb2.GenesGetReply(genes=gene_messages)

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
    servicer = Genes(handler)
    genes_pb2_grpc.add_GenesServicer_to_server(servicer, server)
    await server.start()
    await server.wait_for_termination()
    # TODO: what about teardown? server.stop(None)
