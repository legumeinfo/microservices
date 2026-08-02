import json
import tempfile
import unittest
from pathlib import Path

import networkx as nx

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


# A child node that declares the ANNOTATION as its own parent. Its presence makes
# the annotation an "intermediate" node (both a child of the genome and a parent
# of this node), which is what triggered the load-order-dependent edge-dropping
# bug in generate_digraph.
GENES_SUMMARY_NODE = {
    "filename": "glyma.Wm82.gnm2.ann1.genes",
    "filetype": "genes_summary",
    "canonical_type": "genes_summary",
    "url": "https://example.org/glyma.Wm82.gnm2.ann1.genes.tsv.gz",
    "counts": {},
    "genus": "Glycine",
    "species": "max",
    "origin": "LIS",
    "infraspecies": "Wm82",
    "derived_from": ["glyma.Wm82.gnm2.ann1"],
}


def _write_fixture(tmpdir, *nodes):
    for node in nodes:
        path = Path(tmpdir) / f"{node['filename']}.json"
        path.write_text(json.dumps(node))


def _files_for_load_order(nodes):
    """Return files_for_prefix for the annotation when nodes are loaded in the
    given order. `generate_digraph` iterates `all_objects` in insertion (glob)
    order, so forcing the dict order reproduces a specific filesystem glob order
    deterministically — glob() order is otherwise not controllable in a test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_fixture(tmpdir, *nodes)
        handler = RequestHandler(tmpdir)
        controller = handler.controller
        controller.all_objects = {
            node["filename"]: controller.all_objects[node["filename"]] for node in nodes
        }
        controller.digraph = nx.DiGraph()
        controller.generate_digraph()
        return handler.files_for_prefix("glyma.Wm82.gnm2.ann1")


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
        self.assertEqual(result["genome_url"], GENOME_NODE["url"])


class TestGraphBuildOrderIndependence(unittest.TestCase):
    """The annotation is both a child (of the genome) and a parent (of the
    genes_summary), so its own genome edge must be built regardless of the order
    nodes are loaded in. Previously the edge was dropped when a child node was
    loaded before it, nulling genome_url depending on filesystem glob order."""

    def test_genome_url_resolves_annotation_before_child(self):
        result = _files_for_load_order(
            [ANNOTATION_NODE, GENOME_NODE, GENES_SUMMARY_NODE]
        )
        self.assertEqual(result["genome_url"], GENOME_NODE["url"])

    def test_genome_url_resolves_child_before_annotation(self):
        # The worst-case order: the genes_summary child is loaded first, which
        # pre-adds the annotation as its parent. This is the order that used to
        # drop the annotation->genome edge and return genome_url=None.
        result = _files_for_load_order(
            [GENES_SUMMARY_NODE, ANNOTATION_NODE, GENOME_NODE]
        )
        self.assertEqual(result["genome_url"], GENOME_NODE["url"])


if __name__ == "__main__":
    unittest.main()
