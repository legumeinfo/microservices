# Pure helpers for assembling FASTA output and the strand-aware coordinate math
# the genome path needs. Ported from the web-components retrieve-sequence
# helpers (utils/sequence-fasta.ts) so the logic lives in exactly one place now
# that orchestration has moved server-side. Kept dependency-free and free of any
# I/O so it can be unit-tested in isolation.

# Cap on per-side flank length (matches the spec / web component: 10000 bp each).
MAX_FLANK_BASES = 10000

# Suffix appended to a gene yuck to address its primary mRNA in the LIS
# `*_primary.faa.gz` / `*_primary.fna.gz` FASTAs. The curation pipeline keys the
# canonical isoform by `<gene_id>.1`.
PRIMARY_MRNA_SUFFIX = ".1"

# Standard IUPAC complement table (case-preserving so soft-masked bases survive).
_COMPLEMENT = {
    "A": "T",
    "T": "A",
    "G": "C",
    "C": "G",
    "U": "A",
    "R": "Y",
    "Y": "R",
    "S": "S",
    "W": "W",
    "K": "M",
    "M": "K",
    "B": "V",
    "V": "B",
    "D": "H",
    "H": "D",
    "N": "N",
    "a": "t",
    "t": "a",
    "g": "c",
    "c": "g",
    "u": "a",
    "r": "y",
    "y": "r",
    "s": "s",
    "w": "w",
    "k": "m",
    "m": "k",
    "b": "v",
    "v": "b",
    "d": "h",
    "h": "d",
    "n": "n",
}


def extract_full_yuck_prefix(yuck):
    """Pull the LIS full-yuck annotation prefix (first four dot tokens) out of a
    gene yuck, e.g. `glyma.Wm82.gnm2.ann1` from
    `glyma.Wm82.gnm2.ann1.Glyma.08G002000`. dscensor indexes on this prefix."""
    parts = yuck.split(".")
    if len(parts) < 5:
        raise ValueError(
            f'Gene ID "{yuck}" is not in the expected '
            "gensp.infraspecies.gnm<N>.ann<N>.<suffix> shape."
        )
    return ".".join(parts[:4])


def clamp_flank(value):
    """Coerce a flank value to an integer in [0, MAX_FLANK_BASES]."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 0
    if n < 0:
        return 0
    return min(n, MAX_FLANK_BASES)


def reverse_complement(seq):
    """IUPAC reverse-complement; unknown characters pass through unchanged."""
    return "".join(_COMPLEMENT.get(base, base) for base in reversed(seq))


def compute_flank_region(start, end, strand, upstream, downstream):
    """Region to actually fetch given the gene's 0-based half-open coordinates
    and the requested +/- flank budget.

    For minus-strand genes (`strand == -1`) "upstream" sits at the high-
    coordinate end, so the budgets are swapped before being applied. Start is
    clamped at 0 (pysam half-open coords don't go negative)."""
    up = clamp_flank(upstream)
    down = clamp_flank(downstream)
    negative = strand == -1
    left_budget = down if negative else up
    right_budget = up if negative else down
    return max(0, start - left_budget), end + right_budget


def wrap_sequence(seq, width=60):
    """Wrap a sequence to the conventional FASTA line width (samtools faidx /
    NCBI default is 60). width <= 0 disables wrapping."""
    if width <= 0:
        return seq
    return "\n".join(seq[i : i + width] for i in range(0, len(seq), width))


def format_fasta(records, wrap_width=60):
    """Serialize (header, sequence) records into one FASTA string. Trailing
    newline is intentional (cat-friendly, matches FASTA writer convention)."""
    body = "\n".join(
        f">{header}\n{wrap_sequence(sequence, wrap_width)}"
        for header, sequence in records
    )
    return body + "\n" if records else ""


def strand_sign(strand):
    """Map the genes-service integer strand (1 / -1 / 0) to +/-/. for headers."""
    if strand == 1:
        return "+"
    if strand == -1:
        return "-"
    return "."
