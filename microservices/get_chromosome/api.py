import json
from aiohttp import web
# local
from core import query_string_parser as qsp
import get_chromosome.business as business


method = 'GET'
path = '/macro/get-chromosome'#?chromosome
async def handler(request):
  try:
    # parse the query string parameters
    params = qsp.validate(
      request.query,
      {
        'chromosome': qsp.Parser(qsp.Type.NON_EMPTY_STRING),
      }
    )
    # process the request
    response = await business.getChromosome(params['chromosome'])
    # encode and send the response
    return web.Response(text=json.dumps(response), status=200)
  except Exception as e:
    response_obj = {'status' : 'failed', 'reason': str(e)}
    return web.Response(text=json.dumps(response_obj), status=500)


route = method, path, handler
