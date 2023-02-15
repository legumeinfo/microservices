# dependencies
import aiohttp_cors
from aiohttp import web


async def http_post_handler(request):
    # parse the chromosome and parameters from the POST data
    data = await request.json()
    # required parameters
    chromosome = data.get("chromosome")
    matched = data.get("matched")
    intermediate = data.get("intermediate")
    # optional parameters
    mask = data.get("mask", None)
    targets = data.get("targets", None)
    metrics = data.get("optionalMetrics", None)
    chromosome_genes = data.get("chromosome_genes", None)
    chromosome_length = data.get("chromosome_length", None)
    handler = request.app["handler"]
    try:
        (
            chromosome,
            matched,
            intermediate,
            mask,
            targets,
            metrics,
            chromosome_genes,
            chromosome_length,
        ) = handler.parseArguments(
            chromosome,
            matched,
            intermediate,
            mask,
            targets,
            metrics,
            chromosome_genes,
            chromosome_length,
        )
    except:
        return web.HTTPBadRequest(
            text="Required arguments are missing or have invalid values"
        )
    blocks = await handler.process(
        chromosome,
        matched,
        intermediate,
        mask,
        targets,
        metrics,
        chromosome_genes,
        chromosome_length,
        grpc_decode=True,
    )
    json = web.json_response({"blocks": blocks})
    return json


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
    route = app.router.add_post("/", http_post_handler)
    cors.add(route)
    # run the app
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    # TODO: what about teardown? runner.cleanup()
