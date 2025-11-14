import pytest
import hashlib
import json
from macro_synteny_paf.request_handler import RequestHandler
from collections import namedtuple


@pytest.mark.unit
class TestGenerateCacheKey:
    """Test cache key generation."""

    def setup_method(self):
        self.handler = RequestHandler(
            redis_connection=None,
            chromosome_address="localhost:8081",
            genes_address="localhost:8082",
            macrosyntenyblocks_address="localhost:8083"
        )

    def test_deterministic_key(self):
        """Test that same inputs produce same key."""
        key1 = self.handler._generate_cache_key(
            "genome1", "genome2", 10, 5, None, [], 10, 1, "paf"
        )
        key2 = self.handler._generate_cache_key(
            "genome1", "genome2", 10, 5, None, [], 10, 1, "paf"
        )

        assert key1 == key2

    def test_different_formats_different_keys(self):
        """Test that PAF and JSON formats have different cache keys."""
        key_paf = self.handler._generate_cache_key(
            "genome1", "genome2", 10, 5, None, [], 10, 1, "paf"
        )
        key_json = self.handler._generate_cache_key(
            "genome1", "genome2", 10, 5, None, [], 10, 1, "json"
        )

        assert key_paf != key_json

    def test_different_parameters_different_keys(self):
        """Test that different parameters produce different keys."""
        key1 = self.handler._generate_cache_key(
            "genome1", "genome2", 10, 5, None, [], 10, 1, "paf"
        )
        key2 = self.handler._generate_cache_key(
            "genome1", "genome2", 20, 5, None, [], 10, 1, "paf"  # Different matched
        )

        assert key1 != key2

    def test_metrics_order_independent(self):
        """Test that metrics list order doesn't affect key (sorted internally)."""
        key1 = self.handler._generate_cache_key(
            "genome1", "genome2", 10, 5, None, ["jaccard", "levenshtein"], 10, 1, "paf"
        )
        key2 = self.handler._generate_cache_key(
            "genome1", "genome2", 10, 5, None, ["levenshtein", "jaccard"], 10, 1, "paf"
        )

        assert key1 == key2

    def test_key_format(self):
        """Test that key has correct format with version prefix."""
        key = self.handler._generate_cache_key(
            "genome1", "genome2", 10, 5, None, [], 10, 1, "paf"
        )

        # Should start with version prefix
        assert key.startswith("synteny_cache:v2:")

        # Should be followed by SHA256 hash (64 hex chars)
        hash_part = key.split(":")[-1]
        assert len(hash_part) == 64
        assert all(c in "0123456789abcdef" for c in hash_part)

    def test_sha256_hash(self):
        """Test that the hash is valid SHA256."""
        key = self.handler._generate_cache_key(
            "genome1", "genome2", 10, 5, None, [], 10, 1, "paf"
        )

        hash_part = key.split(":")[-1]

        # Verify it's a valid SHA256 hash by checking length and hex format
        try:
            int(hash_part, 16)
            assert len(hash_part) == 64
        except ValueError:
            pytest.fail("Hash is not valid hexadecimal")

    def test_none_vs_mask_value(self):
        """Test that None mask produces different key than mask value."""
        key1 = self.handler._generate_cache_key(
            "genome1", "genome2", 10, 5, None, [], 10, 1, "paf"
        )
        key2 = self.handler._generate_cache_key(
            "genome1", "genome2", 10, 5, 10, [], 10, 1, "paf"
        )

        assert key1 != key2


@pytest.mark.unit
@pytest.mark.asyncio
class TestBlockToPafRow:
    """Test PAF format conversion."""

    def setup_method(self):
        self.handler = RequestHandler(
            redis_connection=None,
            chromosome_address="localhost:8081",
            genes_address="localhost:8082",
            macrosyntenyblocks_address="localhost:8083"
        )

    async def test_paf_format_with_enrichment(self):
        """Test PAF row generation with enriched gene info."""
        Block = namedtuple("Block", ["i", "j", "fmin", "fmax", "orientation", "queryGeneFmin", "queryGeneFmax"])
        block = Block(
            i=0, j=2, fmin=0, fmax=2999, orientation="+",
            queryGeneFmin=100, queryGeneFmax=2500
        )

        paf_row = await self.handler._blockToPafRow(
            query_chromosome_name="query_chr",
            query_chromosome_length=10000,
            target_chromosome_name="target_chr",
            target_chromosome_length=8000,
            target_block=block
        )

        # PAF format: qname qlen qstart qend strand tname tlen tstart tend matches alen mapq
        fields = paf_row.strip().split("\t")

        assert len(fields) == 12
        assert fields[0] == "query_chr"
        assert fields[1] == "10000"
        assert fields[2] == "100"  # queryGeneFmin
        assert fields[3] == "2500"  # queryGeneFmax
        assert fields[4] == "+"
        assert fields[5] == "target_chr"
        assert fields[6] == "8000"
        assert fields[7] == "0"  # target fmin
        assert fields[8] == "2999"  # target fmax

    async def test_paf_reverse_orientation(self):
        """Test PAF row with reverse orientation."""
        Block = namedtuple("Block", ["i", "j", "fmin", "fmax", "orientation", "queryGeneFmin", "queryGeneFmax"])
        block = Block(
            i=0, j=2, fmin=0, fmax=2999, orientation="-",
            queryGeneFmin=100, queryGeneFmax=2500
        )

        paf_row = await self.handler._blockToPafRow(
            query_chromosome_name="query_chr",
            query_chromosome_length=10000,
            target_chromosome_name="target_chr",
            target_chromosome_length=8000,
            target_block=block
        )

        fields = paf_row.strip().split("\t")
        assert fields[4] == "-"  # Strand field


@pytest.mark.unit
@pytest.mark.asyncio
class TestBlockToJson:
    """Test JSON format conversion."""

    def setup_method(self):
        self.handler = RequestHandler(
            redis_connection=None,
            chromosome_address="localhost:8081",
            genes_address="localhost:8082",
            macrosyntenyblocks_address="localhost:8083"
        )

    async def test_json_format_with_enrichment(self):
        """Test JSON object generation with enriched gene info."""
        Block = namedtuple("Block", ["i", "j", "fmin", "fmax", "orientation", "queryGeneFmin", "queryGeneFmax"])
        block = Block(
            i=0, j=2, fmin=0, fmax=2999, orientation="+",
            queryGeneFmin=100, queryGeneFmax=2500
        )

        json_obj = await self.handler._blockToJson(
            query_chromosome_name="query_chr",
            query_chromosome_length=10000,
            target_chromosome_name="target_chr",
            target_chromosome_length=8000,
            target_block=block
        )

        # Verify JSON structure
        assert "query" in json_obj
        assert "target" in json_obj
        assert "strand" in json_obj

        # Verify query fields
        assert json_obj["query"]["name"] == "query_chr"
        assert json_obj["query"]["length"] == 10000
        assert json_obj["query"]["start"] == 100
        assert json_obj["query"]["end"] == 2500

        # Verify target fields
        assert json_obj["target"]["name"] == "target_chr"
        assert json_obj["target"]["length"] == 8000
        assert json_obj["target"]["start"] == 0
        assert json_obj["target"]["end"] == 2999

        # Verify strand
        assert json_obj["strand"] == "+"

        # Verify optional fields
        assert "numResidueMatches" in json_obj
        assert "alignmentBlockLength" in json_obj
        assert "mappingQuality" in json_obj

    async def test_json_format_reverse_orientation(self):
        """Test JSON object with reverse orientation."""
        Block = namedtuple("Block", ["i", "j", "fmin", "fmax", "orientation", "queryGeneFmin", "queryGeneFmax"])
        block = Block(
            i=0, j=2, fmin=0, fmax=2999, orientation="-",
            queryGeneFmin=100, queryGeneFmax=2500
        )

        json_obj = await self.handler._blockToJson(
            query_chromosome_name="query_chr",
            query_chromosome_length=10000,
            target_chromosome_name="target_chr",
            target_chromosome_length=8000,
            target_block=block
        )

        assert json_obj["strand"] == "-"


@pytest.mark.unit
@pytest.mark.asyncio
class TestBlocksToPafRows:
    """Test batch conversion to PAF format."""

    def setup_method(self):
        self.handler = RequestHandler(
            redis_connection=None,
            chromosome_address="localhost:8081",
            genes_address="localhost:8082",
            macrosyntenyblocks_address="localhost:8083"
        )

    async def test_paf_rows_with_enriched_chromosome_length(self):
        """Test that enriched chromosomeLength is used."""
        Block = namedtuple("Block", ["i", "j", "fmin", "fmax", "orientation", "queryGeneFmin", "queryGeneFmax"])
        Blocks = namedtuple("Blocks", ["chromosome", "blocks", "chromosomeLength"])

        target_block = Blocks(
            chromosome="target_chr",
            chromosomeLength=8000,  # Enriched
            blocks=[
                Block(i=0, j=2, fmin=0, fmax=2999, orientation="+", queryGeneFmin=100, queryGeneFmax=2500),
            ]
        )

        paf_rows = await self.handler._blocksToPafRows(
            query_chromosome_name="query_chr",
            query_chromosome_length=10000,
            target_block=target_block
        )

        # Should use enriched chromosomeLength, not call chromosome service
        assert "8000" in paf_rows