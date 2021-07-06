# dependencies
import aioredis


async def connectToRedis(host='localhost', port=6379, db=0, password=None):
  # connect to database
  connection = await aioredis.create_redis_pool((host, port), db=db, password=password, encoding='utf-8')
  # ping to force connection, preventing errors downstream
  await connection.ping()
  return connection
