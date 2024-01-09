# dependencies
import aiohttp_cors
from aiohttp import web

GENES_PATH = "/gene_linkouts"
GENOMIC_REGIONS_PATH = "/genomic_region_linkouts"
GENE_FAMILIES_PATH = "/gene_family_linkouts"
PAN_GENE_SETS_PATH = "/pan_gene_set_linkouts"
GENES_QUERY = "genes"
GENOMIC_REGIONS_QUERY = "genomic_regions"
GENE_FAMILIES_QUERY = "gene_families"
PAN_GENE_SETS_QUERY = "pan_gene_sets"


async def http_genes_get_handler(request):
    # parse the query from the request query string
    try:
        ids = request.rel_url.query[GENES_QUERY]
    except KeyError:
        raise web.HTTPBadRequest(text="No " + GENES_QUERY + " supplied")
    ids = ids.split(",")
    handler = request.app["handler"]
    linkouts = handler.process_genes(ids)
    return web.json_response(linkouts)


async def http_genes_post_handler(request):
    # parse the query from the request POST data
    data = await request.json()
    ids = data.get(GENES_QUERY, [])
    if type(ids) != list:
        raise web.HTTPBadRequest(text=GENES_QUERY + " must be given as list")
    if len(ids) == 0:
        raise web.HTTPBadRequest(text="No " + GENES_QUERY + " supplied")

    handler = request.app["handler"]
    linkouts = handler.process_genes(ids)
    return web.json_response(linkouts)


async def http_genomic_regions_get_handler(request):
    # parse the query from the request query string
    try:
        ids = request.rel_url.query[GENOMIC_REGIONS_QUERY]
    except KeyError:
        raise web.HTTPBadRequest(text="No " + GENOMIC_REGIONS_QUERY + " supplied")
    ids = ids.split(",")
    handler = request.app["handler"]
    linkouts = handler.process_genomic_regions(ids)
    return web.json_response(linkouts)


async def http_genomic_regions_post_handler(request):
    # parse the query from the request POST data
    data = await request.json()
    ids = data.get(GENOMIC_REGIONS_QUERY, [])
    if type(ids) != list:
        raise web.HTTPBadRequest(text=GENOMIC_REGIONS_QUERY + " must be given as list")
    if len(ids) == 0:
        raise web.HTTPBadRequest(text="No " + GENOMIC_REGIONS_QUERY + " supplied")

    handler = request.app["handler"]
    linkouts = handler.process_genomic_regions(ids)
    return web.json_response(linkouts)

async def http_gene_families_get_handler(request):
    # parse the query from the request query string
    try:
        ids = request.rel_url.query[GENE_FAMILIES_QUERY]
    except KeyError:
        raise web.HTTPBadRequest(text="No " + GENE_FAMILIES_QUERY + " supplied")
    ids = ids.split(",")
    handler = request.app["handler"]
    linkouts = handler.process_gene_families(ids)
    return web.json_response(linkouts)


async def http_gene_families_post_handler(request):
    # parse the query from the request POST data
    data = await request.json()
    ids = data.get(GENE_FAMILIES_QUERY, [])
    if type(ids) != list:
        raise web.HTTPBadRequest(text=GENE_FAMILIES_QUERY + " must be given as list")
    if len(ids) == 0:
        raise web.HTTPBadRequest(text="No " + GENE_FAMILIES_QUERY + " supplied")

    handler = request.app["handler"]
    linkouts = handler.process_gene_families(ids)
    return web.json_response(linkouts)

async def http_pan_gene_sets_get_handler(request):
    # parse the query from the request query string
    try:
        ids = request.rel_url.query[PAN_GENE_SETS_QUERY]
    except KeyError:
        raise web.HTTPBadRequest(text="No " + PAN_GENE_SETS_QUERY + " supplied")
    ids = ids.split(",")
    handler = request.app["handler"]
    linkouts = handler.process_pan_gene_sets(ids)
    return web.json_response(linkouts)


async def http_pan_gene_sets_post_handler(request):
    # parse the query from the request POST data
    data = await request.json()
    ids = data.get(PAN_GENE_SETS_QUERY, [])
    if type(ids) != list:
        raise web.HTTPBadRequest(text=PAN_GENE_SETS_QUERY + " must be given as list")
    if len(ids) == 0:
        raise web.HTTPBadRequest(text="No " + PAN_GENE_SETS_QUERY + " supplied")

    handler = request.app["handler"]
    linkouts = handler.process_pan_gene_sets(ids)
    return web.json_response(linkouts)

def run_http_server(host, port, handler):
    # make the app
    app = web.Application()
    app["handler"] = handler
    # define the route and enable CORS
    cors = aiohttp_cors.setup(
        app,
        defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        },
    )
    route = app.router.add_post(GENES_PATH, http_genes_post_handler)
    cors.add(route)
    route = app.router.add_get(GENES_PATH, http_genes_get_handler)
    cors.add(route)
    route = app.router.add_post(GENOMIC_REGIONS_PATH, http_genomic_regions_post_handler)
    cors.add(route)
    route = app.router.add_get(GENOMIC_REGIONS_PATH, http_genomic_regions_get_handler)
    cors.add(route)
    route = app.router.add_post(GENE_FAMILIES_PATH, http_gene_families_post_handler)
    cors.add(route)
    route = app.router.add_get(GENE_FAMILIES_PATH, http_gene_families_get_handler)
    cors.add(route)
    route = app.router.add_post(PAN_GENE_SETS_PATH, http_pan_gene_sets_post_handler)
    cors.add(route)
    route = app.router.add_get(PAN_GENE_SETS_PATH, http_pan_gene_sets_get_handler)
    cors.add(route)
    # run the app
    web.run_app(app)
    # TODO: what about teardown? runner.cleanup()
