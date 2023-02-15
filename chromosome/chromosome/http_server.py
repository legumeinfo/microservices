# dependencies
import aiohttp_cors
from aiohttp import web


async def http_get_handler(request):
    # parse the query from the URL query string parameters
    name = request.rel_url.query.get("chromosome", "")
    handler = request.app["handler"]
    chromosome = await handler.process(name)
    if chromosome is None:
        return web.HTTPNotFound(text="Chromosome not found")
    return web.json_response({"chromosome": chromosome})


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
