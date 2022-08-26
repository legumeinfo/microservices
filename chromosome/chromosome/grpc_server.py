# dependencies
import grpc
from grpc.experimental import aio
# module
import chromosome
from chromosome.proto.chromosome_service.v1 import chromosome_pb2
from chromosome.proto.chromosome_service.v1 import chromosome_pb2_grpc
from chromosome.proto.track.v1 import track_pb2


class Chromosome(chromosome_pb2_grpc.ChromosomeServicer):

  def __init__(self, handler):
    self.handler = handler

  # create a context done callback that raises the given exception
  def _exceptionCallbackFactory(self, exception):
    def exceptionCallback(call):
      raise exception
    return exceptionCallback

  # the method that actually handles requests
  async def _get(self, request, context):
    chromosome = await self.handler.process(request.name)
    if chromosome is None:
      # return a gRPC NOT FOUND error
      await context.abort(grpc.StatusCode.NOT_FOUND, 'Chromosome not found')
    return chromosome_pb2.ChromosomeGetReply(
      chromosome=track_pb2.Chromosome(
        length=chromosome['length'],
        track=track_pb2.Track(
          genus=chromosome['genus'],
          species=chromosome['species'],
          genes=chromosome['genes'],
          families=chromosome['families']
        )
      )
    )

  # implements the service's API
  async def Get(self, request, context):
    # subvert the gRPC exception handler via a try/except block
    try:
      return await self._get(request, context)
    # let errors we raised go by
    except aio.AbortError as e:
      raise e
    # raise an internal error to prevent internal info from being sent to users
    except Exception as e:
      # raise the exception after aborting so it gets logged
      # NOTE: gRPC docs says abort should raise an error but it doesn't...
      context.add_done_callback(self._exceptionCallbackFactory(e))
      # return a gRPC INTERNAL error
      await context.abort(grpc.StatusCode.INTERNAL, 'Internal server error')



async def run_grpc_server(host, port, handler):
  server = aio.server()
  server.add_insecure_port(f'{host}:{port}')
  servicer = Chromosome(handler)
  chromosome_pb2_grpc.add_ChromosomeServicer_to_server(servicer, server)
  await server.start()
  await server.wait_for_termination()
  # TODO: what about teardown? server.stop(None)
