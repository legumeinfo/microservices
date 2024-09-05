# Python
import asyncio

# dependencies
from redis.commands.search import AsyncSearch
from redis.commands.search.query import Query

# module
from macro_synteny_paf.grpc_client import getGenes, getChromosome, getChromosomeLength, computeMacroSyntenyBlocks


class RequestHandler:
    def __init__(
        self,
        redis_connection,
        chromosome_address,
        genes_address,
        macrosyntenyblocks_address,
        breakpoint_characters=",.<>{}[]\"':;!@#$%^&*()-+=~",
    ):
        self.redis_connection = redis_connection
        self.chromosome_address = chromosome_address
        self.genes_address = genes_address
        self.macrosyntenyblocks_address = macrosyntenyblocks_address
        self.breakpoint_characters = set(breakpoint_characters)

    def parseArguments(
        self,
        genome_1,
        genome_2,
        matched,
        intermediate,
        mask,
        metrics,
        chromosome_genes,
        chromosome_length,
    ):
        if metrics is None:
            metrics = []
        iter(metrics)  # TypeError if not iterable
        matched = int(matched)  # ValueError
        intermediate = int(intermediate)  # ValueError
        if chromosome_genes is None:
            chromosome_genes = matched
        else:
            chromosome_genes = int(chromosome_genes)  # ValueError
        if chromosome_length is None:
            chromosome_length = 1
        else:
            chromosome_length = int(chromosome_length)  # ValueError
        if (
            matched <= 0
            or intermediate <= 0
            or chromosome_genes <= 0
            or chromosome_length <= 0
        ):
            raise ValueError(
                """
                matched, intermediate, chromosome genes, and chromosome length must be
                positive
            """
            )
        if mask is not None:
            mask = int(mask)
            if mask <= 0:
                raise ValueError("mask must be positive")
        return (
            genome_1,
            genome_2,
            matched,
            intermediate,
            mask,
            metrics,
            chromosome_genes,
            chromosome_length,
        )

    async def _getChromosomeNames(
        self,
        genome_prefix,
    ):
        # connect to the index
        chromosome_index = AsyncSearch(self.redis_connection, index_name="chromosomeIdx")
        # replace RediSearch breakpoint characters with spaces
        cleaned_name = ""
        for c in genome_prefix:
            if c in self.breakpoint_characters:
                cleaned_name += " "
            else:
                cleaned_name += c
        # search the chromosome index
        # first get a count
        query = Query(cleaned_name).in_order().paging(0, 0)
        result = await chromosome_index.search(query)
        num_chromosomes = result.total
        # then get the chromosomes
        query = Query(cleaned_name).in_order().limit_fields("name").return_fields("name").paging(0, num_chromosomes)
        result = await chromosome_index.search(query)
        chromosome_names = list(map(lambda d: d.name, result.docs))
        return chromosome_names

    # returns the PAF row for a single macro-synteny block
    async def _blockToPafRow(
        self,
        query_chromosome_name,
        query_chromosome,
        target_chromosome_name,
        target_chromosome_length,
        target_block,
        # default values for PAF columns that are not available from the microservices
        num_residue_matches = 1,
        alignment_block_length = 1,
        mapping_quality = 255, # denotes 'missing'
    ):
        # get gene information from the genes microservice
        gene_names = [ list(query_chromosome.track.genes)[target_block.i] ]
        genes = await getGenes(gene_names, self.genes_address)
        filtered_genes = list(filter(lambda d: d is not None, genes))
        # there should be only one match (index 0)
        query_start = filtered_genes[0].fmin
        query_end = filtered_genes[0].fmax

        # PAF format is defined here: https://github.com/lh3/miniasm/blob/master/PAF.md
        return f'{query_chromosome_name}\t{query_chromosome.length}\t{query_start}\t{query_end}\t{target_block.orientation}\t{target_chromosome_name}\t{target_chromosome_length}\t{target_block.fmin}\t{target_block.fmax}\t{num_residue_matches}\t{alignment_block_length}\t{mapping_quality}\n'

    # returns PAF rows for a target block object (containing multiple macro-synteny blocks)
    async def _blocksToPafRows(
        self,
        query_chromosome_name,
        query_chromosome,
        target_block,
    ):
        # get target chromosome length from the chromosome microservice
        target_chromosome_length = await getChromosomeLength(
            target_block.chromosome,
            self.chromosome_address,
        )

        paf_rows = await asyncio.gather(
            *[
                # compute PAF rows for each target block
                self._blockToPafRow(
                    query_chromosome_name,
                    query_chromosome,
                    target_block.chromosome,
                    target_chromosome_length,
                    tgt_block,
                )
                for tgt_block in target_block.blocks
            ]
        )
        return ''.join(paf_rows)

    async def _computePafRows(
        self,
        query_chromosome_name,
        matched,
        intermediate,
        mask,
        targets,
        metrics,
        chromosome_genes,
        chromosome_length,
        grpc_decode,
    ):
        # call chromosome microservice
        query_chromosome = await getChromosome(query_chromosome_name, self.chromosome_address)

        # compute blocks for target chromosomes from the macro-synteny-blocks microservice
        target_blocks = await computeMacroSyntenyBlocks(
            list(query_chromosome.track.families),
            matched,
            intermediate,
            mask,
            targets,
            metrics,
            chromosome_genes,
            chromosome_length,
            self.macrosyntenyblocks_address,
        )
        # remove the targets that didn't return any blocks
        filtered_target_blocks = list(filter(lambda b: b is not None, target_blocks))

        paf_rows = await asyncio.gather(
            *[
                # compute PAF rows for each target block
                self._blocksToPafRows(
                    query_chromosome_name,
                    query_chromosome,
                    target_block,
                )
                for target_block in filtered_target_blocks
            ]
        )
        return ''.join(paf_rows)

    async def process(
        self,
        genome_1,
        genome_2,
        matched,
        intermediate,
        mask,
        metrics,
        chromosome_genes,
        chromosome_length,
        grpc_decode=False,
    ):
        genome_1_chrs = await self._getChromosomeNames(genome_1)
        genome_2_chrs = await self._getChromosomeNames(genome_2)
        iter(genome_1_chrs) # TypeError if not iterable
        iter(genome_2_chrs) # TypeError if not iterable

        paf_rows = await asyncio.gather(
            *[
                # compute PAF rows for each target chromosome
                self._computePafRows(
                    chr1_name,
                    matched,
                    intermediate,
                    mask,
                    genome_2_chrs,
                    metrics,
                    chromosome_genes,
                    chromosome_length,
                    grpc_decode,
                )
                for chr1_name in genome_1_chrs
            ]
        )
        return ''.join(paf_rows)
