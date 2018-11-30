import json
from aiohttp import web
# local
from core import query_string_parser as qsp
import genes_to_tracks.business as business


method = 'GET'
path = '/micro/genes-to-tracks'#?genes&neighbors
async def handler(request):
  try:
    # parse the query string parameters
    params = qsp.validate(
      request.query,
      {
        'genes': qsp.Parser(qsp.Type.STRING_LIST),
        'neighbors': qsp.Parser(qsp.Type.NATURAL_NUMBER, 10),
      }
    )
    # process the request
    response = await business.genesToTracks(params['genes'], params['neighbors'])
    # encode and send the response
    return web.Response(text=json.dumps(response), status=200)
  except Exception as e:
    response_obj = {'status' : 'failed', 'reason': str(e)}
    return web.Response(text=json.dumps(response_obj), status=500)


route = method, path, handler
