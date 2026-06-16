import unittest

from ds_utilities.bed_lookup import BedRow, select_longest


def _row(start: int, end: int, mrna_id: str, gene_id: str = "g") -> BedRow:
    # Minimal LIS row used by the longest-selection tests — file parsing
    # itself is pysam's responsibility and not exercised here.
    return BedRow(
        molecule="chrom",
        start=start,
        end=end,
        mrna_id=mrna_id,
        score=0,
        strand="+",
        gene_id=gene_id,
    )


class TestSelectLongest(unittest.TestCase):

    def test_returns_longest_row(self):
        rows = [
            _row(100, 500, "a.1"),  # 400 bp
            _row(100, 800, "a.2"),  # 700 bp
            _row(100, 300, "a.3"),  # 200 bp
        ]
        result = select_longest(rows)
        self.assertIsNotNone(result)
        self.assertEqual(result["mrna_id"], "a.2")
        self.assertEqual(result["end"] - result["start"], 700)

    def test_breaks_ties_by_first_in_input(self):
        # On equal lengths max() yields the first iterated, giving the
        # deterministic upstream-most variant on LIS coordinate-sorted BEDs.
        tied = [_row(100, 200, "a.1"), _row(300, 400, "a.2")]
        self.assertEqual(select_longest(tied)["mrna_id"], "a.1")

    def test_returns_none_for_empty_input(self):
        self.assertIsNone(select_longest([]))


if __name__ == "__main__":
    unittest.main()
