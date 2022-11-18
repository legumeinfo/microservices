# dependencies
import aiohttp_cors
from aiohttp import web


async def http_genes_get_handler(request):
  # parse the query from the request query string
  ids = request.rel_url.query['genes']
  ids = ids.split(",")
  handler = request.app['handler']
  linkouts = handler.process_genes(ids)
  return web.json_response(linkouts)

async def http_genes_post_handler(request):
  # parse the query from the request POST data
  data = await request.json()
  ids = data.get('genes', [])
  handler = request.app['handler']
  linkouts = handler.process_genes(ids)
  return web.json_response(linkouts)

async def http_genomic_regions_get_handler(request):
  # parse the query from the request query string
  ids = request.rel_url.query['genomic_regions']
  ids = ids.split(",")
  handler = request.app['handler']
  linkouts = handler.process_genomic_regions(ids)
  return web.json_response(linkouts)

async def http_genomic_regions_post_handler(request):
  # parse the query from the request POST data
  data = await request.json()
  ids = data.get('genomic_regions', [])
  handler = request.app['handler']
  linkouts = handler.process_genomic_regions(ids)
  return web.json_response(linkouts)


def run_http_server(host, port, handler):
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
  route = app.router.add_post('/gene_linkouts', http_genes_post_handler)
  cors.add(route)
  route = app.router.add_get('/gene_linkouts', http_genes_get_handler)
  cors.add(route)
  route = app.router.add_post('/genomic_region_linkouts', http_genomic_regions_post_handler)
  cors.add(route)
  route = app.router.add_get('/genomic_region_linkouts', http_genomic_regions_get_handler)
  cors.add(route)
  # run the app
  #runner = web.AppRunner(app)
  web.run_app(app)
  #  await runner.setup()
  #  site = web.TCPSite(app, host, port)
  #  sys.stderr.write("got to start")
  #  await site.start()
  # TODO: what about teardown? runner.cleanup()
