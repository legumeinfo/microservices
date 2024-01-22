import logging

from aiohttp import web
from rororo import openapi_context, OperationTableDef

# from rororo import OperationTableDef, openapi_context
# from rororo.openapi import get_validated_data, get_validated_parameters

logger = logging.getLogger(__name__)

# ``OperationTableDef`` is analogue of ``web.RouteTableDef`` but for OpenAPI
# operation handlers
operations = OperationTableDef()


@operations.register("getGenus")
async def list_genus(request: web.Request) -> web.Response:
    genus_list = {}
    for node in list(request.app["digraph"].digraph.nodes(data=True)):
        genus_list[
            node[1]["metadata"]["genus"]
        ] = 1  # data part of node tuple with genus key
    return web.json_response([genus for genus in genus_list])


@operations.register("getSpecies")
async def list_species(request: web.Request) -> web.Response:
    species_list = {}
    for node in list(request.app["digraph"].digraph.nodes(data=True)):
        species_list[
            node[1]["metadata"]["species"]
        ] = 1  # data part of node tuple with species key
    return web.json_response([species for species in species_list])


@operations.register("getGenomes")
async def list_genomes(request: web.Request) -> web.Response:
    with openapi_context(request) as context:
        genomes_main = {}
        genus = context.parameters.query.get("genus", "").lower()
        species = context.parameters.query.get("species", "").lower()
        for node in list(request.app["digraph"].digraph.nodes(data=True)):
            node_genus = node[1]["metadata"]["genus"].lower()
            node_species = node[1]["metadata"]["species"].lower()
            node_canonical_type = node[1]["metadata"]["canonical_type"]
            if node_canonical_type != "genome_main":
                continue
            if genus:  # if genus provided only take matching genus
                if node_genus != genus:
                    continue
                if species:  # if genus and species make sure species within genus
                    if node_species != species:
                        continue
            if species:  # lets you specify species without genus which is probably stupid
                if node_species != species:
                    continue
            genomes_main[node[0]] = node[1]
        return web.json_response([genomes_main[genome] for genome in genomes_main])


@operations.register("getGeneModelsMain")
async def list_gene_models(request: web.Request) -> web.Response:
    with openapi_context(request) as context:
        gene_models_main = {}
        genus = context.parameters.query.get("genus")
        species = context.parameters.query.get("species")
        for node in list(request.app["digraph"].digraph.nodes(data=True)):
            node_genus = node[1]["metadata"]["genus"].lower()
            node_species = node[1]["metadata"]["species"].lower()
            node_canonical_type = node[1]["metadata"]["canonical_type"]
            if node_canonical_type != "gene_models_main":
                continue
            if genus:  # if genus provided only take matching genus
                if node_genus != genus:
                    continue
                if species:  # if genus and species make sure species within genus
                    if node_species != species:
                        continue
            if species:  # lets you specify species without genus which is probably stupid
                if node_species != species:
                    continue
            gene_models_main[node[0]] = node[1]
        return web.json_response([gene_models_main[genome] for genome in gene_models_main])
