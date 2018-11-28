# This file contains the definition of the RESTful API. It's responsible for
# receiving requests, parsing query string parameters, and encoding responses.
from aiohttp import web
import asyncio
import aiohttp_cors
import json
# local
import db
import query_string_parser as qsp


# the web application
app = web.Application()
app.cleanup_ctx.append(db.db_engine)


#micro/genes-to-tracks?genes&neighbors  # multi micro and construct query track
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
    response = await db.genesToTracks(params['genes'], params['neighbors'])
    # encode and send the response
    return web.Response(text=json.dumps(response), status=200)
  except Exception as e:
    response_obj = {'status' : 'failed', 'reason': str(e)}
    return web.Response(text=json.dumps(response_obj), status=500)
app.router.add_get('/micro/genes-to-tracks', genesToTracks)


#micro/find-similar-tracks?families&minmatched&maxinsert
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
    response = await db.searchMicroSyntenyTracks(
      params['families'],
      params['minmatched'],
      params['maxinsert']
    )
    # encode and send the response
    return web.Response(text=json.dumps(response), status=200)
  except Exception as e:
    response_obj = {'status' : 'failed', 'reason': str(e)}
    return web.Response(text=json.dumps(response_obj), status=500)
app.router.add_post('/micro/find-similar-tracks', findSimilarTracks)


#macro/compute-syntenic-blocks?chromosome&minmatched&maxinsert&familymask&targets
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
    response = await db.macroSyntenyTracks(
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
app.router.add_post('/macro/compute-syntenic-blocks', computeSyntenicBlocks)


#macro/get-homologous-genes?chromosome&families  # global plots
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
    response = await db.globalPlot(params['chromosome'], params['families'])
    # encode and send the response
    return web.Response(text=json.dumps(response), status=200)
  except Exception as e:
    response_obj = {'status' : 'failed', 'reason': str(e)}
    return web.Response(text=json.dumps(response_obj), status=500)
app.router.add_get('/macro/get-homologous-genes', getHomologousGenes)


#macro/get-chromosome?chromosome
async def getChromosome(request):
  try:
    # parse the query string parameters
    params = qsp.validate(
      request.query,
      {
        'chromosome': qsp.Parser(qsp.Type.NON_EMPTY_STRING),
      }
    )
    # process the request
    response = await db.getChromosome(params['chromosome'])
    # encode and send the response
    return web.Response(text=json.dumps(response), status=200)
  except Exception as e:
    response_obj = {'status' : 'failed', 'reason': str(e)}
    return web.Response(text=json.dumps(response_obj), status=500)
app.router.add_get('/macro/get-chromosome', getChromosome)


# Configure default CORS settings.
cors = aiohttp_cors.setup(app, defaults={
  '*': aiohttp_cors.ResourceOptions(
         allow_credentials=True,
         expose_headers='*',
         allow_headers='*',
       )
})


# Configure CORS on all routes.
for route in app.router.routes():
  cors.add(route)


if __name__ == '__main__':
  # TODO: make host, port, etc configurable at runtime
  web.run_app(app, port=1234)
