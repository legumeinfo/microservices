from aiohttp import web
import json
# local
from core.cors import corsFactory
from core import query_string_parser as qsp
import business


# the web application
app = web.Application()
app.cleanup_ctx.append(business.db_engine)
cors = corsFactory(app)


#/compute-syntenic-blocks?chromosome&minmatched&maxinsert&familymask&targets
async def computeSyntenicBlocks(request):
  try:
    # parse the query string parameters
    params = qsp.validate(
      await request.json(),
      {
        'chromosome': qsp.Parser(qsp.Type.STRING_LIST),
        'minmatched': qsp.Parser(qsp.Type.NATURAL_NUMBER, 20),
        'maxinsert': qsp.Parser(qsp.Type.WHOLE_NUMBER, 10),
        'familymask': qsp.Parser(qsp.Type.WHOLE_NUMBER, 10),
        'targets': qsp.Parser(qsp.Type.NON_EMPTY_STRING_LIST, []),
      }
    )
    # process the request
    response = await business.macroSyntenyTracks(
      params['chromosome'],
      params['minmatched'],
      params['maxinsert'],
      params['targets'],
      params['familymask']
    )
    # encode and send the response
    return web.Response(text=json.dumps(response), status=200)
  except Exception as e:
    response_obj = {'status' : 'failed', 'reason': str(e)}
    return web.Response(text=json.dumps(response_obj), status=500)
route = app.router.add_post('/macro/compute-syntenic-blocks', computeSyntenicBlocks)
cors.add(route)


if __name__ == '__main__':
  web.run_app(app, port=1234)
