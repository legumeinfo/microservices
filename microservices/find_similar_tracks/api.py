import json
from aiohttp import web
# local
from core import query_string_parser as qsp
import find_similar_tracks.business as business


method = 'POST'
path = '/micro/find-similar-tracks'#?families&minmatched&maxinsert
async def handler(request):
  try:
    # parse the query string parameters
    params = qsp.validate(
      await request.json(),
      {
        'families': qsp.Parser(qsp.Type.STRING_LIST),
        'minmatched': qsp.Parser(qsp.Type.NATURAL_NUMBER, 4),
        'maxinsert': qsp.Parser(qsp.Type.WHOLE_NUMBER, 5),
      }
    )
    # process the request
    response = await business.searchMicroSyntenyTracks(
      params['families'],
      params['minmatched'],
      params['maxinsert']
    )
    # encode and send the response
    return web.Response(text=json.dumps(response), status=200)
  except Exception as e:
    response_obj = {'status' : 'failed', 'reason': str(e)}
    return web.Response(text=json.dumps(response_obj), status=500)


route = method, path, handler
