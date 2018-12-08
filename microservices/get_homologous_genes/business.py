from core.utils import cleanGenes, formatGene
from itertools import chain


# chromosome - id of the chromosome you want to find genes on
# families - a list of gene family ids that you want to find all occurrences of on the chromosome
async def globalPlot(r, rpc, chromosome, families):
  families = list(map(lambda f: 'family:' + f, families))
  # get all genes of the query families
  params = {'families': families}
  family_gene_ids = await rpc.call('/family/get-family-genes', params)
  pipeline = r.pipeline()
  for gene_ids in family_gene_ids:
    for g in gene_ids:
      pipeline.hmget('gene:' + g, 'chromosome')
  genes = await pipeline.execute()
  # filter the genes not on the query chromosome
  chromosome_gene_ids = []
  for id, (c, ) in zip(chain(*family_gene_ids), genes):
    if c == 'chromosome:' + chromosome:
      chromosome_gene_ids.append('gene:' + id)
  # get the query chromosome's genes' information
  pipeline = r.pipeline()
  for g in chromosome_gene_ids:
    pipeline.hgetall(g)
  genes = await pipeline.execute()
  group_genes = list(map(lambda e: formatGene(*e), zip(chromosome_gene_ids, genes)))
  cleanGenes(group_genes)
  return group_genes
