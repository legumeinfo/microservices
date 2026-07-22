from collections import namedtuple

import pytest

# Mock gRPC objects
Gene = namedtuple("Gene", ["name", "fmin", "fmax"])
Chromosome = namedtuple("Chromosome", ["name", "genus", "species", "length", "track"])
Track = namedtuple("Track", ["genes"])
Block = namedtuple(
    "Block", ["i", "j", "fmin", "fmax", "orientation", "queryGeneFmin", "queryGeneFmax"]
)
Blocks = namedtuple(
    "Blocks", ["chromosome", "genus", "species", "blocks", "chromosomeLength"]
)


@pytest.fixture
def sample_blocks_with_enrichment():
    """Sample blocks with enrichment (queryGeneFmin, queryGeneFmax, chromosomeLength)."""
    Block = namedtuple(
        "Block",
        ["i", "j", "fmin", "fmax", "orientation", "queryGeneFmin", "queryGeneFmax"],
    )
    Blocks = namedtuple(
        "Blocks", ["chromosome", "genus", "species", "blocks", "chromosomeLength"]
    )

    return [
        Blocks(
            chromosome="target_chr1",
            genus="Target",
            species="species",
            chromosomeLength=10000,
            blocks=[
                Block(
                    i=0,
                    j=2,
                    fmin=0,
                    fmax=2999,
                    orientation="+",
                    queryGeneFmin=0,
                    queryGeneFmax=2999,
                ),
                Block(
                    i=3,
                    j=4,
                    fmin=3000,
                    fmax=4999,
                    orientation="-",
                    queryGeneFmin=3000,
                    queryGeneFmax=4999,
                ),
            ],
        ),
        Blocks(
            chromosome="target_chr2",
            genus="Target",
            species="species",
            chromosomeLength=8000,
            blocks=[
                Block(
                    i=1,
                    j=3,
                    fmin=1000,
                    fmax=3999,
                    orientation="+",
                    queryGeneFmin=1000,
                    queryGeneFmax=3999,
                ),
            ],
        ),
    ]


@pytest.fixture
def sample_blocks_without_enrichment():
    """Sample blocks without enrichment (legacy format)."""
    Block = namedtuple("Block", ["i", "j", "fmin", "fmax", "orientation"])
    Blocks = namedtuple("Blocks", ["chromosome", "genus", "species", "blocks"])

    return [
        Blocks(
            chromosome="target_chr1",
            genus="Target",
            species="species",
            blocks=[
                Block(i=0, j=2, fmin=0, fmax=2999, orientation="+"),
            ],
        ),
    ]
