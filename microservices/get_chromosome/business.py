import core.database as db
from core.utils import formatLocation, removePrefix


# chromosome - id of the chromosome you want to get
async def getChromosome(chromosome):
  r = db.getInterface()
  chromosome = 'chromosome:' + chromosome
  length = await r.hget(chromosome, 'length')
  if length is None:
    return None
  genes = await r.lrange(chromosome + ':genes', 0, -1)
  families = await r.lrange(chromosome + ':families', 0, -1)
  locations = await r.lrange(chromosome + ':locations', 0, -1)
  return {
    'length': int(length),
    'genes': list(map(lambda g: removePrefix('gene:', g), genes)),
    'families': list(map(lambda f: removePrefix('family:', f), families)),
    'locations': list(map(lambda l: formatLocation(l), locations))
  }
