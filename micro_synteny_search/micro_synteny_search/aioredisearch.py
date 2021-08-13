# Python
import time
# dependencies
import redisearch
import six


# copy of RediSearch's to_string function that's not exported
def to_string(s):
  if isinstance(s, six.string_types):
    return s
  elif isinstance(s, six.binary_type):
    return s.decode('utf-8')
  else:
    return s  # Not a string we care about


# a class that overrides a subset of the RediSearch Client methods to be
# asynchronous
class Client(redisearch.Client):

  async def load_document(self, id):
    fields = await self.redis.hgetall(id)
    if six.PY3:
      f2 = {to_string(k): to_string(v) for k, v in fields.items()}
      fields = f2
    try:
      del fields['id']
    except KeyError:
      pass
    return redisearch.Document(id=id, **fields)

  # unlike RediSearch get, this implementation returns a Document instance for
  # each id that exists in the database and None for those that don't
  async def get(self, *ids):
    flat_fields = await self.redis.execute_command('FT.MGET', self.index_name, *ids)
    docs = []
    for id, id_flat_fields in zip(ids, flat_fields):
      if id_flat_fields is None:
        docs.append(None)
      else:
        id_fields = dict(
          dict(zip(map(to_string, id_flat_fields[::2]),
                   map(to_string, id_flat_fields[1::2])))
        )
        doc = redisearch.Document(id, payload=None, **id_fields)
        docs.append(doc)
    return docs

  async def search(self, query):
    args, query = self._mk_query_args(query)
    st = time.time()
    res = await self.redis.execute_command(self.SEARCH_CMD, *args)
    return redisearch.Result(res,
                  not query._no_content,
                  duration=(time.time() - st) * 1000.0,
                  has_payload=query._with_payloads,
                  with_scores=query._with_scores)
