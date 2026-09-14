"""HTTP server for the dscensor API"""

from __future__ import annotations

from typing import Any, Optional

import aiohttp_cors
from aiohttp import web

routes = web.RouteTableDef()


def _parse_results_param(request: web.Request) -> Optional[int]:
    """Extract and validate the optional ``results`` path parameter.

    :param request: The incoming aiohttp request.
    :return: The parsed integer, or ``None`` if the route has no ``results``.
    :raises aiohttp.web.HTTPBadRequest: If ``results`` is present but is not
        a positive integer.
    """
    raw = request.match_info.get("results")
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
    return web.json_response(handler.list_genus())


@routes.get("/species")
@routes.get("/genera/{genus}/species")
async def list_species(request: web.Request) -> web.Response:
    """Return the list of species, optionally limited to one genus.

    :param request: The incoming aiohttp request. An optional ``genus``
        path parameter narrows the result set.
    :return: A JSON response containing the species list.
    """
    handler = request.app["handler"]
    genus = request.match_info.get("genus", "")
    return web.json_response(handler.list_species(genus))


@routes.get("/genomes")
@routes.get("/genomes/limit/{results}")
@routes.get("/genomes/{genus}")
@routes.get("/genomes/{genus}/limit/{results}")
@routes.get("/genomes/{genus}/{species}")
@routes.get("/genomes/{genus}/{species}/limit/{results}")
async def list_genomes(request: web.Request) -> web.Response:
    """Return genome_main objects filtered by path parameters.

    :param request: The incoming aiohttp request. Optional ``genus``,
        ``species`` and ``results`` path parameters narrow the result set.
    :return: A JSON response containing the genome list.
    """
    handler = request.app["handler"]
    genus = request.match_info.get("genus", "")
    species = request.match_info.get("species", "")
    results = _parse_results_param(request)
    return web.json_response(handler.list_genomes(genus, species, results))


@routes.get("/annotations")
@routes.get("/annotations/limit/{results}")
@routes.get("/annotations/{genus}")
@routes.get("/annotations/{genus}/limit/{results}")
@routes.get("/annotations/{genus}/{species}")
@routes.get("/annotations/{genus}/{species}/limit/{results}")
async def list_gene_models(request: web.Request) -> web.Response:
    """Return gene_models_main objects filtered by path parameters.

    :param request: The incoming aiohttp request. Optional ``genus``,
        ``species`` and ``results`` path parameters narrow the result set.
    :return: A JSON response containing the gene model list.
    """
    handler = request.app["handler"]
    genus = request.match_info.get("genus", "")
    species = request.match_info.get("species", "")
    results = _parse_results_param(request)
    return web.json_response(handler.list_gene_models(genus, species, results))


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
