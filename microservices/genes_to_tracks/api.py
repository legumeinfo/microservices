import json
from aiohttp import web
# local
from core import query_string_parser as qsp
import genes_to_tracks.business as business


async def handler(app, raw_params):
  # parse parameters
  params = qsp.validate(
    raw_params,
    {
      'genes': qsp.Parser(qsp.Type.STRING_LIST),
      'neighbors': qsp.Parser(qsp.Type.NATURAL_NUMBER, 10),
    }
  )
  # process the request
  r = app['r_engine']
  genes = params['genes']
  neighbors = params['neighbors']
  return await business.genesToTracks(r, genes, neighbors)


# web API

method = 'GET'
path = '/micro/genes-to-tracks'#?genes&neighbors
async def webHandler(request):
  try:
    params = request.query
    response = await handler(request.app, params)
    return web.Response(text=json.dumps(response), status=200)
  except Exception as e:
    response_obj = {'status' : 'failed', 'reason': str(e)}
    return web.Response(text=json.dumps(response_obj), status=500)


route = method, path, handler, webHandler
