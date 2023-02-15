# dependencies
from redis.commands.search import AsyncSearch
from redis.commands.search.query import Query


class RequestHandler:
    def __init__(
        self, redis_connection, breakpoint_characters=",.<>{}[]\"':;!@#$%^&*()-+=~"
    ):
        self.redis_connection = redis_connection
        self.breakpoint_characters = set(breakpoint_characters)

    async def process(self, name):
        # connect to the index
        gene_index = AsyncSearch(self.redis_connection, index_name="geneIdx")
        # replace RediSearch breakpoint characters with spaces
        cleaned_name = ""
        for c in name:
            if c in self.breakpoint_characters:
                cleaned_name += " "
            else:
                cleaned_name += c
        # search the gene index
        query = Query(cleaned_name).limit_fields("name").return_fields("name")
        result = await gene_index.search(query)
        genes = list(map(lambda d: d.name, result.docs))
        return genes
