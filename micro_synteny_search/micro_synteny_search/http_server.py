# dependencies
import aiohttp_cors
from aiohttp import web


async def http_post_handler(request):
    # parse the query from the POST data
    data = await request.json()
    query = data.get("query")
    matched = data.get("matched")
    intermediate = data.get("intermediate")
    handler = request.app["handler"]
    try:
        query, matched, intermediate = handler.parseArguments(
            query, matched, intermediate
        )
    except:
        return web.HTTPBadRequest(
            text="Required arguments are missing or have invalid values"
        )
    tracks = await handler.process(query, matched, intermediate)
    return web.json_response({"tracks": tracks})


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
