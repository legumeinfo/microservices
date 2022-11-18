import yaml
import re
import glob

class RequestHandler:

  GENE_LINKOUTS = 'gene_linkouts'
  GENE_REGEX = re.compile('{GENE_ID}') 

  GENOMIC_REGION_LINKOUTS = 'genomic_region_linkouts'
  GENOMIC_REGION_SPECIFIER_REGEX = re.compile('^([^:]+):(\d+)(-|\.\.)(\d+)$') 
  GENOMIC_REGION_REGEX = re.compile('{GENOMIC_REGION}') 
  GENOMIC_REGION_CHR_ID_REGEX = re.compile('{GENOMIC_REGION_CHR_ID}') 
  GENOMIC_REGION_START_REGEX = re.compile('{GENOMIC_REGION_START}') 
  GENOMIC_REGION_END_REGEX = re.compile('{GENOMIC_REGION_END}') 

  def __init__(self, lglob_root):
    self.linkout_lookup = {}
    for lfile in glob.glob('**/README.*.yml', root_dir=lglob_root, recursive=True):
      self._read_linkouts(lglob_root + '/' + lfile)

  def _read_linkouts(self, lfile):
    f = open(lfile, 'r')
    yml =  yaml.load(f.read(), Loader=yaml.FullLoader)
    gensp = yml['scientific_name_abbrev']
    ident = yml['identifier']
    #strip off KEY, prepend gensp
    ident = ident.split('.')
    ident.insert(0, gensp)
    ident.pop(len(ident)-1)
    prefix = '.'.join(ident) 

    for linkable_type in [RequestHandler.GENE_LINKOUTS, RequestHandler.GENOMIC_REGION_LINKOUTS]:
      if yml.get(linkable_type) != None:
        for linkout in yml[linkable_type]:
          if self.linkout_lookup.get(linkable_type) == None:
            self.linkout_lookup[linkable_type] = {}
          type_lookup = self.linkout_lookup[linkable_type]
          if type_lookup.get(prefix) == None:
            type_lookup[prefix] = []
          type_lookup[prefix].append(linkout)

  def process_genes(self, ids):
    linkouts = []
    if self.linkout_lookup.get(RequestHandler.GENE_LINKOUTS) == None:
      return linkouts 
    
    type_lookup = self.linkout_lookup.get(RequestHandler.GENE_LINKOUTS)

    for id in ids:
      prefix = '.'.join(id.split('.')[0:4])
      if type_lookup.get(prefix) != None:
        templates = type_lookup[prefix]
        for template in templates:
          linkout = {}
          linkout['method'] = template['method']
          #TODO: if method is POST, we probably need to do something with the request body content
          linkout['href'] = RequestHandler.GENE_REGEX.sub(id, template['href'])
          linkout['text'] = RequestHandler.GENE_REGEX.sub(id, template['text'])
          linkouts.append(linkout)
    return linkouts

  def process_genomic_regions(self, ids):
    linkouts = []
    if self.linkout_lookup.get(RequestHandler.GENOMIC_REGION_LINKOUTS) == None:
      return linkouts 
    
    type_lookup = self.linkout_lookup.get(RequestHandler.GENOMIC_REGION_LINKOUTS)

    for id in ids:
      m = RequestHandler.GENOMIC_REGION_SPECIFIER_REGEX.match(id)
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
          linkout['method'] = template['method']
          #TODO: if method is POST, we probably need to do something with the request body content
          linkout_href = RequestHandler.GENOMIC_REGION_REGEX.sub(id, template['href'])
          linkout_href = RequestHandler.GENOMIC_REGION_CHR_ID_REGEX.sub(chr, linkout_href)
          linkout_href = RequestHandler.GENOMIC_REGION_START_REGEX.sub(start, linkout_href)
          linkout_href = RequestHandler.GENOMIC_REGION_END_REGEX.sub(end, linkout_href)
          linkout['href'] = linkout_href
          linkout['text'] = RequestHandler.GENOMIC_REGION_REGEX.sub(id, template['text'])
          linkouts.append(linkout)
    return linkouts
