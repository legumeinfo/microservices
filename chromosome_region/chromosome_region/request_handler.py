# Python
import asyncio
import bisect

# dependencies
from redis.commands.search import AsyncSearch


class RequestHandler:
    def __init__(self, redis_connection):
        self.redis_connection = redis_connection

    async def _getRedisIntList(self, key):
        key_list = await self.redis_connection.lrange(key, 0, -1)
        return list(map(int, key_list))

    async def process(self, chromosome, start, stop):
        # connect to the index
        chromosome_index = AsyncSearch(
            self.redis_connection, index_name="chromosomeIdx"
        )
        # get the chromosome
        chromosome_doc_id = f"chromosome:{chromosome}"
        chromosome_doc = await chromosome_index.load_document(chromosome_doc_id)
        if not hasattr(chromosome_doc, "name"):
            return None
        # get the chromosome gene locations
        fmins, fmaxs = await asyncio.gather(
            self._getRedisIntList(f"{chromosome_doc_id}:fmins"),
            self._getRedisIntList(f"{chromosome_doc_id}:fmaxs"),
        )
        # find the index bounds using binary search
        i = bisect.bisect_left(fmins, start)
        j = bisect.bisect_right(fmaxs, stop)
        # compute the number of flanking genes and retrieve only the center gene
        neighbors = j - i
        center = (i + j) // 2
        gene = await self.redis_connection.lindex(f"{chromosome_doc_id}:genes", center)
        return {"gene": gene, "neighbors": neighbors}
