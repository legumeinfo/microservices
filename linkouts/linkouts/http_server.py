# dependencies
import aiohttp_cors
from aiohttp import web

GENES_PATH='/gene_linkouts'
GENOMIC_REGIONS_PATH='/genomic_region_linkouts'
GENES_QUERY='genes'
GENOMIC_REGIONS_QUERY='genomic_regions'

async def http_genes_get_handler(request):
  # parse the query from the request query string
  ids = request.rel_url.query[GENES_QUERY]
  ids = ids.split(",")
  handler = request.app['handler']
  linkouts = await handler.process_genes(ids)
  return web.json_response(linkouts)

async def http_genes_post_handler(request):
  # parse the query from the request POST data
  data = await request.json()
  ids = data.get(GENES_QUERY, [])
  handler = request.app['handler']
  linkouts = await handler.process_genes(ids)
  return web.json_response(linkouts)

async def http_genomic_regions_get_handler(request):
  # parse the query from the request query string
  ids = request.rel_url.query[GENOMIC_REGIONS_QUERY]
  ids = ids.split(",")
  handler = request.app['handler']
  linkouts = await handler.process_genomic_regions(ids)
  return web.json_response(linkouts)

async def http_genomic_regions_post_handler(request):
  # parse the query from the request POST data
  data = await request.json()
  ids = data.get(GENOMIC_REGIONS_QUERY, [])
  handler = request.app['handler']
  linkouts = await handler.process_genomic_regions(ids)
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
  route = app.router.add_post(GENES_PATH, http_genes_post_handler)
  cors.add(route)
  route = app.router.add_get(GENES_PATH, http_genes_get_handler)
  cors.add(route)
  route = app.router.add_post(GENOMIC_REGIONS_PATH, http_genomic_regions_post_handler)
  cors.add(route)
  route = app.router.add_get(GENOMIC_REGIONS_PATH, http_genomic_regions_get_handler)
  cors.add(route)
  # run the app
  web.run_app(app)
  # TODO: what about teardown? runner.cleanup()
