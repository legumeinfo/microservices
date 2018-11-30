import core.database as db
from core.utils import cleanTrack, formatGene


# creates a track for the given gene by flanking it with neighbors on either
# side.
# gene - id of the gene at the center of the query context
# neighbors - the number of neighbors that should flank the query gene on either side
async def geneToTrack(gene, neighbors):
  r = db.getInterface()
  # fetch the data
  i, chromosome_id = await r.hmget('gene:' + gene, 'number', 'chromosome')
  if i is None or chromosome_id is None:
    return None
  chromosome = await r.hgetall(chromosome_id)
  genus, species = chromosome['organism'].split(':')[1:]
  length = await r.llen(chromosome_id + ':genes')
  start = max(0, int(i)-neighbors)
  stop = min(int(i)+neighbors, length-1)
  gene_ids = await r.lrange(chromosome_id + ':genes', start, stop)
  pipeline = r.pipeline()
  for g in gene_ids:
    pipeline.hgetall(g)
  genes = await pipeline.execute()
  # format and return
  track = {
    'genus': genus,
    'species': species,
    'species_id': chromosome['organism'],
    'chromosome_name': chromosome['name'],
    'chromosome_id': chromosome_id,
    'genes': list(map(lambda e: formatGene(*e), zip(gene_ids, genes)))
  }
  cleanTrack(track)
  return track


# creates a track for each given gene by flanking it with neighbors on either
# side.
# genes - list of gene ids
# neighbors - number of neighbors that should flank each gene
async def genesToTracks(genes, neighbors):
  families = set()
  tracks = {'groups': []}
  for g in genes:
    track = await geneToTrack(g, neighbors)
    if track is None:
      continue
    families.update(map(lambda g: g['family'], track['genes']))
    tracks['groups'].append(track)
  families.discard('')
  tracks['families'] = list(map(lambda f: {'id': f, 'name': f}, families))
  return tracks
