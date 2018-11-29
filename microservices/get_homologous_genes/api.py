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


#/get-homologous-genes?chromosome&families  # global plots
async def getHomologousGenes(request):
  try:
    # parse the query string parameters
    params = qsp.validate(
      request.query,
      {
        'chromosome': qsp.Parser(qsp.Type.NON_EMPTY_STRING),
        'families': qsp.Parser(qsp.Type.STRING_LIST),
      }
    )
    # process the request
    response = await business.globalPlot(params['chromosome'], params['families'])
    # encode and send the response
    return web.Response(text=json.dumps(response), status=200)
  except Exception as e:
    response_obj = {'status' : 'failed', 'reason': str(e)}
    return web.Response(text=json.dumps(response_obj), status=500)
route = app.router.add_get('/macro/get-homologous-genes', getHomologousGenes)
cors.add(route)


if __name__ == '__main__':
  web.run_app(app, port=1234)
