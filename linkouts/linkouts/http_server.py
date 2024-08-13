# dependencies
import yaml
from pathlib import Path
import aiohttp_cors
from aiohttp import web

GENES_PATH = "/gene_linkouts"
GENES_QUERY = "genes"
GENOMIC_REGIONS_PATH = "/genomic_region_linkouts"
GENOMIC_REGIONS_QUERY = "genomic_regions"
GENE_FAMILIES_PATH = "/gene_family_linkouts"
GENE_FAMILIES_QUERY = "gene_families"
PAN_GENE_SETS_PATH = "/pan_gene_set_linkouts"
PAN_GENE_SETS_QUERY = "pan_gene_sets"
GWAS_PATH = "/gwas_linkouts"
GWAS_QUERY = "gwas"
QTL_STUDIES_PATH = "/qtl_study_linkouts"
QTL_STUDIES_QUERY = "qtl_studies"


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


async def http_gwas_get_handler(request):
    # parse the query from the request query string
    try:
        ids = request.rel_url.query[GWAS_QUERY]
    except KeyError:
        raise web.HTTPBadRequest(text="No " + GWAS_QUERY + " supplied")
    ids = ids.split(",")
    handler = request.app["handler"]
    linkouts = handler.process_gwas(ids)
    return web.json_response(linkouts)


async def http_gwas_post_handler(request):
    # parse the query from the request POST data
    data = await request.json()
    ids = data.get(GWAS_QUERY, [])
    if type(ids) != list:
        raise web.HTTPBadRequest(text=GWAS_QUERY + " must be given as list")
    if len(ids) == 0:
        raise web.HTTPBadRequest(text="No " + GWAS_QUERY + " supplied")

    handler = request.app["handler"]
    linkouts = handler.process_gwas(ids)
    return web.json_response(linkouts)


async def http_qtl_studies_get_handler(request):
    # parse the query from the request query string
    try:
        ids = request.rel_url.query[QTL_STUDIES_QUERY]
    except KeyError:
        raise web.HTTPBadRequest(text="No " + QTL_STUDIES_QUERY + " supplied")
    ids = ids.split(",")
    handler = request.app["handler"]
    linkouts = handler.process_qtl_studies(ids)
    return web.json_response(linkouts)


async def http_qtl_studies_post_handler(request):
    # parse the query from the request POST data
    data = await request.json()
    ids = data.get(QTL_STUDIES_QUERY, [])
    if type(ids) != list:
        raise web.HTTPBadRequest(text=QTL_STUDIES_QUERY + " must be given as list")
    if len(ids) == 0:
        raise web.HTTPBadRequest(text="No " + QTL_STUDIES_QUERY + " supplied")

    handler = request.app["handler"]
    linkouts = handler.process_qtl_studies(ids)
    return web.json_response(linkouts)


def run_http_server(host, port, handler):
    """Run the HTTP server with the given handler"""
    api_version = "v1"
    openapi_spec = f"{Path(__file__).parent.parent}/openapi/{api_version}/linkouts.yaml"
    spec = {}
    with open(openapi_spec, "r") as file:
        spec = yaml.safe_load(file)
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
    path_to_handler = {
        GENES_PATH: {
            'get': http_genes_get_handler,
            'post': http_genes_post_handler
        },
        GENOMIC_REGIONS_PATH: {
            'get': http_genomic_regions_get_handler,
            'post': http_genomic_regions_post_handler
        },
        GENE_FAMILIES_PATH: {
            'get': http_gene_families_get_handler,
            'post': http_gene_families_post_handler
        },
        PAN_GENE_SETS_PATH: {
            'get': http_pan_gene_sets_get_handler,
            'post': http_pan_gene_sets_post_handler
        },
        GWAS_PATH: {
            'get': http_gwas_get_handler,
            'post': http_gwas_post_handler
        },
        QTL_STUDIES_PATH: {
            'get': http_qtl_studies_get_handler,
            'post': http_qtl_studies_post_handler
        }
    }
    for path, methods in spec['paths'].items():
        for method, details in methods.items():
            if method == 'get':
                route = app.router.add_get(path, path_to_handler[path][method])
                cors.add(route)
            elif method == 'post':
                route = app.router.add_post(path, path_to_handler[path][method])
                cors.add(route)
    # run the app
    web.run_app(app)
    # TODO: what about teardown? runner.cleanup()
