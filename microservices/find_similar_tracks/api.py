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


#/find-similar-tracks?families&minmatched&maxinsert
async def findSimilarTracks(request):
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
route = app.router.add_post('/micro/find-similar-tracks', findSimilarTracks)
cors.add(route)


if __name__ == '__main__':
  web.run_app(app, port=1234)
