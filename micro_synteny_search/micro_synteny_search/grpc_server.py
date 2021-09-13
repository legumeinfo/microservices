# dependencies
import grpc
from grpc.experimental import aio
# module
from micro_synteny_search.proto.microsyntenysearch_service.v1 import microsyntenysearch_pb2
from micro_synteny_search.proto.microsyntenysearch_service.v1 import microsyntenysearch_pb2_grpc
from micro_synteny_search.proto.track.v1 import track_pb2


class MicroSyntenySearch(microsyntenysearch_pb2_grpc.MicroSyntenySearchServicer):

  def __init__(self, handler):
    self.handler = handler

  async def Search(self, request, context):
    query = request.query
    matched = request.matched
    intermediate = request.intermediate
    try:
      self.handler.parseArguments(query, matched, intermediate)
    except:
      # raise a gRPC INVALID ARGUMENT error
      await context.abort(grpc.StatusCode.INVALID_ARGUMENT, 'Required arguments are missing or have invalid values')
    tracks = await self.handler.process(query, matched, intermediate)
    track_messages = list(map(lambda t:
      track_pb2.MicroTrack(
        name=t['name'],
        track=track_pb2.Track(
          genus=t['genus'],
          species=t['species'],
          genes=t['genes'],
          families=t['families'],
        )
      ), tracks))
    return microsyntenysearch_pb2.MicroSyntenySearchReply(tracks=track_messages)


async def run_grpc_server(host, port, handler):
  server = aio.server()
  server.add_insecure_port(f'{host}:{port}')
  servicer = MicroSyntenySearch(handler)
  microsyntenysearch_pb2_grpc.add_MicroSyntenySearchServicer_to_server(servicer, server)
  await server.start()
  await server.wait_for_termination()
