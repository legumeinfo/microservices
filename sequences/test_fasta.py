import unittest

from sequences.fasta import (
    MAX_FLANK_BASES,
    clamp_flank,
    compute_flank_region,
    extract_full_yuck_prefix,
    format_fasta,
    reverse_complement,
    strand_sign,
    wrap_sequence,
)


class TestExtractFullYuckPrefix(unittest.TestCase):
    def test_extracts_first_four_tokens(self):
        self.assertEqual(
            extract_full_yuck_prefix("glyma.Wm82.gnm2.ann1.Glyma.08G002000"),
            "glyma.Wm82.gnm2.ann1",
        )

    def test_rejects_too_few_tokens(self):
        with self.assertRaises(ValueError):
            extract_full_yuck_prefix("glyma.Wm82.gnm2.ann1")


class TestReverseComplement(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(reverse_complement("ATGC"), "GCAT")

    def test_preserves_case(self):
        self.assertEqual(reverse_complement("atGC"), "GCat")

    def test_iupac_and_unknown_passthrough(self):
        self.assertEqual(reverse_complement("RYN"), "NRY")
        self.assertEqual(reverse_complement("ATXC"), "GXAT")

    def test_double_reverse_complement_is_identity(self):
        seq = "ACGTNacgtnRYSWKM"
        self.assertEqual(reverse_complement(reverse_complement(seq)), seq)


class TestClampFlank(unittest.TestCase):
    def test_clamps_range(self):
        self.assertEqual(clamp_flank(-5), 0)
        self.assertEqual(clamp_flank(10), 10)
        self.assertEqual(clamp_flank(MAX_FLANK_BASES + 1), MAX_FLANK_BASES)

    def test_invalid_is_zero(self):
        self.assertEqual(clamp_flank("abc"), 0)
        self.assertEqual(clamp_flank(None), 0)


class TestComputeFlankRegion(unittest.TestCase):
    def test_plus_strand(self):
        # start/end are already 0-based half-open
        self.assertEqual(compute_flank_region(100, 200, 1, 10, 20), (90, 220))

    def test_minus_strand_swaps_budgets(self):
        # upstream sits at the high-coordinate end for minus-strand genes
        self.assertEqual(compute_flank_region(100, 200, -1, 10, 20), (80, 210))

    def test_start_clamped_at_zero(self):
        self.assertEqual(compute_flank_region(5, 50, 1, 100, 0), (0, 50))

    def test_flanks_clamped_to_max(self):
        start, end = compute_flank_region(50000, 60000, 1, 999999, 999999)
        self.assertEqual(start, 50000 - MAX_FLANK_BASES)
        self.assertEqual(end, 60000 + MAX_FLANK_BASES)


class TestWrapSequence(unittest.TestCase):
    def test_wraps_at_width(self):
        self.assertEqual(wrap_sequence("AAAAA", 2), "AA\nAA\nA")

    def test_no_wrap_when_width_zero(self):
        self.assertEqual(wrap_sequence("AAAAA", 0), "AAAAA")

    def test_default_width_60(self):
        seq = "A" * 130
        lines = wrap_sequence(seq).split("\n")
        self.assertEqual([len(line) for line in lines], [60, 60, 10])


class TestFormatFasta(unittest.TestCase):
    def test_single_record(self):
        self.assertEqual(format_fasta([("h1", "ACGT")]), ">h1\nACGT\n")

    def test_multiple_records_concatenated(self):
        out = format_fasta([("h1", "AC"), ("h2", "GT")])
        self.assertEqual(out, ">h1\nAC\n>h2\nGT\n")

    def test_empty(self):
        self.assertEqual(format_fasta([]), "")

    def test_wraps_long_sequence(self):
        out = format_fasta([("h", "A" * 70)])
        self.assertEqual(out, ">h\n" + "A" * 60 + "\n" + "A" * 10 + "\n")


class TestStrandSign(unittest.TestCase):
    def test_signs(self):
        self.assertEqual(strand_sign(1), "+")
        self.assertEqual(strand_sign(-1), "-")
        self.assertEqual(strand_sign(0), ".")


if __name__ == "__main__":
    unittest.main()
