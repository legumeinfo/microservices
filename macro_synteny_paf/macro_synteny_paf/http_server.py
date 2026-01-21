# dependencies
import aiohttp_cors
from aiohttp import web
import json


async def http_get_handler(request):
    # parse the query from the URL query string parameters
    genome_1 = request.rel_url.query.get("genome1", "")
    genome_2 = request.rel_url.query.get("genome2", "")
    matched = request.rel_url.query.get("matched", "")
    intermediate = request.rel_url.query.get("intermediate", "")
    # optional parameters
    mask = request.rel_url.query.get("mask", None)
    format_type = request.rel_url.query.get("format", "json")  # default to json
    metrics_param = request.rel_url.query.get("metrics", None)
    metrics = metrics_param.split(",") if metrics_param else None
    identity = request.rel_url.query.get("identity", None)
    anchors = request.rel_url.query.get("anchors", None)
    chromosome_genes = None #data.get("chromosome_genes", None)
    chromosome_length = None #data.get("chromosome_length", None)
    handler = request.app["handler"]

    if format_type not in ["json", "paf"]:
        return web.HTTPBadRequest(
            text="Invalid format parameter. Must be 'json' or 'paf'."
        )

    try:
        (
            genome_1,
            genome_2,
            matched,
            intermediate,
            mask,
            metrics,
            chromosome_genes,
            chromosome_length,
            identity,
            anchors,
        ) = handler.parseArguments(
            genome_1,
            genome_2,
            matched,
            intermediate,
            mask,
            metrics,
            chromosome_genes,
            chromosome_length,
            identity,
            anchors,
        )
    except Exception:
        return web.HTTPBadRequest(
            text="Required arguments are missing or have invalid values"
        )

    result = await handler.process(
        genome_1,
        genome_2,
        matched,
        intermediate,
        mask,
        metrics,
        chromosome_genes,
        chromosome_length,
        identity,
        anchors,
        grpc_decode=True,
        output_format=format_type,
    )

    if format_type == "json":
        return web.Response(
            text=json.dumps(result, indent=2),
            content_type='application/json'
        )
    else:
        return web.Response(
            text=result,
            content_type='text/plain'
        )


async def run_http_server(host, port, handler):
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
    route = app.router.add_get("/", http_get_handler)
    cors.add(route)
    # run the app
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    # TODO: what about teardown? runner.cleanup()
