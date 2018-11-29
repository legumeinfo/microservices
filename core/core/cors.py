import aiohttp_cors


# Configure default CORS settings.
def corsFactory(app):
  return aiohttp_cors.setup(app, defaults={
      '*': aiohttp_cors.ResourceOptions(
             allow_credentials=True,
             expose_headers='*',
             allow_headers='*',
           )
    })
