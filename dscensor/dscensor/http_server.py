from pathlib import Path

# dependencies
from aiohttp import web
from rororo import OperationTableDef, openapi_context, setup_openapi

operations = OperationTableDef()


@operations.register("getGenus")
async def list_genus(request):
    handler = request.app["handler"]
    genus_list = handler.list_genus()
    return web.json_response(genus_list)


@operations.register("getSpecies")
async def list_species(request):
    handler = request.app["handler"]
    species_list = handler.list_species()
    return web.json_response(species_list)


@operations.register("getGenomes")
async def list_genomes(request):
    handler = request.app["handler"]
    with openapi_context(request) as context:
        genus = context.parameters.query.get("genus", "").lower()
        species = context.parameters.query.get("species", "").lower()
    genomes_list = handler.list_genomes(genus, species)
    return web.json_response(genomes_list)


@operations.register("getGeneModelsMain")
async def list_gene_models(request):
    handler = request.app["handler"]
    with openapi_context(request) as context:
        genus = context.parameters.query.get("genus")
        species = context.parameters.query.get("species")
    gene_model_list = handler.list_gene_models(genus, species)
    return web.json_response(gene_model_list)


async def run_http_server(host, port, handler):
    # make the app
    app = web.Application()
    app["handler"] = handler
    # finish setting up the app using OpenAPI
    parent = Path(__file__).parent.parent
    api_path = f"{parent}/openapi/dscensor/v1/dscensor.yaml"
    setup_openapi(
        app,
        api_path,
        operations,
        is_validate_response=False,
        cors_middleware_kwargs={"allow_all": True},
    )
    # run the app
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    # TODO: what about teardown? runner.cleanup()
