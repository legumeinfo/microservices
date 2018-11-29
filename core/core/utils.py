# takes a gene from the db and an id and formats in the manner expected by the
# API user.
# id - a gene id
# g - the gene corresponding to the id
def formatGene(id, g):
  return {
    'name': g['name'],
    'id': id,
    'fmin': g['begin'],
    'fmax': g['end'],
    'strand': -1 if g['orientation'] == '-' else 1,
    'family': g['family']
  }


def splitLocation(l):
  fmin, fmax = l.split(":")
  return int(fmin), int(fmax)


def formatLocation(l):
  fmin, fmax = splitLocation(l)
  return {'fmin': fmin, 'fmax': fmax}


def removePrefix(prefix, string):
  return string[len(prefix):]


def removeSuffix(suffix, string):
  return string[:-len(suffix)]


def cleanGenes(genes):
  for g in genes:
    g['id'] = removePrefix('gene:', g['id'])
    g['family'] = removePrefix('family:', g['family'])


def cleanTrack(track):
  track['chromosome_id'] = removePrefix('chromosome:', track['chromosome_id'])
  cleanGenes(track['genes'])


def cleanMacro():
  pass
