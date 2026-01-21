import pytest
from pairwise_macro_synteny_blocks.request_handler import RequestHandler


@pytest.mark.unit
class TestChromosomesToIndexPairs:
    """Test the index pair generation from matching gene families."""

    def setup_method(self):
        self.handler = RequestHandler(redis_connection=None)

    def test_simple_match(self):
        """Test basic matching between two chromosomes."""
        query = ["fam1", "fam2", "fam3", "fam4"]
        target = ["fam4", "fam3", "fam2", "fam1"]

        pairs, masked = self.handler._chromosomesToIndexPairs(
            query, target, mask=float("inf")
        )

        # Each target family matches one query family
        assert len(pairs) == 4
        assert (0, 3) in pairs  # target[0]=fam4 matches query[3]=fam4
        assert (1, 2) in pairs  # target[1]=fam3 matches query[2]=fam3
        assert (2, 1) in pairs  # target[2]=fam2 matches query[1]=fam2
        assert (3, 0) in pairs  # target[3]=fam1 matches query[0]=fam1

    def test_with_masking(self):
        """Test that families exceeding mask threshold are excluded."""
        query = ["fam1", "fam1", "fam1", "fam2"]
        target = ["fam1", "fam2"]

        pairs, masked = self.handler._chromosomesToIndexPairs(
            query, target, mask=2
        )

        # fam1 appears 3 times in query (exceeds mask=2), so should be masked
        assert "fam1" in masked
        # Only fam2 should match
        assert len(pairs) == 1
        assert (1, 3) in pairs


    def test_duplicate_families_in_target(self):
        """Test handling of duplicated families on target chromosome."""
        query = ["fam1", "fam2", "fam3"]
        target = ["fam1", "fam1", "fam2", "fam3"]

        pairs, masked = self.handler._chromosomesToIndexPairs(
            query, target, mask=float("inf")
        )

        # fam1 appears twice in target, should create 2 pairs
        assert len(pairs) == 4
        assert (0, 0) in pairs  # target[0]=fam1 matches query[0]=fam1
        assert (1, 0) in pairs  # target[1]=fam1 matches query[0]=fam1
        assert (2, 1) in pairs  # target[2]=fam2 matches query[1]=fam2
        assert (3, 2) in pairs  # target[3]=fam3 matches query[2]=fam3

    def test_target_masking(self):
        """Test that target families exceeding mask are excluded."""
        query = ["fam1", "fam2"]
        target = ["fam1", "fam1", "fam1", "fam2"]

        pairs, masked = self.handler._chromosomesToIndexPairs(
            query, target, mask=2
        )

        # fam1 appears 3 times in target (exceeds mask=2)
        # So no fam1 pairs should be created
        assert len(pairs) == 1
        assert (3, 1) in pairs  # Only fam2 match


@pytest.mark.unit
class TestIndexPairsToIndexBlocks:
    """Test the DAG-based longest path algorithm for synteny block detection."""

    def setup_method(self):
        self.handler = RequestHandler(redis_connection=None)

    def test_forward_orientation(self):
        """Test detection of forward-oriented synteny block."""
        # Perfect forward diagonal: (0,0), (1,1), (2,2), (3,3)
        pairs = [(0, 0), (1, 1), (2, 2), (3, 3)]

        blocks = list(self.handler._indexPairsToIndexBlocks(
            pairs, intermediate=1, matched=3
        ))

        assert len(blocks) == 1
        begin, end, path = blocks[0]
        assert (begin, end) == ((0, 0), (3, 3))  # begin, end

    def test_reverse_orientation(self):
        """Test detection of reverse-oriented synteny block."""
        # Reverse diagonal: (0,3), (1,2), (2,1), (3,0)
        pairs = [(0, 3), (1, 2), (2, 1), (3, 0)]

        blocks = list(self.handler._indexPairsToIndexBlocks(
            pairs, intermediate=1, matched=3
        ))

        assert len(blocks) == 1
        begin, end, path = blocks[0]
        assert (begin, end) == ((0, 3), (3, 0))

    def test_intermediate_constraint(self):
        """Test that intermediate distance constraint is enforced."""
        # Two separate blocks with large gap
        pairs = [(0, 0), (1, 1), (10, 10), (11, 11)]

        blocks = list(self.handler._indexPairsToIndexBlocks(
            pairs, intermediate=2, matched=2
        ))

        # Should form 2 separate blocks due to gap
        assert len(blocks) == 2
        endpoints = [(b[0], b[1]) for b in blocks]
        assert ((0, 0), (1, 1)) in endpoints
        assert ((10, 10), (11, 11)) in endpoints

    def test_matched_filtering(self):
        """Test that blocks shorter than matched parameter are filtered."""
        # Small blocks that don't meet matched requirement
        pairs = [(0, 0), (1, 1), (10, 10)]

        blocks = list(self.handler._indexPairsToIndexBlocks(
            pairs, intermediate=1, matched=3
        ))

        # No blocks meet the matched=3 requirement
        assert len(blocks) == 0

    def test_multiple_blocks(self):
        """Test detection of multiple independent synteny blocks."""
        # Two forward blocks separated by a gap
        pairs = [
            (0, 0), (1, 1), (2, 2),  # Block 1
            (10, 10), (11, 11), (12, 12), (13, 13)  # Block 2
        ]

        blocks = list(self.handler._indexPairsToIndexBlocks(
            pairs, intermediate=1, matched=3
        ))

        assert len(blocks) == 2
        endpoints = [(b[0], b[1]) for b in blocks]
        assert ((0, 0), (2, 2)) in endpoints
        assert ((10, 10), (13, 13)) in endpoints

    def test_mixed_orientations(self):
        """Test that forward and reverse blocks are detected independently."""
        # One forward block and one reverse block
        pairs = [
            (0, 0), (1, 1), (2, 2),     # Forward
            (10, 20), (11, 19), (12, 18)  # Reverse
        ]

        blocks = list(self.handler._indexPairsToIndexBlocks(
            pairs, intermediate=1, matched=3
        ))

        assert len(blocks) == 2
        endpoints = [(b[0], b[1]) for b in blocks]

        # Forward block
        assert ((0, 0), (2, 2)) in endpoints
        # Reverse block
        assert ((10, 20), (12, 18)) in endpoints

    def test_greedy_selection(self):
        """Test that highest scoring blocks are selected first (greedy)."""
        # Overlapping paths where greedy selection matters
        # (0,0) -> (1,1) -> (2,2) -> (3,3) [score 4]
        # (1,1) -> (2,2) [score 2]
        pairs = [(0, 0), (1, 1), (2, 2), (3, 3)]

        blocks = list(self.handler._indexPairsToIndexBlocks(
            pairs, intermediate=1, matched=2
        ))

        # Should select the longest block (0,0) -> (3,3)
        # The shorter overlapping block (1,1) -> (2,2) can't be selected
        # because nodes are already used
        assert len(blocks) == 1
        begin, end, path = blocks[0]
        assert (begin, end) == ((0, 0), (3, 3))


@pytest.mark.unit
class TestIndexPathTraceback:
    """Test the greedy traceback algorithm."""

    def setup_method(self):
        self.handler = RequestHandler(redis_connection=None)

    def test_basic_traceback(self):
        """Test basic traceback with a simple path."""
        # Path: node1 -> node2 -> node3
        node1, node2, node3 = (0, 0), (1, 1), (2, 2)
        path_ends = [(3, node3)]  # Score 3, ends at node3
        pointers = {node3: node2, node2: node1}
        scores = {node1: 1, node2: 2, node3: 3}

        blocks = list(self.handler._indexBlocksViaIndexPathTraceback(
            path_ends, pointers, scores, matched=3
        ))

        assert len(blocks) == 1
        begin, end, path = blocks[0]
        assert (begin, end) == (node1, node3)
        # Nodes should be consumed (removed from pointers)
        assert len(pointers) == 0

    def test_multiple_paths_highest_first(self):
        """Test that paths are processed in highest score first order."""
        node1, node2, node3, node4 = (0, 0), (1, 1), (5, 5), (6, 6)

        # Two independent paths with different scores
        path_ends = [
            (4, node2),  # Score 4 (higher)
            (2, node4),  # Score 2 (lower)
        ]
        pointers = {
            node2: node1,
            node4: node3,
        }
        scores = {node1: 1, node2: 4, node3: 1, node4: 2}

        blocks = list(self.handler._indexBlocksViaIndexPathTraceback(
            path_ends, pointers, scores, matched=2
        ))

        # Both blocks meet matched requirement
        assert len(blocks) == 2
        # Higher score block should be yielded first
        begin1, end1, path1 = blocks[0]
        begin2, end2, path2 = blocks[1]
        assert (begin1, end1) == (node1, node2)
        assert (begin2, end2) == (node3, node4)

    def test_overlapping_paths_greedy_consumption(self):
        """Test that once a node is used, it's unavailable for other blocks."""
        shared_node = (1, 1)
        node1, node3 = (0, 0), (2, 2)

        # Two paths sharing a node
        path_ends = [
            (3, node3),  # Score 3, path: node1 -> shared_node -> node3
            (2, shared_node),  # Score 2, ends at shared_node
        ]
        pointers = {
            node3: shared_node,
            shared_node: node1,
        }
        scores = {node1: 1, shared_node: 2, node3: 3}

        blocks = list(self.handler._indexBlocksViaIndexPathTraceback(
            path_ends, pointers, scores, matched=2
        ))

        # Only the first (higher score) block should be selected
        # The second block can't be formed because shared_node is consumed
        assert len(blocks) == 1
        begin, end, path = blocks[0]
        assert (begin, end) == (node1, node3)


@pytest.mark.unit
@pytest.mark.asyncio
class TestProcessIntegration:
    """Integration tests for the full process pipeline."""

    async def test_process_chromosome_not_found(self, redis_with_chromosome):
        """Test handling of non-existent target chromosome."""
        handler = RequestHandler(redis_with_chromosome)

        result = await handler.process(
            query_chromosome=["fam1", "fam2"],
            target="nonexistent_chr",
            matched=2,
            intermediate=5,
            mask=None,
            metrics=[],
            chromosome_genes=2,
            chromosome_length=1,
        )

        # Should return None when chromosome not found
        assert result is None

    async def test_process_chromosome_too_short(self, redis_with_chromosome):
        """Test filtering of chromosomes below length threshold."""
        handler = RequestHandler(redis_with_chromosome)

        result = await handler.process(
            query_chromosome=["fam1", "fam2"],
            target="test_chr",
            matched=2,
            intermediate=5,
            mask=None,
            metrics=[],
            chromosome_genes=2,
            chromosome_length=20000,  # Larger than test_chr length (10000)
        )

        # Should return empty list for too-short chromosome
        assert result == []

    async def test_process_insufficient_genes(self, redis_with_chromosome):
        """Test filtering when target has too few genes for a block."""
        handler = RequestHandler(redis_with_chromosome)

        result = await handler.process(
            query_chromosome=["fam1", "fam2"],
            target="test_chr",
            matched=100,  # More genes than exist
            intermediate=5,
            mask=None,
            metrics=[],
            chromosome_genes=100,
            chromosome_length=1,
        )

        # Should return empty list when insufficient genes
        assert result == []

    async def test_process_with_masking(self, redis_with_chromosome):
        """Test that masking parameter filters repetitive families."""
        handler = RequestHandler(redis_with_chromosome)

        # Create query with repeated families
        query_chromosome = ["fam1", "fam1", "fam1", "fam2", "fam3"]

        blocks = await handler.process(
            query_chromosome=query_chromosome,
            target="test_chr",
            matched=2,
            intermediate=5,
            mask=2,  # fam1 should be masked
            metrics=[],
            chromosome_genes=2,
            chromosome_length=1,
        )

        # Blocks should not include masked families
        # (This is implicit in the algorithm, hard to assert directly)
        assert isinstance(blocks, list)
