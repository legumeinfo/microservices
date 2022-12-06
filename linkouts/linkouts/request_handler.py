import yaml
import logging
import re
import glob

HREF = 'href'
METHOD = 'method'
TEXT = 'text'

GENE_LINKOUTS = 'gene_linkouts'
GENE_REGEX = re.compile('{GENE_ID}') 

GENOMIC_REGION_LINKOUTS = 'genomic_region_linkouts'
GENOMIC_REGION_SPECIFIER_REGEX = re.compile('^([^:]+):(\d+)(-|\.\.)(\d+)$') 
GENOMIC_REGION_REGEX = re.compile('{GENOMIC_REGION}') 
GENOMIC_REGION_CHR_ID_REGEX = re.compile('{GENOMIC_REGION_CHR_ID}') 
GENOMIC_REGION_START_REGEX = re.compile('{GENOMIC_REGION_START}') 
GENOMIC_REGION_END_REGEX = re.compile('{GENOMIC_REGION_END}') 

class RequestHandler:


  def __init__(self, lglob_root):
    self.linkout_lookup = {}
    try:
      for lfile in glob.glob('**/LINKOUTS.*.yml', root_dir=lglob_root, recursive=True):
        self._read_linkouts(lglob_root + '/' + lfile)
    except Exception as e:
      logging.error('failed to read linkouts from ' + lglob_root + '/' + lfile)
      logging.error(e)

  def _read_linkouts(self, lfile):
    f = open(lfile, 'r')
    yml =  yaml.load(f.read(), Loader=yaml.FullLoader)
    prefix = yml['prefix']

    for linkable_type in [GENE_LINKOUTS, GENOMIC_REGION_LINKOUTS]:
      if yml.get(linkable_type) != None:
        for linkout in yml[linkable_type]:
          if self.linkout_lookup.get(linkable_type) == None:
            self.linkout_lookup[linkable_type] = {}
          type_lookup = self.linkout_lookup[linkable_type]
          if type_lookup.get(prefix) == None:
            type_lookup[prefix] = []
          type_lookup[prefix].append(linkout)

  async def process_genes(self, ids):
    linkouts = []
    if self.linkout_lookup.get(GENE_LINKOUTS) == None:
      return linkouts 
    
    type_lookup = self.linkout_lookup.get(GENE_LINKOUTS)

    for id in ids:
      prefix = '.'.join(id.split('.')[0:4])
      if type_lookup.get(prefix) != None:
        templates = type_lookup[prefix]
        for template in templates:
          linkout = {}
          linkout[METHOD] = template[METHOD]
          #TODO: if method is POST, we probably need to do something with the request body content
          linkout[HREF] = GENE_REGEX.sub(id, template[HREF])
          linkout[TEXT] = GENE_REGEX.sub(id, template[TEXT])
          linkouts.append(linkout)
    return linkouts

  async def process_genomic_regions(self, ids):
    linkouts = []
    if self.linkout_lookup.get(GENOMIC_REGION_LINKOUTS) == None:
      return linkouts 
    
    type_lookup = self.linkout_lookup.get(GENOMIC_REGION_LINKOUTS)

    for id in ids:
      m = GENOMIC_REGION_SPECIFIER_REGEX.match(id)
      if m == None:
        continue
      chr = m.group(1)
      start = m.group(2)
      end = m.group(4)

      prefix = '.'.join(chr.split('.')[0:3])
      if type_lookup.get(prefix) != None:
        templates = type_lookup[prefix]
        for template in templates:
          linkout = {}
          linkout[METHOD] = template[METHOD]
          #TODO: if method is POST, we probably need to do something with the request body content
          linkout_href = GENOMIC_REGION_REGEX.sub(id, template[HREF])
          linkout_href = GENOMIC_REGION_CHR_ID_REGEX.sub(chr, linkout_href)
          linkout_href = GENOMIC_REGION_START_REGEX.sub(start, linkout_href)
          linkout_href = GENOMIC_REGION_END_REGEX.sub(end, linkout_href)
          linkout[HREF] = linkout_href
          linkout[TEXT] = GENOMIC_REGION_REGEX.sub(id, template[TEXT])
          linkouts.append(linkout)
    return linkouts
