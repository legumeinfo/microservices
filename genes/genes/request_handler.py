# dependencies
from redis.commands.search import AsyncSearch
from redis.commands.search.document import Document
from redis.commands.search._util import to_string


class RequestHandler:
    def __init__(self, redis_connection):
        self.redis_connection = redis_connection

    # decorate RediSearch get to return a Document instance for each id that
    # exists in the index and None for those that don't, instead of raw contents
    async def _get(self, index, *ids):
        flat_fields = await index.get(*ids)
        docs = []
        for id, id_flat_fields in zip(ids, flat_fields):
            if id_flat_fields is None:
                docs.append(None)
            else:
                id_fields = dict(
                    dict(
                        zip(
                            map(to_string, id_flat_fields[::2]),
                            map(to_string, id_flat_fields[1::2]),
                        )
                    )
                )
                doc = Document(id, payload=None, **id_fields)
                docs.append(doc)
        return docs

    def _geneDocToDict(self, gene_doc):
        return {
            "name": gene_doc.name,
            "chromosome": gene_doc.chromosome,
            "family": gene_doc.family or "",
            "fmin": int(gene_doc.fmin),
            "fmax": int(gene_doc.fmax),
            "strand": int(gene_doc.strand),
        }

    async def process(self, names):
        # connect to the index
        gene_index = AsyncSearch(self.redis_connection, index_name="geneIdx")
        # get the genes from the index
        gene_ids = map(lambda name: f"gene:{name}", names)
        docs = await self._get(gene_index, *gene_ids)
        genes = list(map(self._geneDocToDict, filter(lambda d: d is not None, docs)))
        return genes
