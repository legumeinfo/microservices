import os
import logging
import environ
from pathlib import Path
from typing import Union
# dependencies
from aiohttp import web
from rororo import OperationTableDef, openapi_context, setup_openapi, setup_settings, BaseSettings
from dscensor.directed_graph import DirectedGraphController

operations = OperationTableDef()


@environ.config(prefix=None, frozen=True)
class Settings(BaseSettings):
    input_nodes: str = environ.var(name="DSCENSOR_INPUT_NODES", default="./autocontent")


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


def run_http_server(host, port, handler, settings: Union[Settings, None] = None):
    # make the app
    if settings is None:
        settings = Settings.from_environ()
    app = setup_settings(
        web.Application(),
        settings,
        loggers=("aiohttp", "aiohttp_middlewares", "dscensor", "rororo"),
        remove_root_handlers=True,
    )
    nodes = os.getenv("DSCENSOR_NODES")
    if not nodes:
        nodes = "./autocontent"
    app["handler"] = handler
    app["digraph"] = DirectedGraphController(nodes)
    # finish setting up the app using OpenAPI
    parent = Path(__file__).parent.parent
    api_path = f"{parent}/openapi/dscensor/v1/dscensor.yaml"
    return setup_openapi(
        app,
        api_path,
        operations,
        is_validate_response=False,
        cors_middleware_kwargs={"allow_all": True},
    )
    # run the app


#    runner = web.AppRunner()
#    await runner.setup()
#    site = web.TCPSite(runner, host, port)
#    await site.start()
#    web.run_app(setup_openapi, port=port, host=host)
# TODO: what about teardown? runner.cleanup()
