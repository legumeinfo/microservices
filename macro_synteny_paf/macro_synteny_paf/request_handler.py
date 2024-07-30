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
        chr_prefix_1,
        chr_digits_1,
        n_chr_1,
        genome_2,
        chr_prefix_2,
        chr_digits_2,
        n_chr_2,
        matched,
        intermediate,
        mask,
        metrics,
        chromosome_genes,
        chromosome_length,
    ):
        chr_digits_1 = int(chr_digits_1) # ValueError
        chr_digits_2 = int(chr_digits_2) # ValueError
        n_chr_1 = int(n_chr_1) # ValueError
        n_chr_2 = int(n_chr_2) # ValueError
        # Assumes that chromosome names have format (chr_prefix + number),
        # padding number with leading zeros to chr_digits digits
        genome_1_chrs = [ genome_1 + '.' + chr_prefix_1 + str(i).zfill(chr_digits_1) for i in range(1, n_chr_1 + 1) ]
        genome_2_chrs = [ genome_2 + '.' + chr_prefix_2 + str(i).zfill(chr_digits_2) for i in range(1, n_chr_2 + 1) ]
        iter(genome_1_chrs) # TypeError if not iterable
        iter(genome_2_chrs) # TypeError if not iterable
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
            genome_1_chrs,
            genome_2_chrs,
            matched,
            intermediate,
            mask,
            metrics,
            chromosome_genes,
            chromosome_length,
        )

    def _grpcBlockToDictBlock(self, grpc_block):
        dict_block = {
            "i": grpc_block.i,
            "j": grpc_block.j,
            "fmin": grpc_block.fmin,
            "fmax": grpc_block.fmax,
            "orientation": grpc_block.orientation,
        }
        if grpc_block.optionalMetrics:
            dict_block["optionalMetrics"] = list(grpc_block.optionalMetrics)
        return dict_block

    def _grpcBlocksToDictBlocks(self, grpc_blocks):
        dict_blocks = {
            "chromosome": grpc_blocks.chromosome,
            "genus": grpc_blocks.genus,
            "species": grpc_blocks.species,
            "blocks": list(map(self._grpcBlockToDictBlock, grpc_blocks.blocks)),
        }
        return dict_blocks

    def _grpcGeneToDictGene(self, grpc_gene):
        dict_gene = {
            "name": grpc_gene.name,
            "fmin": grpc_gene.fmin,
            "fmax": grpc_gene.fmax,
            "strand": grpc_gene.strand,
            "family": grpc_gene.family,
            "chromosome": grpc_gene.chromosome,
        }
        return dict_gene

    def _grpcChromosomeToDictChromosome(self, grpc_chromosome):
        dict_chromosome = {
            "length": grpc_chromosome.length,
            "genus": grpc_chromosome.track.genus,
            "species": grpc_chromosome.track.species,
            "genes": list(grpc_chromosome.track.genes),
            "families": list(grpc_chromosome.track.families),
        }
        return dict_chromosome

    def _grpcChromosomeToLength(self, grpc_chromosome):
        return grpc_chromosome.length

    async def _computePafRows(
        self,
        chr1,
        matched,
        intermediate,
        mask,
        targets,
        metrics,
        chromosome_genes,
        chromosome_length,
        grpc_decode,
    ):
        # PAF format is defined here: https://github.com/lh3/miniasm/blob/master/PAF.md

        # use these default values for PAF columns that are not available from the microservices
        num_residue_matches = 1
        alignment_block_length = 1
        mapping_quality = 255 # denotes 'missing'

        # compute blocks for target chromosomes from the macro-synteny-blocks microservice
        target_blocks_doc = await computeMacroSyntenyBlocks(
            chr1["families"],
            matched,
            intermediate,
            mask,
            targets,
            metrics,
            chromosome_genes,
            chromosome_length,
            self.macrosyntenyblocks_address,
        )
        target_blocks = list(map(self._grpcBlocksToDictBlocks, target_blocks_doc))
        # remove the targets that didn't return any blocks
        filtered_target_blocks = list(filter(lambda b: b is not None, target_blocks))

        # count number of blocks
        num_blocks = 0
        for b in filtered_target_blocks:
            num_blocks += len(b["blocks"])
        paf_rows = ['']*num_blocks

        # loop over blocks to create PAF rows
        paf_row_index = 0
        for b in filtered_target_blocks:
            target_sequence_name = b["chromosome"]
            # get target chromosome length from the chromosome microservice
            target_sequence_length = await getChromosomeLength(target_sequence_name, self.chromosome_address)
            for bi in b["blocks"] :
                query_sequence_name = chr1["name"]
                query_sequence_length = chr1["length"]
                # get gene information from the genes microservice
                gene_names = [ chr1["genes"][bi["i"]] ]
                gene_docs = await getGenes(gene_names, self.genes_address)
                genes = list(map(self._grpcGeneToDictGene, filter(lambda d: d is not None, gene_docs)))
                query_start = genes[0]["fmin"]
                query_end = genes[0]["fmax"]
                strand = bi["orientation"]
                target_start = bi["fmin"]
                target_end = bi["fmax"]

                # create PAF row for the current block
                paf_rows[paf_row_index] = f'{query_sequence_name}\t{query_sequence_length}\t{query_start}\t{query_end}\t{strand}\t{target_sequence_name}\t{target_sequence_length}\t{target_start}\t{target_end}\t{num_residue_matches}\t{alignment_block_length}\t{mapping_quality}\n'
                paf_row_index += 1
        return ''.join(paf_rows)

    async def process(
        self,
        genome_1_chrs,
        genome_2_chrs,
        matched,
        intermediate,
        mask,
        metrics,
        chromosome_genes,
        chromosome_length,
        grpc_decode=False,
    ):
        # other chromosome 1 information
        all_paf_rows = []
        for chr1_name in genome_1_chrs :
            # call chromosome microservice
            chr1_doc = await getChromosome(chr1_name, self.chromosome_address)
            chr1 = self._grpcChromosomeToDictChromosome(chr1_doc)
            # include query chromosome name as we will need it in self._computePafRows()
            chr1["name"] = chr1_name

            # compute PAF rows for each target chromosome
            paf_rows = await self._computePafRows(
                chr1,
                matched,
                intermediate,
                mask,
                genome_2_chrs,
                metrics,
                chromosome_genes,
                chromosome_length,
                grpc_decode,
            )
            all_paf_rows += paf_rows

        return ''.join(all_paf_rows)
