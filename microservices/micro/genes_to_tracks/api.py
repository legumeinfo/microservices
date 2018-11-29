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


#/genes-to-tracks?genes&neighbors  # multi micro and construct query track
async def genesToTracks(request):
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
route = app.router.add_get('/genes-to-tracks', genesToTracks)
cors.add(route)


if __name__ == '__main__':
  web.run_app(app, port=1234)
