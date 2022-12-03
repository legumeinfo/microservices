# Python
import time
# dependencies
from redis.asyncio.client import Pipeline as AsyncPipeline
from redis.client import Pipeline
from redis.commands.search import AsyncSearch
from redis.commands.search.commands import SEARCH_CMD
from redis.commands.search.result import Result


# a class that overrides a subset of the RediSearch Client methods to be
# asynchronous
class CustomAsyncSearch(AsyncSearch):

  # a copy of the RediSearch search command's inline Result instantiation so we
  # can process results from searches made with a Redis Pipeline
  def search_result(self, query, res, st=time.time()):
    return Result(res,
                  not query._no_content,
                  duration=(time.time() - st) * 1000.0,
                  has_payload=query._with_payloads,
                  with_scores=query._with_scores)

  # a copy of the RediSearch search command that checks for the async pipeline;
  # I've opened an issue in the redis-py repo since this is a bug:
  # https://github.com/redis/redis-py/issues/2279
  async def search(self, query, query_params=None):
    args, query = self._mk_query_args(query, query_params=query_params)
    st = time.time()
    res = self.execute_command(SEARCH_CMD, *args)

    if isinstance(res, Pipeline) or isinstance(res, AsyncPipeline):
        return res
    return self.search_result(query, res, st)
