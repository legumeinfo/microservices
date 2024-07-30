# dependencies
import aiohttp_cors
from aiohttp import web


async def http_get_handler(request):
    # parse the query from the URL query string parameters
    genome_1 = request.rel_url.query.get("genome1", "")
    chr_prefix_1 = request.rel_url.query.get("chrpfx1", "")
    chr_digits_1 = request.rel_url.query.get("chrdgt1", "")
    n_chr_1 = request.rel_url.query.get("nchr1", "")
    genome_2 = request.rel_url.query.get("genome2", "")
    chr_prefix_2 = request.rel_url.query.get("chrpfx2", "")
    chr_digits_2 = request.rel_url.query.get("chrdgt2", "")
    n_chr_2 = request.rel_url.query.get("nchr2", "")
    matched = request.rel_url.query.get("matched", "")
    intermediate = request.rel_url.query.get("intermediate", "")
    # optional parameters
    mask = request.rel_url.query.get("mask", None)
    metrics = None #data.get("optionalMetrics", None)
    chromosome_genes = None #data.get("chromosome_genes", None)
    chromosome_length = None #data.get("chromosome_length", None)
    handler = request.app["handler"]
    try:
        (
            genome_1_chrs,
            genome_2_chrs,
            matched,
            intermediate,
            mask,
            metrics,
            chromosome_genes,
            chromosome_length,
        ) = handler.parseArguments(
            genome_1,
            chr_prefix_1,
            chr_digits_1,
            n_chr_1,
            genome_2,
            chr_prefix_2,
            chr_digits_2,
            n_chr_2,
            matched,
            intermediate,
            mask,
            metrics,
            chromosome_genes,
            chromosome_length,
        )
    except Exception:
        return web.HTTPBadRequest(
            text="Required arguments are missing or have invalid values"
        )
    paf_rows = await handler.process(
        genome_1_chrs,
        genome_2_chrs,
        matched,
        intermediate,
        mask,
        metrics,
        chromosome_genes,
        chromosome_length,
        grpc_decode=True,
    )
    paf = web.Response(text = paf_rows, content_type = 'text/html')
    return paf


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
