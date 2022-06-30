# dependencies
import aiohttp_cors
from aiohttp import web


async def http_post_handler(request):
  # parse the chromosome and parameters from the POST data
  data = await request.json()
  chromosome = data.get('chromosome')
  matched = data.get('matched')
  intermediate = data.get('intermediate')
  mask = data.get('mask')
  targets = data.get('targets', [])
  metrics = data.get('optionalMetrics', [])
  chromosome_genes = data.get('chromosome_genes', matched)
  chromosome_length = data.get('chromosome_length', 1)
  handler = request.app['handler']
  try:
    chromosome, matched, intermediate, mask, targets, metrics, chromosome_genes, chromosome_length = \
      handler.parseArguments(chromosome, matched, intermediate, mask, targets, metrics, chromosome_genes, chromsome_length)
  except:
    return web.HTTPBadRequest(text='Required arguments are missing or have invalid values')
  blocks = await handler.process(chromosome, matched, intermediate, mask, targets, metrics, chromosome_genes, chromsome_length, grpc_decode=True)
  json = web.json_response({'blocks': blocks})
  return json


async def run_http_server(host, port, handler):
  # make the app
  app = web.Application()
  app['handler'] = handler
  # define the route and enable CORS
  cors = aiohttp_cors.setup(app, defaults={
    '*': aiohttp_cors.ResourceOptions(
           allow_credentials=True,
           expose_headers='*',
           allow_headers='*',
         )
  })
  route = app.router.add_post('/', http_post_handler)
  cors.add(route)
  # run the app
  runner = web.AppRunner(app)
  await runner.setup()
  site = web.TCPSite(runner, host, port)
  await site.start()
  # TODO: what about teardown? runner.cleanup()
