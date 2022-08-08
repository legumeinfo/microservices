# Python
import asyncio
from collections import defaultdict
from itertools import chain
# dependencies
from redis.commands.search.query import Query
from redis.commands.search import AsyncSearch


class RequestHandler:

  def __init__(self, redis_connection):
    self.redis_connection = redis_connection

  def parseArguments(self, query_track, matched, intermediate):
    iter(query_track)  # TypeError if not iterable
    matched = float(matched)  # ValueError
    intermediate = float(intermediate)  # ValueError
    if matched <= 0 or intermediate <= 0:
      raise ValueError('matched and intermediate must be positive')
    return query_track, matched, intermediate

  async def _blockToTrack(self, chromosome_doc, block):
    first = block[0]
    last = block[-1]
    genes, families = await asyncio.gather(
      self.redis_connection.lrange(f'{chromosome_doc.id}:genes', first, last),
      self.redis_connection.lrange(f'{chromosome_doc.id}:families', first, last)
    )
    # format and return
    track = {
        'name': chromosome_doc.name,
        'genus': chromosome_doc.genus,
        'species': chromosome_doc.species,
        'genes': genes,
        'families': families,
      }
    return track

  async def _chromosomeBlocksToTracks(self, chromosome_name, blocks, chromosome_index):
    chromosome_doc = await chromosome_index.load_document(f'chromosome:{chromosome_name}')
    tracks = await asyncio.gather(*[
      self._blockToTrack(chromosome_doc, block)
      for block in blocks
    ])
    return tracks

  async def _queryToChromosomeGeneMatchIndexes(self, query_track, gene_index):
    families = set(query_track)
    families.discard('')
    chromosome_match_indices = defaultdict(list)
    for family in families:
      # count how many genes are in the family
      query_string = '@family:{' + family + '}'
      query = Query(query_string)\
                .paging(0, 0)
      result = await gene_index.search(query)
      num_genes = result.total
      # get the genes
      query = Query(query_string)\
                .return_fields('chromosome', 'index')\
                .paging(0, num_genes)
      result = await gene_index.search(query)
      for d in result.docs:
        chromosome_match_indices[d.chromosome].append(int(d.index))
    return chromosome_match_indices

  async def _chromosomeGeneIndexesToBlocks(self, query_track, chromosome_match_indices, matched, intermediate):
    # compute blocks from indexes via islands and gaps
    blocks = defaultdict(list)
    for chromosome_name, indices in chromosome_match_indices.items():
      indices.sort()
      block = [indices[0]]
      for i in indices[1:]:
        # match is close enough to previous match to add to block
        if (intermediate < 1 and (i-block[-1])/len(query_track) <= intermediate) or \
        (intermediate >= 1 and i-block[-1] <= intermediate-1):
          block.append(i)
        # match is too far away from previous match
        else:
          # save block if it's big enough
          if (matched < 1 and len(block)/len(query_track) >= matched) or \
          (matched >= 1 and len(block) >= matched):
            blocks[chromosome_name].append(block)
          # start a new block with the current match
          block = [i]
      # save last block if it's big enough
      if (matched < 1 and len(block)/len(query_track) >= matched) or \
      (matched >= 1 and len(block) >= matched):
        blocks[chromosome_name].append(block)
    return blocks

  async def process(self, query_track, matched, intermediate):
    # connect to the index
    gene_index = AsyncSearch(self.redis_connection, index_name='geneIdx')
    chromosome_index = AsyncSearch(self.redis_connection, index_name='chromosomeIdx')
    # search the gene index
    # TODO: is there a way to query for all genes exactly at once?
    chromosome_match_indexes = await self._queryToChromosomeGeneMatchIndexes(query_track, gene_index)
    # compute micro-synteny blocks
    blocks = await self._chromosomeGeneIndexesToBlocks(query_track, chromosome_match_indexes, matched, intermediate)
    # fetch result tracks
    block_tracks = await asyncio.gather(*[
      self._chromosomeBlocksToTracks(chr_name, chr_blocks, chromosome_index)
      for chr_name, chr_blocks in blocks.items()
    ])
    tracks = list(chain(*block_tracks))
    return tracks
