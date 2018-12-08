import json
from aiohttp import web
# local
from core import query_string_parser as qsp
import compute_syntenic_blocks.business as business


async def handler(app, raw_params):
  # parse the parameters
  params = qsp.validate(
    raw_params,
    {
      'chromosome': qsp.Parser(qsp.Type.STRING_LIST),
      'minmatched': qsp.Parser(qsp.Type.NATURAL_NUMBER, 20),
      'maxinsert': qsp.Parser(qsp.Type.WHOLE_NUMBER, 10),
      'familymask': qsp.Parser(qsp.Type.WHOLE_NUMBER, 10),
      'targets': qsp.Parser(qsp.Type.NON_EMPTY_STRING_LIST, []),
    }
  )
  # process the request
  return await business.macroSyntenyTracks(
    app['r_engine'],
    params['chromosome'],
    params['minmatched'],
    params['maxinsert'],
    params['targets'],
    params['familymask']
  )



method = 'POST'
path = '/macro/compute-syntenic-blocks'#?chromosome&minmatched&maxinsert&familymask&targets
async def webHandler(request):
  try:
    params = await request.json()
    response = await handler(request.app, params)
    return web.Response(text=json.dumps(response), status=200)
  except Exception as e:
    response_obj = {'status' : 'failed', 'reason': str(e)}
    return web.Response(text=json.dumps(response_obj), status=500)


route = method, path, handler, webHandler
