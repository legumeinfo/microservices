# Python
import asyncio
from collections import defaultdict

# dependencies
from redis.commands.search.query import Query

# module
from macro_synteny_blocks.aioredisearch import CustomAsyncSearch
from macro_synteny_blocks.grpc_client import computePairwiseMacroSyntenyBlocks


class RequestHandler:
    def __init__(
        self,
        redis_connection,
        pairwise_address,
        breakpoint_characters=",.<>{}[]\"':;!@#$%^&*()-+=~",
    ):
        self.redis_connection = redis_connection
        self.pairwise_address = pairwise_address
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
                "matched, intermediate, chromosome genes, and chromosome length must be positive"
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
        cleaned_tag = ""
        for c in tag:
            if c in self.breakpoint_characters:
                cleaned_tag += "\\"
            cleaned_tag += c
        return cleaned_tag

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
        # use a pipeline to reduce the number of calls to database
        pipeline = self.redis_connection.pipeline()
        gene_index = CustomAsyncSearch(pipeline, index_name="geneIdx")

        # get genes for each family and bin them by chromosome
        families = set(chromosome)
        families.discard("")
        chromosome_match_indices = defaultdict(list)

        # count how many genes are in each family
        query_strings = []
        count_queries = []
        for family in families:
            cleaned_family = self._cleanTag(family)
            query_string = "(@family:{" + cleaned_family + "})"
            # limit the genes to the target chromosomes
            if targets:
                cleaned_targets = map(self._cleanTag, targets)
                query_string += "(@chromosome:{" + "|".join(cleaned_targets) + "})"
            query_strings.append(query_string)
            # count how many genes are in the family
            query = Query(query_string).verbatim().paging(0, 0)
            count_queries.append(query)
            await gene_index.search(query)  # returns the pipeline, not a Result!
        count_results = await pipeline.execute()

        # get the genes for each family
        gene_queries = []
        for family, query_string, query, res in zip(
            families, query_strings, count_queries, count_results
        ):
            result = gene_index.search_result(query, res)
            num_genes = result.total
            # get the genes
            query = (
                Query(query_string)
                .verbatim()
                .return_fields("chromosome", "index")
                .paging(0, num_genes)
            )
            gene_queries.append(query)
            await gene_index.search(query)  # returns the pipeline, not a Result!
        gene_results = await pipeline.execute()

        # bin the genes by chromosome
        for query, res in zip(gene_queries, gene_results):
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
