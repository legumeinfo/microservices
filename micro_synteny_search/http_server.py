# dependencies
import aiohttp_cors
from aiohttp import web


async def http_post_handler(request):
  # parse the query from the POST data
  data = await request.json()
  query = data.get('query')
  matched = data.get('matched')
  intermediate = data.get('intermediate')
  try:
    if type(query) is not list:
      raise ValueError('query must be a list')
    matched = float(matched)
    intermediate = float(intermediate)
    if matched <= 0 or intermediate <= 0:
      raise ValueError('matched and intermediate must be positive')
  except:
    matched = None
    intermediate = None
  if query is None or matched is None or intermediate is None:
    return web.HTTPBadRequest(text='Required arguments are missing or have invalid values')
  handler = request.app['handler']
  tracks = await handler.process(query, matched, intermediate)
  return web.json_response({'tracks': tracks})


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
  route = app.router.add_post('/micro-synteny-search', http_post_handler)
  cors.add(route)
  # run the app
  runner = web.AppRunner(app)
  await runner.setup()
  site = web.TCPSite(runner, host, port)
  await site.start()
  # TODO: what about teardown? runner.cleanup()
