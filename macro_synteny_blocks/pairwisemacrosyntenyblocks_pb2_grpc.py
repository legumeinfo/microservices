# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import pairwisemacrosyntenyblocks_pb2 as pairwisemacrosyntenyblocks__pb2


class PairwiseMacroSyntenyBlocksStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Compute = channel.unary_unary(
                '/pairwisemacrosyntenyblocks.PairwiseMacroSyntenyBlocks/Compute',
                request_serializer=pairwisemacrosyntenyblocks__pb2.ComputeRequest.SerializeToString,
                response_deserializer=pairwisemacrosyntenyblocks__pb2.ComputeReply.FromString,
                )


class PairwiseMacroSyntenyBlocksServicer(object):
    """Missing associated documentation comment in .proto file."""

    def Compute(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_PairwiseMacroSyntenyBlocksServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'Compute': grpc.unary_unary_rpc_method_handler(
                    servicer.Compute,
                    request_deserializer=pairwisemacrosyntenyblocks__pb2.ComputeRequest.FromString,
                    response_serializer=pairwisemacrosyntenyblocks__pb2.ComputeReply.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'pairwisemacrosyntenyblocks.PairwiseMacroSyntenyBlocks', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class PairwiseMacroSyntenyBlocks(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Compute(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/pairwisemacrosyntenyblocks.PairwiseMacroSyntenyBlocks/Compute',
            pairwisemacrosyntenyblocks__pb2.ComputeRequest.SerializeToString,
            pairwisemacrosyntenyblocks__pb2.ComputeReply.FromString,
            options, channel_credentials,
            call_credentials, compression, wait_for_ready, timeout, metadata)