import json
import unittest
import urllib.error
import urllib.request

# Live integration tests. They require a running `sequences` instance (default
# http://localhost:8082) wired to running genes / dscensor / ds_utilities
# instances. Run the unit suite (test_fasta.py) for logic that needs no network.
#
#   GENES_ADDR=localhost:8081 DSCENSOR_URL=http://localhost:8765 \
#   DS_UTILITIES_URL=http://localhost:8080 sequences --host 0.0.0.0 --port 8082
#
# The expected sequences depend on the loaded datastore, so these assert
# structural FASTA invariants rather than exact bytes.

BASE = "http://localhost:8082"

# Two genes from the same assembly (one dscensor prefix) plus the soybean
# example used throughout the retrieve-sequence work.
GENE_A = "glyma.Wm82.gnm2.ann1.Glyma.08G002000"
GENE_B = "glyma.Wm82.gnm2.ann1.Glyma.08G003000"


class TestSequencesEndpoints(unittest.TestCase):
    def fetch(self, path, data=None):
        """Return (status, body_text). data!=None issues a JSON POST."""
        url = f"{BASE}{path}"
        headers = {}
        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    def assertFastaWithRecords(self, text, n):
        self.assertTrue(text.startswith(">"), "FASTA must start with a header")
        self.assertTrue(text.endswith("\n"), "FASTA should end with a newline")
        self.assertEqual(text.count(">"), n, f"expected {n} records")

    def test_protein_get_multiple(self):
        status, text = self.fetch(f"/seq/{GENE_A},{GENE_B}?type=protein")
        self.assertEqual(status, 200)
        self.assertFastaWithRecords(text, 2)
        self.assertIn(f"gene={GENE_A}", text)
        self.assertIn(f"gene={GENE_B}", text)

    def test_cds_get_single(self):
        status, text = self.fetch(f"/seq/{GENE_A}?type=cds")
        self.assertEqual(status, 200)
        self.assertFastaWithRecords(text, 1)
        self.assertIn("cds", text.splitlines()[0])

    def test_genome_get_with_flanks(self):
        status, text = self.fetch(f"/seq/{GENE_A}?type=genome&up=100&down=50")
        self.assertEqual(status, 200)
        self.assertFastaWithRecords(text, 1)
        self.assertIn("genome", text.splitlines()[0])
        self.assertIn("flanks=100/50", text.splitlines()[0])

    def test_post_list(self):
        status, text = self.fetch(
            "/seq", data={"yucks": [GENE_A, GENE_B], "type": "protein"}
        )
        self.assertEqual(status, 200)
        self.assertFastaWithRecords(text, 2)

    def test_unknown_gene_fails_whole_request(self):
        status, _ = self.fetch(
            f"/seq/{GENE_A},glyma.Wm82.gnm2.ann1.Glyma.NOPE?type=protein"
        )
        self.assertIn(status, (400, 404))

    def test_malformed_gene_id_rejected(self):
        status, _ = self.fetch("/seq/not-a-yuck?type=protein")
        self.assertEqual(status, 400)

    def test_invalid_type_rejected(self):
        status, _ = self.fetch(f"/seq/{GENE_A}?type=bogus")
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
