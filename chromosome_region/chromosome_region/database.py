# dependencies
import redis.asyncio as redis


async def connectToRedis(host='localhost', port=6379, db=0, password=None):
  # connect to database
  connection = await redis.Redis(host=host, port=port, db=db, password=password, decode_responses=True)
  # ping to force connection, preventing errors downstream
  await connection.ping()
  return connection
