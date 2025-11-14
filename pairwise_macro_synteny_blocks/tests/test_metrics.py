"""
Unit tests for distance metrics used in synteny block analysis.

Tests Jaccard distance and Levenshtein distance calculations.
"""
import pytest
from pairwise_macro_synteny_blocks.metrics import jaccard, levenshtein


@pytest.mark.unit
class TestJaccardDistance:
    """Test Jaccard distance metric."""

    def test_identical_sequences(self):
        """Distance should be 0 for identical sequences."""
        a = ["fam1", "fam2", "fam3"]
        b = ["fam1", "fam2", "fam3"]

        distance = jaccard(a, b)

        assert distance == 0

    def test_completely_different(self):
        """Distance should be 1 for no overlap."""
        a = ["fam1", "fam2", "fam3"]
        b = ["fam4", "fam5", "fam6"]

        distance = jaccard(a, b)

        assert distance == 1

    def test_partial_overlap(self):
        """Distance should reflect partial overlap."""
        a = ["fam1", "fam2", "fam3"]
        b = ["fam2", "fam3", "fam4"]

        distance = jaccard(a, b)

        # Intersection: {fam2, fam3} = 2
        # Union: {fam1, fam2, fam3, fam4} = 4
        # Jaccard index = 2/4 = 0.5
        # Jaccard distance = 1 - 0.5 = 0.5
        assert distance == 0.5

    def test_with_2grams(self):
        """Test with n=2 (bigrams)."""
        a = ["fam1", "fam2", "fam3"]
        b = ["fam1", "fam2", "fam4"]

        distance = jaccard(a, b, n=2)

        # a 2-grams: [(fam1,fam2), (fam2,fam3)]
        # b 2-grams: [(fam1,fam2), (fam2,fam4)]
        # Intersection: {(fam1,fam2)} = 1
        # Union: {(fam1,fam2), (fam2,fam3), (fam2,fam4)} = 3
        # Distance = 1 - 1/3 = 2/3
        assert abs(distance - 2/3) < 0.001

    def test_with_3grams(self):
        """Test with n=3 (trigrams)."""
        a = ["fam1", "fam2", "fam3", "fam4"]
        b = ["fam1", "fam2", "fam3", "fam5"]

        distance = jaccard(a, b, n=3)

        # a 3-grams: [(fam1,fam2,fam3), (fam2,fam3,fam4)]
        # b 3-grams: [(fam1,fam2,fam3), (fam2,fam3,fam5)]
        # Intersection: {(fam1,fam2,fam3)} = 1
        # Union: 3
        # Distance = 1 - 1/3 = 2/3
        assert abs(distance - 2/3) < 0.001

    def test_n_larger_than_sequence(self):
        """When n > sequence length, should return 1."""
        a = ["fam1", "fam2"]
        b = ["fam1", "fam2"]

        distance = jaccard(a, b, n=5)

        # n=5 but sequences only have 2 elements
        assert distance == 1


    def test_with_reversals_bigrams(self):
        """Test reversals with n=2."""
        a = ["fam1", "fam2", "fam3"]
        b = ["fam3", "fam2", "fam1"]

        distance = jaccard(a, b, n=2, reversals=True)

        # a 2-grams: [(fam1,fam2), (fam2,fam3)]
        # b 2-grams: [(fam3,fam2), (fam2,fam1)]
        # With reversals: (fam1,fam2) == (fam2,fam1) and (fam2,fam3) == (fam3,fam2)
        assert distance == 0

    def test_with_multiset(self):
        """Test that multiset=True counts duplicates."""
        a = ["fam1", "fam1", "fam2"]
        b = ["fam1", "fam2", "fam2"]

        distance_no_multiset = jaccard(a, b, n=1, multiset=False)
        distance_with_multiset = jaccard(a, b, n=1, multiset=True)

        # Without multiset: {fam1, fam2} vs {fam1, fam2} -> distance = 0
        assert distance_no_multiset == 0

        # With multiset: {fam1:2, fam2:1} vs {fam1:1, fam2:2}
        # Intersection: min counts = {fam1:1, fam2:1} = 2
        # Union: max counts = {fam1:2, fam2:2} = 4
        # Distance = 1 - 2/4 = 0.5
        assert distance_with_multiset == 0.5

    def test_string_arguments(self):
        """Test that string arguments are correctly parsed."""
        a = ["fam1", "fam2"]
        b = ["fam1", "fam2"]

        # n as string
        distance = jaccard(a, b, n="2")
        assert isinstance(distance, float)

        # reversals as string
        distance = jaccard(a, b, reversals="True")
        assert isinstance(distance, float)

    def test_empty_sequences(self):
        """Test handling of empty sequences."""
        a = []
        b = ["fam1"]

        distance = jaccard(a, b, n=1)

        # Empty vs non-empty should give distance 1
        assert distance == 1


@pytest.mark.unit
class TestLevenshteinDistance:
    """Test Levenshtein edit distance metric."""

    def test_identical_sequences(self):
        """Distance should be 0 for identical sequences."""
        a = ["fam1", "fam2", "fam3"]
        b = ["fam1", "fam2", "fam3"]

        distance = levenshtein(a, b)

        assert distance == 0

    def test_single_substitution(self):
        """Distance should be 1 for single substitution."""
        a = ["fam1", "fam2", "fam3"]
        b = ["fam1", "fam4", "fam3"]  # fam2 -> fam4

        distance = levenshtein(a, b)

        assert distance == 1

    def test_single_insertion(self):
        """Distance should be 1 for single insertion."""
        a = ["fam1", "fam2"]
        b = ["fam1", "fam2", "fam3"]  # Inserted fam3

        distance = levenshtein(a, b)

        assert distance == 1

    def test_single_deletion(self):
        """Distance should be 1 for single deletion."""
        a = ["fam1", "fam2", "fam3"]
        b = ["fam1", "fam3"]  # Deleted fam2

        distance = levenshtein(a, b)

        assert distance == 1

    def test_multiple_operations(self):
        """Test distance with multiple edit operations."""
        a = ["fam1", "fam2", "fam3"]
        b = ["fam4", "fam1", "fam5"]  # sub + sub + sub = 3, or del + ins + ... = ?

        distance = levenshtein(a, b)

        # Should be 3 (all different positions)
        assert distance == 3

    def test_empty_to_nonempty(self):
        """Distance from empty to non-empty is length of non-empty."""
        a = []
        b = ["fam1", "fam2", "fam3"]

        distance = levenshtein(a, b)

        assert distance == 3

    def test_nonempty_to_empty(self):
        """Distance from non-empty to empty is length of non-empty."""
        a = ["fam1", "fam2"]
        b = []

        distance = levenshtein(a, b)

        assert distance == 2

    def test_both_empty(self):
        """Distance between two empty sequences is 0."""
        a = []
        b = []

        distance = levenshtein(a, b)

        assert distance == 0

    def test_completely_different(self):
        """Distance for completely different sequences."""
        a = ["fam1", "fam2", "fam3"]
        b = ["fam4", "fam5", "fam6"]

        distance = levenshtein(a, b)

        # All substitutions = 3
        assert distance == 3

    def test_longer_sequences(self):
        """Test with longer sequences."""
        a = ["fam1", "fam2", "fam3", "fam4", "fam5"]
        b = ["fam1", "fam2", "fam4", "fam5"]  # Deleted fam3

        distance = levenshtein(a, b)

        assert distance == 1

    def test_optimized_for_length_swap(self):
        """Test that algorithm swaps to optimize when b > a."""
        # Internally, algorithm swaps if lb > la for efficiency
        a = ["fam1", "fam2"]
        b = ["fam1", "fam2", "fam3", "fam4"]

        distance = levenshtein(a, b)

        # Should be 2 insertions
        assert distance == 2
