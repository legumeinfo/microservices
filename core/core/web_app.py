import aiohttp_cors
import aioredis
from aiohttp import web
from functools import partial
# local
from core.message_queue import RPC


class WebApp(object):

  async def redis_engine(self, app):
    app['r_engine'] = await aioredis.create_redis(
      '/run/redis/redis.sock',
      encoding='utf-8',
      loop=app.loop
    )
    yield
    app['r_engine'].close()
    await app['r_engine'].wait_closed()

  async def rabbitmq_engine(self, routes, app):
    app['rpc'] = RPC(app.loop)
    await app['rpc'].connect()
    # consume the route queues
    for method, path, handler, webHandler in routes:
      await app['rpc'].consume_queue(path, partial(handler, app))
    yield
    await app['rpc'].close()

  def __init__(self, routes):
    self.app = web.Application()
    self.cors = aiohttp_cors.setup(self.app, defaults={
      '*': aiohttp_cors.ResourceOptions(
             allow_credentials=True,
             expose_headers='*',
             allow_headers='*',
           )
    })
    for method, path, handler, webHandler in routes:
      route = self.app.router.add_route(method, path, webHandler)
      self.cors.add(route)
    self.app.cleanup_ctx.append(self.redis_engine)
    self.app.cleanup_ctx.append(partial(self.rabbitmq_engine, routes))

  def run(self, port=1234):
    web.run_app(self.app, port=port)
