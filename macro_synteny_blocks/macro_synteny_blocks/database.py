# dependencies
import redis.asyncio as redis
# module
import macro_synteny_blocks


COMPATIBLE_KEY = 'GCV_COMPATIBLE_SCHEMA_VERSIONS'


class SchemaVersionError(Exception):
  '''
  The exception to raise when the GCV database schema doesn't support the schema
  required by the service.
  '''
  pass


async def connectToRedis(host='localhost', port=6379, db=0, password=None):
  # connect to database
  connection = await redis.Redis(host=host, port=port, db=db, password=password, decode_responses=True)
  # ping to force connection, preventing errors downstream
  await connection.ping()
  # check that the database is loaded with a compatible schema version
  if not await connection.sismember(COMPATIBLE_KEY, macro_synteny_blocks.__schema_version__):
    message = ('The Redis database does not support the required GCV schema '
               f'version: {macro_synteny_blocks.__schema_version__}')
    raise SchemaVersionError(message)
  return connection
