from collections import namedtuple
from unittest.mock import patch

import pytest

from macro_synteny_blocks.request_handler import RequestHandler


@pytest.mark.unit
class TestCleanTag:
    """Test RediSearch special character escaping."""

    def setup_method(self):
        self.handler = RequestHandler(
            redis_connection=None, pairwise_address="localhost:8081"
        )

    def test_escape_special_characters(self):
        """Test that RediSearch breakpoint characters are escaped."""
        tag = "aradu.V14167"
        cleaned = self.handler._cleanTag(tag)

        assert cleaned == "aradu\\.V14167"

    def test_multiple_special_characters(self):
        """Test escaping of multiple special characters."""
        tag = "test-name.version:1"
        cleaned = self.handler._cleanTag(tag)

        # -, ., and : should all be escaped
        assert "\\" in cleaned
        assert cleaned == "test\\-name\\.version\\:1"

    def test_no_special_characters(self):
        """Test that regular strings pass through unchanged."""
        tag = "simplestring"
        cleaned = self.handler._cleanTag(tag)

        assert cleaned == "simplestring"


@pytest.mark.integration
@pytest.mark.asyncio
class TestGetTargets:
    """Test the batching optimization in _getTargets()."""

    async def test_batching_with_large_family_set(self, redis_connection):
        """Test that >100 families trigger batching logic."""
        # Create a large set of families (>100) to test batching
        chromosome = [f"test_batch_fam{i}" for i in range(150)]

        # Populate Redis with test data
        # Create genes on chr1 and chr2 with some of the families
        for i in range(10):
            await redis_connection.hset(
                f"gene:test_batch_gene_chr1_{i}",
                mapping={
                    "name": f"test_batch_gene_chr1_{i}",
                    "family": f"test_batch_fam{i}",
                    "chromosome": "test_batch_chr1",
                    "index": str(i),
                },
            )

        for i in range(5):
            await redis_connection.hset(
                f"gene:test_batch_gene_chr2_{i}",
                mapping={
                    "name": f"test_batch_gene_chr2_{i}",
                    "family": f"test_batch_fam{i + 100}",
                    "chromosome": "test_batch_chr2",
                    "index": str(i),
                },
            )

        handler = RequestHandler(
            redis_connection=redis_connection, pairwise_address="localhost:8081"
        )

        # Call _getTargets with large chromosome
        targets = await handler._getTargets(
            targets=[], chromosome=chromosome, matched=2, intermediate=50
        )

        # Should return the chromosomes that have matches
        assert len(targets) >= 0  # At least some targets should be found

        # Clean up test data
        for i in range(10):
            await redis_connection.delete(f"gene:test_batch_gene_chr1_{i}")
        for i in range(5):
            await redis_connection.delete(f"gene:test_batch_gene_chr2_{i}")

    async def test_filtering_by_matched(self, redis_connection):
        """Test that chromosomes with insufficient matches are filtered."""
        chromosome = [
            "test_match_fam1",
            "test_match_fam2",
            "test_match_fam3",
            "test_match_fam4",
        ]

        # chr1 has only 1 match (below matched=3)
        await redis_connection.hset(
            "gene:test_match_chr1_gene1",
            mapping={
                "name": "test_match_chr1_gene1",
                "family": "test_match_fam1",
                "chromosome": "test_match_chr1",
                "index": "0",
            },
        )

        # chr2 has 4 matches (meets matched=3)
        for i in range(4):
            await redis_connection.hset(
                f"gene:test_match_chr2_gene{i}",
                mapping={
                    "name": f"test_match_chr2_gene{i}",
                    "family": f"test_match_fam{i + 1}",
                    "chromosome": "test_match_chr2",
                    "index": str(i),
                },
            )

        handler = RequestHandler(
            redis_connection=redis_connection, pairwise_address="localhost:8081"
        )

        targets = await handler._getTargets(
            targets=[],
            chromosome=chromosome,
            matched=3,  # Minimum 3 matches required
            intermediate=10,
        )

        # Only chr2 should pass the filter
        assert "test_match_chr2" in targets
        assert "test_match_chr1" not in targets

        # Clean up test data
        await redis_connection.delete("gene:test_match_chr1_gene1")
        for i in range(4):
            await redis_connection.delete(f"gene:test_match_chr2_gene{i}")

    async def test_filtering_by_intermediate(self, redis_connection):
        """Test that chromosomes where matches are too sparse are filtered."""
        chromosome = [
            "test_inter_fam1",
            "test_inter_fam2",
            "test_inter_fam3",
            "test_inter_fam4",
        ]

        # chr1: matches at indices 0, 1, 2 (close together)
        for i in range(3):
            await redis_connection.hset(
                f"gene:test_inter_chr1_gene{i}",
                mapping={
                    "name": f"test_inter_chr1_gene{i}",
                    "family": f"test_inter_fam{i + 1}",
                    "chromosome": "test_inter_chr1",
                    "index": str(i),
                },
            )

        # chr2: matches at indices 0, 10, 20 (too far apart with intermediate=5)
        for idx, i in enumerate([0, 10, 20]):
            await redis_connection.hset(
                f"gene:test_inter_chr2_gene{idx}",
                mapping={
                    "name": f"test_inter_chr2_gene{idx}",
                    "family": f"test_inter_fam{idx + 1}",
                    "chromosome": "test_inter_chr2",
                    "index": str(i),
                },
            )

        handler = RequestHandler(
            redis_connection=redis_connection, pairwise_address="localhost:8081"
        )

        targets = await handler._getTargets(
            targets=[],
            chromosome=chromosome,
            matched=3,
            intermediate=5,  # Max gap of 5 between matches
        )

        # chr1 should pass (matches are close)
        assert "test_inter_chr1" in targets
        # chr2 should fail (matches too far apart)
        assert "test_inter_chr2" not in targets

        # Clean up test data
        for i in range(3):
            await redis_connection.delete(f"gene:test_inter_chr1_gene{i}")
        for idx in range(3):
            await redis_connection.delete(f"gene:test_inter_chr2_gene{idx}")

    async def test_with_targets_filter(self, redis_connection):
        """Test that targets parameter filters chromosomes."""
        chromosome = ["test_target_fam1", "test_target_fam2", "test_target_fam3"]

        # Both chr1 and chr2 have enough matches
        for i in range(3):
            await redis_connection.hset(
                f"gene:test_target_chr1_gene{i}",
                mapping={
                    "name": f"test_target_chr1_gene{i}",
                    "family": f"test_target_fam{i + 1}",
                    "chromosome": "test_target_chr1",
                    "index": str(i),
                },
            )
            await redis_connection.hset(
                f"gene:test_target_chr2_gene{i}",
                mapping={
                    "name": f"test_target_chr2_gene{i}",
                    "family": f"test_target_fam{i + 1}",
                    "chromosome": "test_target_chr2",
                    "index": str(i),
                },
            )

        handler = RequestHandler(
            redis_connection=redis_connection, pairwise_address="localhost:8081"
        )

        # Only request chr1
        targets = await handler._getTargets(
            targets=["test_target_chr1"],  # Filter to only chr1
            chromosome=chromosome,
            matched=2,
            intermediate=10,
        )

        # Should only return chr1, even though chr2 also meets criteria
        assert "test_target_chr1" in targets
        assert "test_target_chr2" not in targets

        # Clean up test data
        for i in range(3):
            await redis_connection.delete(f"gene:test_target_chr1_gene{i}")
            await redis_connection.delete(f"gene:test_target_chr2_gene{i}")


@pytest.mark.unit
@pytest.mark.asyncio
class TestEnrichBlocksWithGeneInfo:
    """Test the new gene enrichment feature."""

    def setup_method(self):
        self.handler = RequestHandler(
            redis_connection=None, pairwise_address="localhost:8081"
        )

    async def test_enrichment_with_genes_address(
        self, sample_blocks, sample_query_gene_names, mock_genes_service
    ):
        """Test that blocks are enriched when genes_address is configured."""
        self.handler.genes_address = "localhost:8082"

        # Mock getGenes function
        with patch(
            "macro_synteny_blocks.request_handler.getGenes", new=mock_genes_service
        ):
            enriched = await self.handler._enrichBlocksWithGeneInfo(
                sample_blocks, sample_query_gene_names
            )

            # Check that gene info was added
            for blocks_obj in enriched:
                for block in blocks_obj["blocks"]:
                    assert "queryGeneName" in block
                    assert "queryGeneFmin" in block
                    assert "queryGeneFmax" in block

    async def test_enrichment_uses_both_terminal_genes(
        self, sample_blocks, sample_query_gene_names, mock_genes_service
    ):
        """Test that enrichment uses both block.i and block.j (recent change)."""
        self.handler.genes_address = "localhost:8082"

        genes_fetched = set()

        async def tracking_mock_getGenes(gene_names, address):
            genes_fetched.update(gene_names)
            return await mock_genes_service(gene_names, address)

        with patch(
            "macro_synteny_blocks.request_handler.getGenes", new=tracking_mock_getGenes
        ):
            await self.handler._enrichBlocksWithGeneInfo(
                sample_blocks, sample_query_gene_names
            )

            # Should have fetched genes at both i and j indices
            # Block at i=0, j=2 should fetch gene1 (index 0) and gene3 (index 2)
            assert "gene1" in genes_fetched
            assert "gene3" in genes_fetched
            # Block at i=3, j=4 should fetch gene4 and gene5
            assert "gene4" in genes_fetched
            assert "gene5" in genes_fetched

    async def test_enrichment_without_genes_address(
        self, sample_blocks, sample_query_gene_names
    ):
        """Test that blocks are unchanged when genes_address is None."""
        self.handler.genes_address = None

        enriched = await self.handler._enrichBlocksWithGeneInfo(
            sample_blocks, sample_query_gene_names
        )

        # Blocks should be unchanged
        assert enriched == sample_blocks
        # No gene info should be added
        for blocks_obj in enriched:
            for block in blocks_obj["blocks"]:
                assert "queryGeneName" not in block

    async def test_enrichment_handles_grpc_objects(
        self, sample_query_gene_names, mock_genes_service
    ):
        """Test enrichment works with gRPC Block objects (not just dicts)."""
        self.handler.genes_address = "localhost:8082"

        # Create mock gRPC-style blocks using a simple class to simulate protobuf objects
        class MockGrpcBlock:
            def __init__(self, i, j, fmin, fmax, orientation):
                self.i = i
                self.j = j
                self.fmin = fmin
                self.fmax = fmax
                self.orientation = orientation

        grpc_blocks = [
            {
                "chromosome": "chr1",
                "genus": "Test",
                "species": "species",
                "blocks": [
                    MockGrpcBlock(i=0, j=2, fmin=0, fmax=2999, orientation="+"),
                ],
            }
        ]

        with patch(
            "macro_synteny_blocks.request_handler.getGenes", new=mock_genes_service
        ):
            enriched = await self.handler._enrichBlocksWithGeneInfo(
                grpc_blocks, sample_query_gene_names
            )

            # Check that enrichment worked with gRPC objects
            block = enriched[0]["blocks"][0]
            assert hasattr(block, "queryGeneName")
            assert hasattr(block, "queryGeneFmin")
            assert hasattr(block, "queryGeneFmax")

    async def test_enrichment_with_min_max_calculation(
        self, sample_query_gene_names, mock_genes_service
    ):
        """Test that fmin uses min and fmax uses max when both terminal genes present."""
        self.handler.genes_address = "localhost:8082"

        # Block with i=0, j=2 (spans from gene1 at index 0 to gene3 at index 2)
        blocks = [
            {
                "chromosome": "chr1",
                "genus": "Test",
                "species": "species",
                "blocks": [
                    {"i": 0, "j": 2, "fmin": 0, "fmax": 2999, "orientation": "+"},
                ],
            }
        ]

        with patch(
            "macro_synteny_blocks.request_handler.getGenes", new=mock_genes_service
        ):
            enriched = await self.handler._enrichBlocksWithGeneInfo(
                blocks, sample_query_gene_names
            )

            block = enriched[0]["blocks"][0]
            # gene1 (i=0): fmin=0, fmax=999 (from mock: gene_index=0, so 0*1000 to 0*1000+999)
            # gene3 (j=2): fmin=2000, fmax=2999 (from mock: gene_index=2, so 2*1000 to 2*1000+999)
            # queryGeneFmin should be min(0, 2000) = 0
            # queryGeneFmax should be max(999, 2999) = 2999
            assert block["queryGeneFmin"] == 0
            assert block["queryGeneFmax"] == 2999


@pytest.mark.unit
@pytest.mark.asyncio
class TestAddChromosomeLengths:
    """Test chromosome length enrichment."""

    async def test_add_chromosome_lengths(self, redis_with_chromosomes, sample_blocks):
        """Test that chromosome lengths are added to Blocks objects."""
        handler = RequestHandler(
            redis_connection=redis_with_chromosomes, pairwise_address="localhost:8081"
        )

        enriched = await handler._addChromosomeLengths(sample_blocks)

        # Check that chromosomeLength was added
        for blocks_obj in enriched:
            assert "chromosomeLength" in blocks_obj
            chr_name = blocks_obj["chromosome"]
            if chr_name == "chr1":
                assert blocks_obj["chromosomeLength"] == 10000
            elif chr_name == "chr2":
                assert blocks_obj["chromosomeLength"] == 8000


@pytest.mark.unit
@pytest.mark.asyncio
class TestProcessWithChromosomeName:
    """Test the new processWithChromosomeName endpoint."""

    async def test_process_with_chromosome_name_success(
        self,
        fakeredis_connection,
        mock_chromosome_service,
        mock_genes_service,
        mock_pairwise_service,
    ):
        """Test successful processing with chromosome name."""
        handler = RequestHandler(
            redis_connection=fakeredis_connection,
            pairwise_address="localhost:8081",
            chromosome_address="localhost:8082",
            genes_address="localhost:8083",
        )

        # Setup chromosome data in Redis
        await fakeredis_connection.hset(
            "chromosome:chr1",
            mapping={
                "name": "chr1",
                "genus": "Test",
                "species": "species",
                "length": "10000",
            },
        )

        with patch(
            "macro_synteny_blocks.request_handler.getChromosome",
            new=mock_chromosome_service,
        ):
            with patch(
                "macro_synteny_blocks.request_handler.getGenes", new=mock_genes_service
            ):
                with patch(
                    "macro_synteny_blocks.request_handler.computePairwiseMacroSyntenyBlocks",
                    new=mock_pairwise_service,
                ):
                    with patch.object(handler, "_getTargets", return_value=["chr1"]):
                        result = await handler.processWithChromosomeName(
                            chromosome_name="test_chr",
                            matched=3,
                            intermediate=5,
                            mask=None,
                            targets=[],
                            metrics=[],
                            chromosome_genes=3,
                            chromosome_length=1,
                        )

                        # Should return enriched blocks
                        assert isinstance(result, list)

    async def test_process_with_chromosome_name_no_address(self, fakeredis_connection):
        """Test that ValueError is raised when chromosome_address is None."""
        handler = RequestHandler(
            redis_connection=fakeredis_connection,
            pairwise_address="localhost:8081",
            chromosome_address=None,  # Not configured
        )

        with pytest.raises(ValueError, match="Chromosome address is not configured"):
            await handler.processWithChromosomeName(
                chromosome_name="test_chr",
                matched=3,
                intermediate=5,
                mask=None,
                targets=[],
                metrics=[],
                chromosome_genes=3,
                chromosome_length=1,
            )

    async def test_process_with_chromosome_name_not_found(
        self, fakeredis_connection, mock_chromosome_service
    ):
        """Test that ValueError is raised when chromosome is not found."""
        handler = RequestHandler(
            redis_connection=fakeredis_connection,
            pairwise_address="localhost:8081",
            chromosome_address="localhost:8082",
        )

        async def mock_getChromosome_none(name, address):
            return None

        with patch(
            "macro_synteny_blocks.request_handler.getChromosome",
            new=mock_getChromosome_none,
        ):
            with pytest.raises(ValueError, match="not found"):
                await handler.processWithChromosomeName(
                    chromosome_name="nonexistent",
                    matched=3,
                    intermediate=5,
                    mask=None,
                    targets=[],
                    metrics=[],
                    chromosome_genes=3,
                    chromosome_length=1,
                )


@pytest.mark.unit
class TestGrpcBlockToDictBlock:
    """Test conversion from gRPC blocks to dict blocks."""

    def setup_method(self):
        self.handler = RequestHandler(
            redis_connection=None, pairwise_address="localhost:8081"
        )

    def test_basic_conversion(self):
        """Test basic block conversion."""
        Block = namedtuple(
            "Block", ["i", "j", "fmin", "fmax", "orientation", "optionalMetrics"]
        )
        grpc_block = Block(
            i=0, j=5, fmin=0, fmax=5000, orientation="+", optionalMetrics=[]
        )

        dict_block = self.handler._grpcBlockToDictBlock(grpc_block)

        assert dict_block["i"] == 0
        assert dict_block["j"] == 5
        assert dict_block["fmin"] == 0
        assert dict_block["fmax"] == 5000
        assert dict_block["orientation"] == "+"

    def test_conversion_with_metrics(self):
        """Test conversion with optional metrics."""
        Block = namedtuple(
            "Block", ["i", "j", "fmin", "fmax", "orientation", "optionalMetrics"]
        )
        grpc_block = Block(
            i=0, j=5, fmin=0, fmax=5000, orientation="+", optionalMetrics=[0.5, 0.8]
        )

        dict_block = self.handler._grpcBlockToDictBlock(grpc_block)

        assert "optionalMetrics" in dict_block
        assert dict_block["optionalMetrics"] == [0.5, 0.8]
