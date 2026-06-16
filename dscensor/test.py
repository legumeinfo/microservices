import json
import tempfile
import unittest
from pathlib import Path

from dscensor.request_handler import RequestHandler

ANNOTATION_NODE = {
    "filename": "glyma.Wm82.gnm2.ann1",
    "filetype": "gene_models_main",
    "canonical_type": "gene_models_main",
    "url": (
        "https://data.legumeinfo.org/Glycine/max/annotations/"
        "Wm82.gnm2.ann1.RVB6/glyma.Wm82.gnm2.ann1.RVB6."
        "gene_models_main.gff3.gz"
    ),
    "counts": {},
    "genus": "Glycine",
    "species": "max",
    "origin": "LIS",
    "infraspecies": "Wm82",
    "derived_from": ["glyma.Wm82.gnm2"],
}

GENOME_NODE = {
    "filename": "glyma.Wm82.gnm2",
    "filetype": "genome_main",
    "canonical_type": "genome_main",
    "url": (
        "https://data.legumeinfo.org/Glycine/max/genomes/"
        "Wm82.gnm2.DTC4/glyma.Wm82.gnm2.DTC4.genome_main.fna.gz"
    ),
    "counts": {},
    "genus": "Glycine",
    "species": "max",
    "origin": "LIS",
    "infraspecies": "Wm82",
    "derived_from": [],
}


def _write_fixture(tmpdir, *nodes):
    for node in nodes:
        path = Path(tmpdir) / f"{node['filename']}.json"
        path.write_text(json.dumps(node))


class TestFilesForPrefix(unittest.TestCase):

    def test_derives_protein_and_cds_urls_from_gff_url(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_fixture(tmpdir, ANNOTATION_NODE, GENOME_NODE)
            handler = RequestHandler(tmpdir)
            result = handler.files_for_prefix("glyma.Wm82.gnm2.ann1")

        self.assertEqual(
            result["protein_url"],
            "https://data.legumeinfo.org/Glycine/max/annotations/"
            "Wm82.gnm2.ann1.RVB6/glyma.Wm82.gnm2.ann1.RVB6."
            "protein_primary.faa.gz",
        )
        self.assertEqual(
            result["cds_url"],
            "https://data.legumeinfo.org/Glycine/max/annotations/"
            "Wm82.gnm2.ann1.RVB6/glyma.Wm82.gnm2.ann1.RVB6."
            "cds_primary.fna.gz",
        )
        self.assertEqual(
            result["bed_url"],
            "https://data.legumeinfo.org/Glycine/max/annotations/"
            "Wm82.gnm2.ann1.RVB6/glyma.Wm82.gnm2.ann1.RVB6."
            "gene_models_main.bed.gz",
        )

    def test_resolves_genome_url_via_derived_from_edge(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_fixture(tmpdir, ANNOTATION_NODE, GENOME_NODE)
            handler = RequestHandler(tmpdir)
            result = handler.files_for_prefix("glyma.Wm82.gnm2.ann1")

        self.assertEqual(result["genome_url"], GENOME_NODE["url"])
        self.assertEqual(result["genus"], "Glycine")
        self.assertEqual(result["species"], "max")
        self.assertEqual(result["infraspecies"], "Wm82")

    def test_returns_none_for_unknown_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_fixture(tmpdir, ANNOTATION_NODE, GENOME_NODE)
            handler = RequestHandler(tmpdir)
            self.assertIsNone(handler.files_for_prefix("nope.no.such.ann"))

    def test_returns_null_genome_url_when_parent_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_fixture(tmpdir, ANNOTATION_NODE)
            handler = RequestHandler(tmpdir)
            result = handler.files_for_prefix("glyma.Wm82.gnm2.ann1")

        self.assertIsNotNone(result)
        self.assertIsNone(result["genome_url"])
        self.assertIsNotNone(result["protein_url"])

    def test_returns_null_protein_cds_when_url_suffix_unexpected(self):
        node = dict(ANNOTATION_NODE)
        node["url"] = "https://example.org/weird/path.gff3"
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_fixture(tmpdir, node, GENOME_NODE)
            handler = RequestHandler(tmpdir)
            result = handler.files_for_prefix("glyma.Wm82.gnm2.ann1")

        self.assertIsNone(result["protein_url"])
        self.assertIsNone(result["cds_url"])
        self.assertIsNone(result["bed_url"])
        self.assertEqual(result["genome_url"], GENOME_NODE["url"])


if __name__ == "__main__":
    unittest.main()
