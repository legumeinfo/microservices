"""HTTP server for the dscensor API"""

from __future__ import annotations

from typing import Any, Optional

import aiohttp_cors
from aiohttp import web

routes = web.RouteTableDef()


def _parse_results_param(request: web.Request) -> Optional[int]:
    """Extract and validate the optional ``results`` query parameter.

    :param request: The incoming aiohttp request.
    :return: The parsed integer, or ``None`` if the parameter is absent.
    :raises aiohttp.web.HTTPBadRequest: If ``results`` is present but is not
        a positive integer.
    """
    raw = request.query.get("results")
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise web.HTTPBadRequest(reason="'results' must be an integer") from exc
    if value < 1:
        raise web.HTTPBadRequest(reason="'results' must be >= 1")
    return value


@routes.get("/genera")
async def list_genus(request: web.Request) -> web.Response:
    """Return the list of available genera.

    :param request: The incoming aiohttp request.
    :return: A JSON response containing the genus list.
    """
    handler = request.app["handler"]
    genus_list = handler.list_genus()
    return web.json_response(genus_list)


@routes.get("/species")
async def list_species(request: web.Request) -> web.Response:
    """Return the list of available species.

    :param request: The incoming aiohttp request.
    :return: A JSON response containing the species list.
    """
    handler = request.app["handler"]
    species_list = handler.list_species()
    return web.json_response(species_list)


@routes.get("/genomes")
async def list_genomes(request: web.Request) -> web.Response:
    """Return genome_main objects filtered by genus/species query parameters.

    :param request: The incoming aiohttp request. Optional ``genus`` and
        ``species`` query parameters narrow the result set. An optional
        ``results`` query parameter is validated but not yet forwarded to
        the handler (see module docstring note).
    :return: A JSON response containing the genome list.
    """
    handler = request.app["handler"]
    genus = request.query.get("genus", "").lower()
    species = request.query.get("species", "").lower()
    _parse_results_param(request)  # validate against openAPI spec
    genomes_list = handler.list_genomes(genus, species)
    return web.json_response(genomes_list)


@routes.get("/annotations")
async def list_gene_models(request: web.Request) -> web.Response:
    """Return gene_models_main objects filtered by genus/species.

    :param request: The incoming aiohttp request. Optional ``genus`` and
        ``species`` query parameters narrow the result set. An optional
        ``results`` query parameter is validated but not yet forwarded to
        the handler (see module docstring note).
    :return: A JSON response containing the gene model list.
    """
    handler = request.app["handler"]
    genus = request.query.get("genus")
    species = request.query.get("species")
    _parse_results_param(request)  # spec validation
    gene_model_list = handler.list_gene_models(genus, species)
    return web.json_response(gene_model_list)


# --- catalog endpoints -------------------------------------------------------
# These answer whole-store questions ("what exists, how does it relate") that the
# per-object node endpoints above cannot. Each response carries the catalog's
# build provenance so a client can see how fresh the answer is.


def _catalog_or_503(request: web.Request):
    """Return the loaded catalog, or raise 503 explaining that none is configured."""
    catalog = request.app["handler"].catalog
    if not catalog.loaded:
        raise web.HTTPServiceUnavailable(
            reason="No catalog loaded; start dscensor with --catalog /path/to/catalog.json"
        )
    return catalog


def _envelope(catalog, payload: dict) -> web.Response:
    """Wrap a result with the catalog build stamp."""
    body = {"catalog": catalog.provenance()}
    body.update(payload)
    return web.json_response(body)


@routes.get("/meta")
async def catalog_meta(request: web.Request) -> web.Response:
    """Report whether a catalog is loaded, and how stale it is.

    :param request: The incoming aiohttp request.
    :return: A JSON response with schema version, build time and source commit.
    """
    catalog = request.app["handler"].catalog
    return web.json_response(catalog.provenance())


@routes.get("/catalog")
async def catalog_document(request: web.Request) -> web.Response:
    """Return the whole catalog document.

    Intended for clients that hold the catalog in memory themselves rather than
    querying endpoint by endpoint.

    :param request: The incoming aiohttp request.
    :return: The complete catalog as JSON.
    """
    catalog = _catalog_or_503(request)
    return web.json_response(catalog.document)


@routes.get("/collections")
async def list_collections(request: web.Request) -> web.Response:
    """Return catalog collections filtered by genus, species, type and flags.

    :param request: The incoming aiohttp request. Optional ``genus``,
        ``species``, ``type``, ``has_doi`` and ``indexed`` query parameters
        narrow the result set.
    :return: A JSON response containing the matching collections.
    """
    catalog = _catalog_or_503(request)
    collections = catalog.list_collections(
        genus=request.query.get("genus", ""),
        species=request.query.get("species", ""),
        collection_type=request.query.get("type", ""),
        has_doi=request.query.get("has_doi") in ("1", "true", "yes"),
        indexed_only=request.query.get("indexed") in ("1", "true", "yes"),
    )
    return _envelope(catalog, {"count": len(collections), "collections": collections})


@routes.get("/types")
async def list_types(request: web.Request) -> web.Response:
    """Return the collection types available, with counts.

    :param request: The incoming aiohttp request. Optional ``genus`` and
        ``species`` query parameters narrow the scope.
    :return: A JSON response mapping collection type to count.
    """
    catalog = _catalog_or_503(request)
    return _envelope(
        catalog,
        {
            "types": catalog.list_types(
                genus=request.query.get("genus", ""),
                species=request.query.get("species", ""),
            )
        },
    )


@routes.get("/species-with")
async def species_with(request: web.Request) -> web.Response:
    """Return species holding a collection of every requested type.

    :param request: The incoming aiohttp request. Repeat or comma-separate the
        ``type`` parameter, e.g. ``?type=diversity&type=expression``.
    :return: A JSON response listing the matching species.
    """
    catalog = _catalog_or_503(request)
    raw = request.query.getall("type", [])
    types = [t for value in raw for t in value.split(",") if t]
    if not types:
        raise web.HTTPBadRequest(reason="at least one 'type' parameter is required")
    matches = catalog.species_with(types)
    return _envelope(
        catalog, {"types": types, "count": len(matches), "species": matches}
    )


@routes.get("/assemblies")
async def rank_assemblies(request: web.Request) -> web.Response:
    """Return genome collections ranked by assembly quality, best first.

    :param request: The incoming aiohttp request. Optional ``genus`` and
        ``species`` query parameters narrow the scope.
    :return: A JSON response of assemblies ordered by BUSCO completeness, then
        contig N50.
    """
    catalog = _catalog_or_503(request)
    rows = catalog.rank_assemblies(
        genus=request.query.get("genus", ""),
        species=request.query.get("species", ""),
    )
    # `ranked` tells the caller whether the order means anything. It is False while
    # assembly metrics are deferred; see the NOTE in dscensor/catalog.py.
    return _envelope(
        catalog,
        {
            "count": len(rows),
            "ranked": catalog.assemblies_are_ranked(),
            "assemblies": rows,
        },
    )


@routes.get("/lineage/{identifier}")
async def lineage(request: web.Request) -> web.Response:
    """Return a collection's ancestry and every publication it depends on.

    :param request: The incoming aiohttp request; ``identifier`` is a collection
        id such as ``Wm82.gnm4.ann1.T8TQ``.
    :return: A JSON response with the derived_from chain and its DOIs.
    """
    catalog = _catalog_or_503(request)
    result = catalog.lineage(request.match_info["identifier"])
    if not result["found"]:
        raise web.HTTPNotFound(
            reason=f"no collection with id {request.match_info['identifier']}"
        )
    return _envelope(catalog, result)


@routes.get("/indexed-files")
async def indexed_files(request: web.Request) -> web.Response:
    """Return files that can be range-read over HTTP, with their index types.

    The datastore's directory index omits ``.fai``/``.tbi`` siblings, so this
    listing cannot be reproduced by crawling the store.

    :param request: The incoming aiohttp request. Optional ``genus``,
        ``species`` and ``type`` query parameters narrow the scope.
    :return: A JSON response of collections and their randomly accessible files.
    """
    catalog = _catalog_or_503(request)
    rows = catalog.indexed_files(
        genus=request.query.get("genus", ""),
        species=request.query.get("species", ""),
        collection_type=request.query.get("type", ""),
    )
    return _envelope(catalog, {"count": len(rows), "collections": rows})


def _setup_cors(app: web.Application) -> None:
    """Attach permissive CORS to every registered route.

    :param app: The application whose routes should get CORS headers.
    """
    cors = aiohttp_cors.setup(
        app,
        defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=False,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*",
            )
        },
    )
    for route in list(app.router.routes()):
        cors.add(route)


async def run_http_server(host: str, port: int, handler: Any) -> web.AppRunner:
    """Configure and start the aiohttp HTTP server.

    :param host: Host/interface to bind to.
    :param port: Port to bind to.
    :param handler: The application's data-access handler, stashed on
        ``app["handler"]`` for the route handlers to use.
    :return: The running :class:`~aiohttp.web.AppRunner`. Callers are
        responsible for eventually calling ``await runner.cleanup()``
    """
    app = web.Application()
    app.add_routes(routes)
    app["handler"] = handler
    _setup_cors(app)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    return runner
