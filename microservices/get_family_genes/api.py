import json
from aiohttp import web
# local
from core import query_string_parser as qsp
import get_family_genes.business as business


async def handler(app, raw_params):
  # parse the parameters
  params = qsp.validate(
    raw_params,
    {
      'families': qsp.Parser(qsp.Type.STRING_LIST),
    }
  )
  # process the request
  r = app['r_engine']
  families = params['families']
  return await business.getFamilyGenes(r, families)


method = 'GET'
path = '/family/get-family-genes'#?family
async def webHandler(request):
  try:
    params = await request.json()
    response = handler(request.app, params)
    return web.Response(text=json.dumps(response), status=200)
  except Exception as e:
    response_obj = {'status' : 'failed', 'reason': str(e)}
    return web.Response(text=json.dumps(response_obj), status=500)


route = method, path, handler, webHandler
