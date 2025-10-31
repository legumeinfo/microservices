# Python
import asyncio
import logging
from collections import defaultdict

# dependencies
from redis.commands.search.query import Query

# module
from macro_synteny_blocks.aioredisearch import CustomAsyncSearch
from macro_synteny_blocks.grpc_client import computePairwiseMacroSyntenyBlocks, getChromosome, getGenes


class RequestHandler:
    def __init__(
        self,
        redis_connection,
        pairwise_address,
        chromosome_address=None,
        genes_address=None,
        breakpoint_characters=",.<>{}[]\"':;!@#$%^&*()-+=~",
    ):
        self.redis_connection = redis_connection
        self.pairwise_address = pairwise_address
        self.chromosome_address = chromosome_address
        self.genes_address = genes_address
        self.breakpoint_characters = set(breakpoint_characters)

    def parseArguments(
        self,
        chromosome,
        matched,
        intermediate,
        mask,
        targets,
        metrics,
        chromosome_genes,
        chromosome_length,
    ):
        iter(chromosome)  # TypeError if not iterable
        if targets is None:
            targets = []
        iter(targets)  # TypeError if not iterable
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
            chromosome,
            matched,
            intermediate,
            mask,
            targets,
            metrics,
            chromosome_genes,
            chromosome_length,
        )

    def _cleanTag(self, tag):
        parts = []
        for c in tag:
            if c in self.breakpoint_characters:
                parts.append("\\")
            parts.append(c)
        return ''.join(parts)

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

    async def _getTargets(self, targets, chromosome, matched, intermediate):
        BATCH_SIZE = 100

        # use a pipeline to reduce the number of calls to database
        pipeline = self.redis_connection.pipeline()
        gene_index = CustomAsyncSearch(pipeline, index_name="geneIdx")

        # get genes for each family and bin them by chromosome
        families = set(chromosome)
        families.discard("")
        chromosome_match_indices = defaultdict(list)

        # pre-compute cleaned targets string once
        targets_query_part = ""
        if targets:
            cleaned_targets = [self._cleanTag(target) for target in targets]
            targets_query_part = f"(@chromosome:{{{'|'.join(cleaned_targets)}}})"

        # clean all families once
        cleaned_families = [self._cleanTag(family) for family in families]

        # split families into batches
        family_batches = []
        for i in range(0, len(cleaned_families), BATCH_SIZE):
            family_batches.append(cleaned_families[i:i + BATCH_SIZE])

        # count the number of genes per family batch
        batch_queries = []
        query_strings = []
        for batch in family_batches:
            # combine all families in this batch with pipe (OR) operator
            query_string = f"(@family:{{{'|'.join(batch)}}}){targets_query_part}"
            query_strings.append(query_string)
            query = Query(query_string).verbatim().paging(0, 0)
            batch_queries.append(query)
            await gene_index.search(query) # returns the pipeline, not a Result!
        count_results = await pipeline.execute()

        # get the genes in each family batch
        for query_string, query, count_result in zip(query_strings, batch_queries, count_results):
            r = gene_index.search_result(query, count_result)
            num_genes = r.total
            query = (
                Query(query_string)
                .verbatim()
                .return_fields("chromosome", "index")
                .paging(0, num_genes)
            )
            await gene_index.search(query)
        gene_results = await pipeline.execute()

        # bin the genes by chromosome from all batch results
        if not gene_results or len(gene_results) == 0:
            logging.warning("No results returned from gene query pipeline")
            return []

        for query, res in zip(batch_queries, gene_results):
            result = gene_index.search_result(query, res)
            for d in result.docs:
                chromosome_match_indices[d.chromosome].append(int(d.index))

        # sort index lists and filter by match and intermediate parameters
        filtered_targets = []
        for name in chromosome_match_indices:
            num_genes = len(chromosome_match_indices[name])
            # there's not enough matches on the entire chromosome
            if num_genes < matched:
                continue
            # check blocks of genes that are closes
            indices = sorted(chromosome_match_indices[name])
            block = [indices[0]]
            for j, i in enumerate(indices[1:]):
                # match is close enough to previous match to add to block
                if (
                    intermediate < 1
                    and (i - block[-1]) / len(chromosome) <= intermediate
                ) or (intermediate >= 1 and i - block[-1] <= intermediate - 1):
                    block.append(i)
                # match is too far away from previous match
                else:
                    # save block if it's big enough
                    if (matched < 1 and len(block) / len(chromosome) >= matched) or (
                        matched >= 1 and len(block) >= matched
                    ):
                        filtered_targets.append(name)
                        break
                    # start a new block with the current match
                    block = [i]
                    # no need to compute more blocks if none will be large enough
                    if num_genes - j < matched:
                        break
            # save last block if it's big enough
            if (
                (matched < 1 and len(block) / len(chromosome) >= matched)
                or (matched >= 1 and len(block) >= matched)
                and (not filtered_targets or filtered_targets[-1] != name)
            ):
                filtered_targets.append(name)

        return filtered_targets

    async def _computePairwiseBlocks(
        self,
        chromosome,
        target,
        matched,
        intermediate,
        mask,
        metrics,
        chromosome_genes,
        chromosome_length,
        chromosome_index,
        grpc_decode,
    ):
        # compute the blocks for the target chromosome
        blocks = await computePairwiseMacroSyntenyBlocks(
            chromosome,
            target,
            matched,
            intermediate,
            mask,
            metrics,
            chromosome_genes,
            chromosome_length,
            self.pairwise_address,
        )
        if not blocks:  # true for None or []
            return None
        # fetch the chromosome object
        doc = await chromosome_index.load_document(f"chromosome:{target}")
        blocks_object = {
            "chromosome": target,
            "genus": doc.genus,
            "species": doc.species,
        }
        # decode the blocks if not outputting gRPC
        if grpc_decode:
            blocks_object["blocks"] = list(map(self._grpcBlockToDictBlock, blocks))
        else:
            blocks_object["blocks"] = blocks
        return blocks_object

    async def process(
        self,
        chromosome,
        matched,
        intermediate,
        mask,
        targets,
        metrics,
        chromosome_genes,
        chromosome_length,
        grpc_decode=False,
    ):
        # connect to the index
        chromosome_index = CustomAsyncSearch(
            self.redis_connection, index_name="chromosomeIdx"
        )
        # get all chromosome names if no targets are specified
        filtered_targets = await self._getTargets(
            targets, chromosome, matched, intermediate
        )
        # compute blocks for each chromosome that is large enough
        target_blocks = await asyncio.gather(
            *[
                self._computePairwiseBlocks(
                    chromosome,
                    name,
                    matched,
                    intermediate,
                    mask,
                    metrics,
                    chromosome_genes,
                    chromosome_length,
                    chromosome_index,
                    grpc_decode,
                )
                for name in filtered_targets
            ]
        )
        # remove the targets that didn't return any blocks
        filtered_target_blocks = list(filter(lambda b: b is not None, target_blocks))

        return filtered_target_blocks

    async def _enrichBlocksWithGeneInfo(self, blocks, query_gene_names):
        """
        Enrich blocks with query gene position information.

        Parameters:
            blocks: List of Blocks objects from process()
            query_gene_names: List of query chromosome gene names

        Returns:
            Enriched blocks with gene names and positions filled in
        """
        if self.genes_address is None:
            return blocks  # Return blocks unchanged if genes address not configured

        # Collect all unique gene names needed
        gene_names_to_fetch = set()
        for blocks_obj in blocks:
            for block in blocks_obj["blocks"]:
                gene_idx = block.i
                if gene_idx < len(query_gene_names):
                    gene_names_to_fetch.add(query_gene_names[gene_idx])

        if not gene_names_to_fetch:
            return blocks

        # Fetch all gene info in one call
        genes = await getGenes(list(gene_names_to_fetch), self.genes_address)
        if genes is None:
            return blocks

        # Create lookup map
        gene_map = {}
        for gene in genes:
            gene_map[gene.name] = gene

        # Enrich each block
        for blocks_obj in blocks:
            for block in blocks_obj["blocks"]:
                gene_idx = block.i
                if gene_idx < len(query_gene_names):
                    gene_name = query_gene_names[gene_idx]
                    if gene_name in gene_map:
                        gene = gene_map[gene_name]
                        block.queryGeneName = gene_name
                        block.queryGeneFmin = gene.fmin
                        block.queryGeneFmax = gene.fmax

        return blocks

    async def _addChromosomeLengths(self, blocks):
        """
        Add target chromosome lengths to Blocks objects.

        Parameters:
            blocks: List of Blocks objects from process()

        Returns:
            Blocks with chromosomeLength field filled in
        """
        # Connect to the chromosome index
        chromosome_index = CustomAsyncSearch(
            self.redis_connection, index_name="chromosomeIdx"
        )

        for blocks_obj in blocks:
            # Fetch the chromosome doc to get length
            doc = await chromosome_index.load_document(f"chromosome:{blocks_obj['chromosome']}")
            blocks_obj["chromosomeLength"] = int(doc.length)

        return blocks

    async def processWithChromosomeName(
        self,
        chromosome_name,
        matched,
        intermediate,
        mask,
        targets,
        metrics,
        chromosome_genes,
        chromosome_length,
        grpc_decode=False,
    ):
        """
        Process macro synteny blocks using a chromosome name instead of gene families.
        This method fetches the chromosome data from the chromosome microservice first,
        and enriches the returned blocks with gene position information.

        Parameters:
            chromosome_name (str): Name of the query chromosome.
            Other parameters: Same as process() method.

        Returns:
            Same as process() method, but with enriched blocks containing:
            - queryGeneName, queryGeneFmin, queryGeneFmax (if genes_address configured)
            - chromosomeLength in Blocks objects (target chromosome lengths)
        """
        if self.chromosome_address is None:
            raise ValueError(
                "Chromosome address is not configured. Cannot use ComputeByChromosome endpoint."
            )

        # Fetch chromosome data from the chromosome microservice
        chromosome_data = await getChromosome(chromosome_name, self.chromosome_address)

        if chromosome_data is None:
            raise ValueError(f"Chromosome '{chromosome_name}' not found")

        chromosome_families, query_gene_names, query_chromosome_length = chromosome_data

        # Use the existing process method with the fetched gene families
        blocks = await self.process(
            chromosome_families,
            matched,
            intermediate,
            mask,
            targets,
            metrics,
            chromosome_genes,
            chromosome_length,
            grpc_decode,
        )

        # Enrich blocks with query gene information
        blocks = await self._enrichBlocksWithGeneInfo(blocks, query_gene_names)

        # Add target chromosome lengths
        blocks = await self._addChromosomeLengths(blocks)

        return blocks
