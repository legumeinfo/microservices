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
    except Exception:
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


async def http_post_by_chromosome_handler(request):
    # parse the chromosome name and parameters from the POST data
    data = await request.json()
    # required parameters
    chromosome_name = data.get("chromosomeName")
    matched = data.get("matched")
    intermediate = data.get("intermediate")
    # optional parameters
    mask = data.get("mask", None)
    targets = data.get("targets", None)
    metrics = data.get("optionalMetrics", None)
    chromosome_genes = data.get("chromosome_genes", None)
    chromosome_length = data.get("chromosome_length", None)
    handler = request.app["handler"]

    # Check if chromosome address is configured
    if handler.chromosome_address is None:
        return web.HTTPServiceUnavailable(
            text="ComputeByChromosome endpoint is not enabled. Chromosome address not configured."
        )

    try:
        (
            chromosome_name_list,
            matched,
            intermediate,
            mask,
            targets,
            metrics,
            chromosome_genes,
            chromosome_length,
        ) = handler.parseArguments(
            [chromosome_name],
            matched,
            intermediate,
            mask,
            targets,
            metrics,
            chromosome_genes,
            chromosome_length,
        )
        chromosome_name = chromosome_name_list[0]
    except Exception:
        return web.HTTPBadRequest(
            text="Required arguments are missing or have invalid values"
        )

    try:
        blocks = await handler.processWithChromosomeName(
            chromosome_name,
            matched,
            intermediate,
            mask,
            targets,
            metrics,
            chromosome_genes,
            chromosome_length,
            grpc_decode=True,
        )
    except ValueError as e:
        return web.HTTPBadRequest(text=str(e))

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
    # Add the new chromosome-based endpoint
    route_by_chromosome = app.router.add_post(
        "/by-chromosome", http_post_by_chromosome_handler
    )
    cors.add(route_by_chromosome)
    # run the app
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    # TODO: what about teardown? runner.cleanup()
