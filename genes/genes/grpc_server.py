# dependencies
from grpc.experimental import aio
# module
from genes.proto.genes_service.v1 import genes_pb2
from genes.proto.genes_service.v1 import genes_pb2_grpc
from genes.proto.gene.v1 import gene_pb2


class Genes(genes_pb2_grpc.GenesServicer):

  def __init__(self, handler):
    self.handler = handler

  async def Get(self, request, context):
    genes = await self.handler.process(request.names)
    gene_messages = list(map(lambda g:
      gene_pb2.Gene(
        name=g['name'],
        fmin=g['fmin'],
        fmax=g['fmax'],
        strand=g['strand'],
        family=g['family'],
        chromosome=g['chromosome'],
      ), genes))
    return genes_pb2.GenesGetReply(genes=gene_messages)


async def run_grpc_server(host, port, handler):
  server = aio.server()
  server.add_insecure_port(f'{host}:{port}')
  servicer = Genes(handler)
  genes_pb2_grpc.add_GenesServicer_to_server(servicer, server)
  await server.start()
  await server.wait_for_termination()
