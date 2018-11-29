import aioredis
import functools


# the database driver
r = None


# sets up and takes down the database connection
async def db_engine(*args):
  global r
  r = await aioredis.create_redis('/run/redis/redis.sock', encoding='utf-8')
  yield
  r.close()
  await r.wait_closed()
  r = None


# a decorator that ensures that the database driver has been setup before the
# decorated function attempts to use it.
def requires_r(func):
  @functools.wraps(func)
  async def wrapper(*args, **kwargs):
    if r is None:
      raise NameError("Database driver undefined.")
    return await func(*args, **kwargs)
  return wrapper
