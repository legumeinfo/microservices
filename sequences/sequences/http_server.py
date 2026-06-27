import aiohttp_cors
from aiohttp import web

from sequences.request_handler import RequestError


async def _respond(handler, yucks, seq_type, upstream, downstream):
    try:
        fasta = await handler.process(yucks, seq_type, upstream, downstream)
    except RequestError as e:
        return web.json_response(
            {"error": e.message, "status": e.status}, status=e.status
        )
    return web.Response(
        text=fasta,
        content_type="text/x-fasta",
        headers={"Content-Disposition": 'attachment; filename="sequences.fasta"'},
    )


async def http_index(request):
    return web.Response(text="sequences")


async def http_seq_get(request):
    handler = request.app["handler"]
    raw = request.match_info.get("yucks", "")
    yucks = [y for y in raw.split(",") if y]
    seq_type = request.query.get("type", "protein")
    # up/down are coerced + clamped downstream by fasta.clamp_flank, so the raw
    # query strings (or None when absent) can be passed straight through.
    upstream = request.query.get("up")
    downstream = request.query.get("down")
    return await _respond(handler, yucks, seq_type, upstream, downstream)


async def http_seq_post(request):
    handler = request.app["handler"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response(
            {"error": "Request body must be JSON.", "status": 400}, status=400
        )
    yucks = data.get("yucks", [])
    if not isinstance(yucks, list):
        return web.json_response(
            {"error": '"yucks" must be a list.', "status": 400}, status=400
        )
    seq_type = data.get("type", "protein")
    upstream = data.get("up")
    downstream = data.get("down")
    return await _respond(handler, yucks, seq_type, upstream, downstream)


async def run_http_server(host, port, handler):
    # make the app
    app = web.Application()
    app["handler"] = handler
    # define the routes and enable CORS
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
    cors.add(app.router.add_get("/", http_index))
    cors.add(app.router.add_get("/seq/{yucks}", http_seq_get))
    cors.add(app.router.add_post("/seq", http_seq_post))
    # run the app
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    # TODO: what about teardown? runner.cleanup()
