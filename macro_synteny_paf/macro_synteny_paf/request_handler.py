# Python
import asyncio
import hashlib
import json
import logging

# dependencies
from redis.commands.search import AsyncSearch
from redis.commands.search.query import Query

# module
from macro_synteny_paf.grpc_client import (
    computeMacroSyntenyBlocks,
    computeMacroSyntenyBlocksByChromosome,
    getChromosome,
    getChromosomeLength,
    getGenes,
)


class RequestHandler:
    def __init__(
        self,
        redis_connection,
        chromosome_address,
        genes_address,
        macrosyntenyblocks_address,
        breakpoint_characters=",.<>{}[]\"':;!@#$%^&*()-+=~",
        cache_enabled=True,
        cache_ttl=86400,
    ):
        self.redis_connection = redis_connection
        self.chromosome_address = chromosome_address
        self.genes_address = genes_address
        self.macrosyntenyblocks_address = macrosyntenyblocks_address
        self.breakpoint_characters = set(breakpoint_characters)
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl

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
        identity=None,
        anchors=None,
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
        # validate identity parameter
        if identity is not None and identity not in ("levenshtein", "jaccard"):
            raise ValueError('identity must be "levenshtein" or "jaccard"')
        # validate anchors parameter
        if anchors is not None and anchors not in ("simple", "regular"):
            raise ValueError('anchors must be "simple" or "regular"')
        return (
            genome_1,
            genome_2,
            matched,
            intermediate,
            mask,
            metrics,
            chromosome_genes,
            chromosome_length,
            identity,
            anchors,
        )

    async def _getChromosomeNames(
        self,
        genome_prefix,
    ):
        # connect to the index
        chromosome_index = AsyncSearch(
            self.redis_connection, index_name="chromosomeIdx"
        )
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
        query = (
            Query(cleaned_name)
            .in_order()
            .limit_fields("name")
            .return_fields("name")
            .paging(0, num_chromosomes)
        )
        result = await chromosome_index.search(query)
        chromosome_names = list(map(lambda d: d.name, result.docs))
        return chromosome_names

    # returns the PAF row for a single macro-synteny block
    async def _blockToPafRow(
        self,
        query_chromosome_name,
        query_chromosome_length,
        target_chromosome_name,
        target_chromosome_length,
        target_block,
        # default values for PAF columns that are not available from the microservices
        num_residue_matches=1,
        alignment_block_length=1,
        mapping_quality=255,  # denotes 'missing'
    ):
        # Check if block has enriched gene information from macro-synteny-blocks
        if hasattr(target_block, "queryGeneFmin") and target_block.queryGeneFmin:
            # Use pre-fetched gene positions from enriched blocks
            query_start = target_block.queryGeneFmin
            query_end = target_block.queryGeneFmax
        else:
            # Fallback: get gene information from the genes microservice
            # This path is used when macro-synteny-blocks doesn't have genes_address configured
            gene_names = [list(query_chromosome.track.genes)[target_block.i]]
            genes = await getGenes(gene_names, self.genes_address)
            filtered_genes = list(filter(lambda d: d is not None, genes))
            # there should be only one match (index 0)
            query_start = filtered_genes[0].fmin
            query_end = filtered_genes[0].fmax

        # PAF format is defined here: https://github.com/lh3/miniasm/blob/master/PAF.md
        paf_row = f"{query_chromosome_name}\t{query_chromosome_length}\t{query_start}\t{query_end}\t{target_block.orientation}\t{target_chromosome_name}\t{target_chromosome_length}\t{target_block.fmin}\t{target_block.fmax}\t{num_residue_matches}\t{alignment_block_length}\t{mapping_quality}"

        # Add optionalMetrics as PAF tag if present (om:B:f,value1,value2,...)
        if hasattr(target_block, "optionalMetrics") and target_block.optionalMetrics:
            metrics_str = ",".join(str(m) for m in target_block.optionalMetrics)
            paf_row += f"\tom:B:f,{metrics_str}"

        return paf_row + "\n"

    # returns JSON object for a single macro-synteny block
    async def _blockToJson(
        self,
        query_chromosome_name,
        query_chromosome_length,
        target_chromosome_name,
        target_chromosome_length,
        target_block,
        # default values for PAF columns that are not available from the microservices
        num_residue_matches=1,
        alignment_block_length=1,
        mapping_quality=255,  # denotes 'missing'
    ):
        # Check if block has enriched gene information from macro-synteny-blocks
        if hasattr(target_block, "queryGeneFmin") and target_block.queryGeneFmin:
            query_start = target_block.queryGeneFmin
            query_end = target_block.queryGeneFmax
        else:
            gene_names = [list(query_chromosome.track.genes)[target_block.i]]
            genes = await getGenes(gene_names, self.genes_address)
            filtered_genes = list(filter(lambda d: d is not None, genes))
            # there should be only one match (index 0)
            query_start = filtered_genes[0].fmin
            query_end = filtered_genes[0].fmax

        result = {
            "query": {
                "name": query_chromosome_name,
                "length": query_chromosome_length,
                "start": query_start,
                "end": query_end,
            },
            "target": {
                "name": target_chromosome_name,
                "length": target_chromosome_length,
                "start": target_block.fmin,
                "end": target_block.fmax,
            },
            "strand": target_block.orientation,
            "numResidueMatches": num_residue_matches,
            "alignmentBlockLength": alignment_block_length,
            "mappingQuality": mapping_quality,
        }
        # Include identity if present
        if hasattr(target_block, "identity") and target_block.HasField("identity"):
            result["identity"] = target_block.identity
        # Include optionalMetrics if present
        if hasattr(target_block, "optionalMetrics"):
            metrics_list = list(target_block.optionalMetrics)
            logging.debug(
                f"Block has optionalMetrics: {metrics_list}, length: {len(metrics_list)}"
            )
            if metrics_list:
                result["optionalMetrics"] = metrics_list
        else:
            logging.debug(
                f"Block does not have optionalMetrics attribute. Block attributes: {dir(target_block)}"
            )
        return result

    # returns PAF rows for a target block object (containing multiple macro-synteny blocks)
    async def _blocksToPafRows(
        self,
        query_chromosome_name,
        query_chromosome_length,
        target_block,
    ):
        # Check if target block has enriched chromosomeLength from macro-synteny-blocks
        if hasattr(target_block, "chromosomeLength") and target_block.chromosomeLength:
            # Use pre-fetched chromosome length from enriched blocks
            target_chromosome_length = target_block.chromosomeLength
        else:
            # Fallback: get target chromosome length from the chromosome microservice
            # This path is used when macro-synteny-blocks doesn't have enrichment enabled
            target_chromosome_length = await getChromosomeLength(
                target_block.chromosome,
                self.chromosome_address,
            )

        paf_rows = await asyncio.gather(
            *[
                # compute PAF rows for each target block
                self._blockToPafRow(
                    query_chromosome_name,
                    query_chromosome_length,
                    target_block.chromosome,
                    target_chromosome_length,
                    tgt_block,
                )
                for tgt_block in target_block.blocks
            ]
        )
        return "".join(paf_rows)

    # returns JSON array for a target block object (containing multiple macro-synteny blocks)
    async def _blocksToJson(
        self,
        query_chromosome_name,
        query_chromosome_length,
        target_block,
        query_assembly_name=None,
        target_assembly_name=None,
        anchors=None,
    ):
        # Check if target block has enriched chromosomeLength from macro-synteny-blocks
        if hasattr(target_block, "chromosomeLength") and target_block.chromosomeLength:
            target_chromosome_length = target_block.chromosomeLength
        else:
            target_chromosome_length = await getChromosomeLength(
                target_block.chromosome,
                self.chromosome_address,
            )

        json_objects = await asyncio.gather(
            *[
                self._blockToJson(
                    query_chromosome_name,
                    query_chromosome_length,
                    target_block.chromosome,
                    target_chromosome_length,
                    tgt_block,
                )
                for tgt_block in target_block.blocks
            ]
        )

        # If regular anchors mode, extract correspondences as top-level JBrowse-compatible objects
        if anchors == "regular":
            jbrowse_objects = []
            for idx, tgt_block in enumerate(target_block.blocks):
                if hasattr(tgt_block, "correspondences") and tgt_block.correspondences:
                    for corr_idx, corr in enumerate(tgt_block.correspondences):
                        # Skip self-identity correspondences (same position on query and target)
                        # These create "vertical lines" that obscure synteny relationships
                        if (
                            corr.query_fmin == corr.target_fmin
                            and corr.query_fmax == corr.target_fmax
                        ):
                            continue
                        # Generate unique ID from chromosome names and coordinates
                        unique_id = f"{query_chromosome_name}:{corr.query_fmin}-{corr.query_fmax}_{target_block.chromosome}:{corr.target_fmin}-{corr.target_fmax}"
                        jbrowse_obj = {
                            "uniqueId": unique_id,
                            "refName": target_block.chromosome,
                            "start": corr.target_fmin,
                            "end": corr.target_fmax,
                            "assemblyName": target_assembly_name,
                            "strand": tgt_block.orientation,
                            "mate": {
                                "refName": query_chromosome_name,
                                "start": corr.query_fmin,
                                "end": corr.query_fmax,
                                "assemblyName": query_assembly_name,
                            },
                        }
                        # Include identity if present on the block
                        if hasattr(tgt_block, "identity") and tgt_block.HasField(
                            "identity"
                        ):
                            jbrowse_obj["identity"] = tgt_block.identity
                        jbrowse_objects.append(jbrowse_obj)
            return jbrowse_objects

        return json_objects

    def _generate_cache_key(
        self,
        genome_1,
        genome_2,
        matched,
        intermediate,
        mask,
        metrics,
        chromosome_genes,
        chromosome_length,
        output_format,
        identity=None,
        anchors=None,
    ):
        """
        Generate a deterministic cache key from request parameters.

        Returns:
            str: A Redis key for caching this specific computation.
        """
        # Convert metrics list to a stable string representation
        metrics_str = ",".join(sorted(metrics)) if metrics else ""
        identity_str = identity if identity else ""
        anchors_str = anchors if anchors else ""
        # Create a composite key from all parameters including format
        key_components = (
            f"{genome_1}:{genome_2}:{matched}:{intermediate}:"
            f"{mask}:{metrics_str}:{chromosome_genes}:{chromosome_length}:{output_format}:{identity_str}:{anchors_str}"
        )
        # Hash to create a fixed-length key
        hash_digest = hashlib.sha256(key_components.encode()).hexdigest()
        # Use a versioned prefix to allow cache invalidation if format changes
        return f"synteny_cache:v5:{hash_digest}"

    async def _computeResults(
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
        output_format,
        identity=None,
        anchors=None,
        query_assembly_name=None,
        target_assembly_name=None,
    ):
        # Use the new ComputeByChromosome endpoint in macro-synteny-blocks
        # This now returns enriched blocks with gene positions and chromosome lengths
        # Request correspondences from backend when anchors="regular"
        correspondences = anchors == "regular"
        target_blocks = await computeMacroSyntenyBlocksByChromosome(
            query_chromosome_name,
            matched,
            intermediate,
            mask,
            targets,
            metrics,
            chromosome_genes,
            chromosome_length,
            self.macrosyntenyblocks_address,
            identity,
            correspondences,
        )
        # remove the targets that didn't return any blocks
        filtered_target_blocks = list(filter(lambda b: b is not None, target_blocks))

        # Get query chromosome length (still needed for both formats)
        # NOTE: If blocks are enriched, we could optimize this by getting it from
        # the chromosome service call inside macro-synteny-blocks, but that would
        # require passing it back in the response
        query_chromosome = await getChromosome(
            query_chromosome_name, self.chromosome_address
        )
        query_chromosome_length = query_chromosome.length

        if output_format == "paf":
            # Return PAF format (tab-delimited text)
            paf_rows = await asyncio.gather(
                *[
                    # compute PAF rows for each target block
                    self._blocksToPafRows(
                        query_chromosome_name,
                        query_chromosome_length,
                        target_block,
                    )
                    for target_block in filtered_target_blocks
                ]
            )
            return "".join(paf_rows)
        else:
            # Return JSON format (list of alignment objects)
            json_arrays = await asyncio.gather(
                *[
                    # compute JSON objects for each target block
                    self._blocksToJson(
                        query_chromosome_name,
                        query_chromosome_length,
                        target_block,
                        query_assembly_name,
                        target_assembly_name,
                        anchors=anchors,
                    )
                    for target_block in filtered_target_blocks
                ]
            )
            # Flatten the list of lists into a single list
            return [item for sublist in json_arrays for item in sublist]

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
        identity=None,
        anchors=None,
        grpc_decode=False,
        output_format="json",
    ):
        cache_key = None
        # Check cache first if caching is enabled
        if self.cache_enabled:
            cache_key = self._generate_cache_key(
                genome_1,
                genome_2,
                matched,
                intermediate,
                mask,
                metrics,
                chromosome_genes,
                chromosome_length,
                output_format,
                identity,
                anchors,
            )

            try:
                cached_result = await self.redis_connection.get(cache_key)
                if cached_result:
                    try:
                        cached_json = json.loads(cached_result)
                        return cached_json
                    except json.JSONDecodeError:
                        return cached_result
            except Exception as e:
                # Log cache retrieval errors but continue with computation
                # This ensures cache failures don't break the service
                logging.warning(f"Cache retrieval failed for key {cache_key}: {e}")

        # Cache miss or caching disabled - compute the result
        genome_1_chrs = await self._getChromosomeNames(genome_1)
        genome_2_chrs = await self._getChromosomeNames(genome_2)
        iter(genome_1_chrs)  # TypeError if not iterable
        iter(genome_2_chrs)  # TypeError if not iterable

        results = await asyncio.gather(
            *[
                # compute results for each target chromosome
                self._computeResults(
                    chr1_name,
                    matched,
                    intermediate,
                    mask,
                    genome_2_chrs,
                    metrics,
                    chromosome_genes,
                    chromosome_length,
                    grpc_decode,
                    output_format,
                    identity,
                    anchors,
                    query_assembly_name=genome_1,
                    target_assembly_name=genome_2,
                )
                for chr1_name in genome_1_chrs
            ]
        )

        # Combine results based on format
        if output_format == "paf":
            result = "".join(results)
        else:
            all_alignments = [item for sublist in results for item in sublist]
            result = {"alignments": all_alignments}

        # Store result in cache if caching is enabled
        if self.cache_enabled and cache_key is not None:
            try:
                # For JSON, serialize before caching
                cache_value = result
                if output_format == "json":
                    cache_value = json.dumps(result)

                # Store with TTL
                await self.redis_connection.setex(
                    cache_key, self.cache_ttl, cache_value
                )
            except Exception as e:
                # Log cache storage errors but don't fail the request
                # The computation succeeded, cache failure is non-critical
                logging.warning(f"Cache storage failed for key {cache_key}: {e}")

        return result
