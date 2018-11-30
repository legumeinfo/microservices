import aioredis
import functools


# the database interface
r = None


# make the interface effectively a singleton to other modules
def getInterface():
  return r


# sets up and takes down the database connection
async def db_engine(*args):
  global r
  r = await aioredis.create_redis('/run/redis/redis.sock', encoding='utf-8')
  yield
  r.close()
  await r.wait_closed()
  r = None
