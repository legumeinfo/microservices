import aiohttp_cors
import core.database as db
from aiohttp import web


class WebApp(object):

  def __init__(self, routes):
    self.app = web.Application()
    self.app.cleanup_ctx.append(db.db_engine)
    self.cors = aiohttp_cors.setup(self.app, defaults={
      '*': aiohttp_cors.ResourceOptions(
             allow_credentials=True,
             expose_headers='*',
             allow_headers='*',
           )
    })
    for method, path, handler in routes:
      route = self.app.router.add_route(method, path, handler)
      self.cors.add(route)

  def run(self):
    web.run_app(self.app, port=1234)
