import pytest
import fakeredis.aioredis
import redis.asyncio as aioredis
import os
from unittest.mock import AsyncMock, MagicMock
from collections import namedtuple


@pytest.fixture
async def redis_connection():
    """Real Redis connection for integration tests (from compose.test.yml)."""
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))

    redis_conn = await aioredis.from_url(
        f"redis://{redis_host}:{redis_port}",
        decode_responses=True
    )

    yield redis_conn

    await redis_conn.aclose()


@pytest.fixture
async def fakeredis_connection():
    """In-memory Redis for unit tests."""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.aclose()


@pytest.fixture
async def redis_with_gene_index(fakeredis_connection):
    """Fixture providing fakeredis with gene index data for batching tests."""
    redis = fakeredis_connection

    # Create gene documents in the gene index
    # Simulate genes for multiple chromosomes with various families
    test_data = [
        # chr1 genes
        ("gene1_chr1", "fam1", "chr1", 0),
        ("gene2_chr1", "fam2", "chr1", 1),
        ("gene3_chr1", "fam3", "chr1", 2),
        ("gene4_chr1", "fam1", "chr1", 3),  # Duplicate family
        # chr2 genes
        ("gene1_chr2", "fam1", "chr2", 0),
        ("gene2_chr2", "fam4", "chr2", 1),
        ("gene3_chr2", "fam5", "chr2", 2),
        # chr3 genes - more matches
        ("gene1_chr3", "fam1", "chr3", 0),
        ("gene2_chr3", "fam2", "chr3", 1),
        ("gene3_chr3", "fam3", "chr3", 2),
        ("gene4_chr3", "fam1", "chr3", 3),
        ("gene5_chr3", "fam2", "chr3", 4),
    ]

    for gene_name, family, chromosome, index in test_data:
        # In fakeredis, we need to manually add documents for search
        # This is a simplified version - real implementation would use ft.add
        await redis.hset(f"gene:{gene_name}", mapping={
            "name": gene_name,
            "family": family,
            "chromosome": chromosome,
            "index": str(index),
        })

    # Create chromosome documents
    for chr_id in ["chr1", "chr2", "chr3"]:
        await redis.hset(f"chromosome:{chr_id}", mapping={
            "name": chr_id,
            "genus": "Test",
            "species": "species",
            "length": "10000",
        })

    yield redis


@pytest.fixture
async def redis_with_chromosomes(fakeredis_connection):
    """Fixture with chromosome data for enrichment tests."""
    redis = fakeredis_connection

    # Create chromosomes with gene families
    chromosomes = {
        "chr1": {
            "families": ["fam1", "fam2", "fam3", "fam4"],
            "genes": ["gene1", "gene2", "gene3", "gene4"],
            "length": 10000,
        },
        "chr2": {
            "families": ["fam1", "fam2", "fam5"],
            "genes": ["gene5", "gene6", "gene7"],
            "length": 8000,
        },
    }

    for chr_id, data in chromosomes.items():
        await redis.hset(f"chromosome:{chr_id}", mapping={
            "name": chr_id,
            "genus": "Test",
            "species": "species",
            "length": str(data["length"]),
        })

    yield redis


# Mock gRPC objects for testing
Gene = namedtuple("Gene", ["name", "fmin", "fmax"])


@pytest.fixture
def mock_genes_service():
    """Mock genes microservice gRPC client."""
    async def mock_getGenes(gene_names, address):
        # Return mock gene objects with positions
        # Position is based on the gene number in the name (e.g., "gene1" -> index 0, "gene3" -> index 2)
        genes = []
        for name in gene_names:
            # Extract the gene number from the name (e.g., "gene1" -> 1, "gene3" -> 3)
            gene_number = int(name.replace("gene", ""))
            # Calculate position based on gene number (gene1 at index 0, gene2 at index 1, etc.)
            gene_index = gene_number - 1
            genes.append(Gene(
                name=name,
                fmin=gene_index * 1000,
                fmax=gene_index * 1000 + 999
            ))
        return genes

    return mock_getGenes


@pytest.fixture
def mock_chromosome_service():
    """Mock chromosome microservice gRPC client."""
    async def mock_getChromosome(chromosome_name, address):
        # Return mock chromosome data: (families, gene_names, length)
        if chromosome_name == "test_chr":
            return (
                ["fam1", "fam2", "fam3", "fam4", "fam5"],
                ["gene1", "gene2", "gene3", "gene4", "gene5"],
                10000,
            )
        elif chromosome_name == "chr1":
            return (
                ["fam1", "fam2", "fam3"],
                ["gene1", "gene2", "gene3"],
                8000,
            )
        return None

    return mock_getChromosome


@pytest.fixture
def mock_pairwise_service():
    """Mock pairwise-macro-synteny-blocks gRPC client."""
    async def mock_computePairwise(chromosome, target, matched, intermediate, mask, metrics, chromosome_genes, chromosome_length, address):
        # Return mock blocks as dicts to allow dynamic attribute assignment
        # This simulates gRPC objects that can have attributes added
        class MockBlock:
            def __init__(self, i, j, fmin, fmax, orientation):
                self.i = i
                self.j = j
                self.fmin = fmin
                self.fmax = fmax
                self.orientation = orientation

        return [
            MockBlock(i=0, j=2, fmin=0, fmax=2999, orientation="+"),
            MockBlock(i=3, j=4, fmin=3000, fmax=4999, orientation="+"),
        ]

    return mock_computePairwise


@pytest.fixture
def sample_blocks():
    """Sample block data for testing enrichment."""
    # Blocks in dict format (as returned by process())
    return [
        {
            "chromosome": "chr1",
            "genus": "Test",
            "species": "species",
            "blocks": [
                {"i": 0, "j": 2, "fmin": 0, "fmax": 2999, "orientation": "+"},
                {"i": 3, "j": 4, "fmin": 3000, "fmax": 4999, "orientation": "-"},
            ]
        },
        {
            "chromosome": "chr2",
            "genus": "Test",
            "species": "species",
            "blocks": [
                {"i": 1, "j": 3, "fmin": 1000, "fmax": 3999, "orientation": "+"},
            ]
        },
    ]


@pytest.fixture
def sample_query_gene_names():
    """Sample query gene names for enrichment tests."""
    return ["gene1", "gene2", "gene3", "gene4", "gene5"]
