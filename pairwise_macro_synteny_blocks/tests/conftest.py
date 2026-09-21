import fakeredis.aioredis
import pytest


@pytest.fixture
async def fakeredis_connection():
    """In-memory Redis for unit tests."""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.aclose()


@pytest.fixture
async def redis_with_chromosome(fakeredis_connection):
    """Fixture providing fakeredis with sample chromosome data."""
    redis = fakeredis_connection

    # Populate with sample chromosome
    target = "test_chr"
    await redis.hset(
        f"chromosome:{target}",
        mapping={
            "name": target,
            "genus": "Test",
            "species": "species",
            "length": "10000",
        },
    )

    # Gene families on the chromosome
    families = ["fam1", "fam2", "fam3", "fam4", "fam5", "fam6", "fam7", "fam8"]
    await redis.rpush(f"chromosome:{target}:families", *families)

    # Gene names
    genes = [f"gene{i}" for i in range(1, 9)]
    await redis.rpush(f"chromosome:{target}:genes", *genes)

    # Gene positions (fmin)
    fmins = ["0", "1000", "2000", "3000", "4000", "5000", "6000", "7000"]
    await redis.rpush(f"chromosome:{target}:fmins", *fmins)

    # Gene positions (fmax)
    fmaxs = ["999", "1999", "2999", "3999", "4999", "5999", "6999", "7999"]
    await redis.rpush(f"chromosome:{target}:fmaxs", *fmaxs)

    yield redis


@pytest.fixture
async def redis_with_multiple_chromosomes(fakeredis_connection):
    """Fixture providing fakeredis with multiple chromosomes."""
    redis = fakeredis_connection

    # Create two chromosomes with different characteristics
    for chr_id, (length, num_genes) in [("chr1", (10000, 8)), ("chr2", (5000, 4))]:
        await redis.hset(
            f"chromosome:{chr_id}",
            mapping={
                "name": chr_id,
                "genus": "Test",
                "species": "species",
                "length": str(length),
            },
        )

        families = [f"fam{i}" for i in range(1, num_genes + 1)]
        await redis.rpush(f"chromosome:{chr_id}:families", *families)

        genes = [f"gene{chr_id}_{i}" for i in range(1, num_genes + 1)]
        await redis.rpush(f"chromosome:{chr_id}:genes", *genes)

        fmins = [str(i * 1000) for i in range(num_genes)]
        await redis.rpush(f"chromosome:{chr_id}:fmins", *fmins)

        fmaxs = [str(i * 1000 + 999) for i in range(num_genes)]
        await redis.rpush(f"chromosome:{chr_id}:fmaxs", *fmaxs)

    yield redis
