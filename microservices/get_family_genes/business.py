from core.utils import removePrefix

# families - a set of family ids to retrieve gene identifiers for
async def getFamilyGenes(r, families):
  pipeline = r.pipeline()
  for f in set(families):
    pipeline.smembers(f)
  family_gene_ids = []
  for gene_ids in await pipeline.execute():
    genes = list(map(lambda g: removePrefix('gene:', g), gene_ids))
    family_gene_ids.append(genes)
  return family_gene_ids
