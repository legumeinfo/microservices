# dependencies
import grpc
from grpc.experimental import aio
# module
import pairwisemacrosyntenyblocks_pb2
import pairwisemacrosyntenyblocks_pb2_grpc


class PairwiseMacroSyntenyBlocks(pairwisemacrosyntenyblocks_pb2_grpc.PairwiseMacroSyntenyBlocksServicer):

  def __init__(self, handler):
    self.handler = handler

  async def Compute(self, request, context):
    chromosome = request.chromosome
    target = request.target
    matched = request.matched
    intermediate = request.intermediate
    mask = request.mask
    try:
      self.handler.parseArguments(chromosome, target, matched, intermediate, mask)
    except Exception as e:
      # raise a gRPC INVALID ARGUMENT error
      await context.abort(grpc.StatusCode.INVALID_ARGUMENT, 'Required arguments are missing or given arguments have invalid values')
    blocks = await self.handler.process(chromosome, target, matched, intermediate, mask)
    if blocks is None:
      # raise a gRPC NOT FOUND error
      await context.abort(grpc.StatusCode.NOT_FOUND, 'Chromosome not found')
    return pairwisemacrosyntenyblocks_pb2.ComputeReply(blocks=blocks)


async def run_grpc_server(host, port, handler):
  server = aio.server()
  server.add_insecure_port(f'{host}:{port}')
  servicer = PairwiseMacroSyntenyBlocks(handler)
  pairwisemacrosyntenyblocks_pb2_grpc\
    .add_PairwiseMacroSyntenyBlocksServicer_to_server(servicer, server)
  await server.start()
  await server.wait_for_termination()
