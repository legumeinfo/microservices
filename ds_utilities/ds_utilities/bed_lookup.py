"""Domain helpers for the LIS 7-column gene_models BED schema.

Bioinformatics file handling (HTTPS streaming, BGZF decompression, tabix
index lookup, BED line splitting) lives in pysam — we don't reimplement
any of that. This module is just the LIS-specific schema knowledge that
sits above pysam's output: the field names for the 7 columns, the typed
row shape we surface as JSON, and the "longest variant" selection rule
from Steven's Jun 5 spec.
"""

from typing import List, Optional, TypedDict

# Field order of the LIS seven-column gene_models_main BED, per Steven
# Cannon (Jun 5, 2026). Columns 1-6 match the standard BED schema, but
# column 7 is the gene-ID rather than thickStart — which is why we read
# col 7 positionally rather than via the standard pysam.BedProxy.thickStart
# attribute (pysam would try to int-cast it).
LIS_BED_COLS = (
    "molecule",
    "start",
    "end",
    "mrna_id",
    "score",
    "strand",
    "gene_id",
)

# Columns we cast from pysam's string representation to int. `score` is
# always 0 by LIS convention, so an int cast surfaces a TypeError if the
# convention ever drifts rather than silently widening to a string.
LIS_BED_INT_COLS = frozenset(("start", "end", "score"))


class BedRow(TypedDict):
    """One row of a LIS seven-column gene_models_main BED, in JSON-ready form."""

    molecule: str
    start: int
    end: int
    mrna_id: str
    score: int
    strand: str
    gene_id: str


def select_longest(rows: List[BedRow]) -> Optional[BedRow]:
    """Return the single longest row by feature length, or None if empty.

    Implements Steven's "return one" mode for callers that want a
    representative transcript without surfacing the variant choice in the
    UI. On length ties, max() returns the first element in iteration order;
    LIS BEDs are coordinate-sorted, so the tie-break is deterministic and
    yields the upstream-most variant.
    """
    if not rows:
        return None
    return max(rows, key=lambda r: r["end"] - r["start"])
