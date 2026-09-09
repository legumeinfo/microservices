"""Tests for the in-memory catalog controller and its HTTP endpoints.

No network and no real datastore: a small fixture catalog exercises the parsing,
the tri-state index status, and the whole-store queries that the node digraph
cannot answer.
"""

import asyncio
import json

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from dscensor.catalog import SUPPORTED_SCHEMA, CatalogController, CatalogError
from dscensor.http_server import routes

FIXTURE = {
    "schema": SUPPORTED_SCHEMA,
    "built_at": "2026-09-08T12:00:00Z",
    "source_commit": "abc123def456",
    "datastore_url": "https://data.legumeinfo.org",
    "stats": {"collections": 4},
    "collections": [
        {
            "path": "Glycine/max/genomes/Wm82.gnm4.4PTR",
            "id": "Wm82.gnm4.4PTR",
            "type": "genomes",
            "genus": "Glycine",
            "species": "max",
            "base_url": "https://data.legumeinfo.org/Glycine/max/genomes/Wm82.gnm4.4PTR",
            "index_status": "known",
            "taxid": 3847,
            "publication_doi": "10.1111/tpj.14500",
            "chromosome_prefix": "Gm",
            "files": [
                {
                    "n": "glyma.Wm82.gnm4.4PTR.genome_main.fna.gz",
                    "i": [".fai"],
                    "description": "Genome assembly",
                }
            ],
        },
        {
            "path": "Glycine/max/genomes/58-161.gnm1.BW8J",
            "id": "58-161.gnm1.BW8J",
            "type": "genomes",
            "genus": "Glycine",
            "species": "max",
            "base_url": "https://data.legumeinfo.org/Glycine/max/genomes/58-161.gnm1.BW8J",
            "index_status": "known",
            "files": [],
        },
        {
            "path": "Glycine/max/annotations/Wm82.gnm4.ann1.T8TQ",
            "id": "Wm82.gnm4.ann1.T8TQ",
            "type": "annotations",
            "genus": "Glycine",
            "species": "max",
            "base_url": "https://data.legumeinfo.org/Glycine/max/annotations/Wm82.gnm4.ann1.T8TQ",
            "index_status": "known",
            "publication_doi": "10.1111/tpj.14500",
            "publication_title": "Three reference-quality genome assemblies",
            "derived_from": ["Wm82.gnm4.4PTR"],
            "files": [{"n": "glyma...protein_primary.faa.gz", "i": [".fai"]}],
        },
        {
            "path": "Glycine/max/qtl/Demo.qtl.X_1990",
            "id": "Demo.qtl.X_1990",
            "type": "qtl",
            "genus": "Glycine",
            "species": "max",
            "base_url": "https://data.legumeinfo.org/Glycine/max/qtl/Demo.qtl.X_1990",
            "index_status": "unknown",
            "publication_doi": "10.1007/bf00226154",
            "files": [],
        },
        {
            "path": "Phaseolus/vulgaris/diversity/G19833.gnm1.div.X",
            "id": "G19833.gnm1.div.X",
            "type": "diversity",
            "genus": "Phaseolus",
            "species": "vulgaris",
            "base_url": "https://data.legumeinfo.org/Phaseolus/vulgaris/diversity/G19833.gnm1.div.X",
            "index_status": "known",
            "files": [],
        },
        {
            "path": "Phaseolus/vulgaris/expression/G19833.gnm1.expr.X",
            "id": "G19833.gnm1.expr.X",
            "type": "expression",
            "genus": "Phaseolus",
            "species": "vulgaris",
            "base_url": "https://data.legumeinfo.org/Phaseolus/vulgaris/expression/G19833.gnm1.expr.X",
            "index_status": "known",
            "files": [],
        },
    ],
}


@pytest.fixture
def catalog_file(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(FIXTURE), encoding="UTF-8")
    return str(path)


@pytest.fixture
def catalog(catalog_file):
    return CatalogController(catalog_file)


# --- loading -----------------------------------------------------------------
def test_no_catalog_is_a_valid_state():
    """The catalog is optional; the node endpoints must work without one."""
    empty = CatalogController()
    assert empty.loaded is False
    assert empty.provenance()["loaded"] is False


def test_loads_and_indexes(catalog):
    assert catalog.loaded is True
    assert len(catalog.collections) == 6
    assert catalog.get_collection("Glycine/max/genomes/Wm82.gnm4.4PTR")["taxid"] == 3847


def test_unsupported_schema_is_refused(tmp_path):
    """Fields move between versions; guessing at an unknown schema is worse than
    refusing, because the failure would be silent and downstream."""
    path = tmp_path / "future.json"
    path.write_text(json.dumps({"schema": 99, "collections": []}), encoding="UTF-8")
    with pytest.raises(CatalogError, match="schema"):
        CatalogController(str(path))


def test_missing_file_raises_catalog_error(tmp_path):
    with pytest.raises(CatalogError, match="no catalog"):
        CatalogController(str(tmp_path / "absent.json"))


def test_provenance_carries_the_build_stamp(catalog):
    prov = catalog.provenance()
    assert prov["source_commit"] == "abc123def456"
    assert prov["built_at"] == "2026-09-08T12:00:00Z"


# --- whole-store queries -----------------------------------------------------
def test_species_with_requires_every_type(catalog):
    """The co-availability question crawling cannot answer."""
    both = catalog.species_with(["diversity", "expression"])
    assert [(s["genus"], s["species"]) for s in both] == [("Phaseolus", "vulgaris")]
    assert catalog.species_with(["diversity", "gwas"]) == []


def test_list_types_counts_by_scope(catalog):
    assert catalog.list_types(genus="Glycine") == {
        "annotations": 1,
        "genomes": 2,
        "qtl": 1,
    }


def test_assemblies_list_without_metrics_and_say_so(catalog):
    """Ranking is deferred with the assembly metrics (see the NOTE in catalog.py).

    The important property while deferred is honesty: the rows must not carry
    metric keys they cannot fill, and `assemblies_are_ranked()` must report False
    so a caller never presents catalog order as a quality ordering.
    """
    rows = catalog.rank_assemblies(genus="Glycine", species="max")
    assert {r["id"] for r in rows} == {"Wm82.gnm4.4PTR", "58-161.gnm1.BW8J"}
    assert all("busco_complete_pct" not in r for r in rows)
    assert all("contig_n50" not in r for r in rows)
    assert catalog.assemblies_are_ranked() is False


def test_lineage_walks_parents_and_collects_dois(catalog):
    result = catalog.lineage("Wm82.gnm4.ann1.T8TQ")
    assert result["found"] is True
    assert [c["id"] for c in result["chain"]] == [
        "Wm82.gnm4.ann1.T8TQ",
        "Wm82.gnm4.4PTR",
    ]
    # the annotation and its genome share a DOI; the bundle must dedupe
    assert result["dois"] == ["10.1111/tpj.14500"]


def test_lineage_reports_a_miss_rather_than_an_empty_chain(catalog):
    assert catalog.lineage("NoSuchThing")["found"] is False


def test_filters_compose(catalog):
    assert len(catalog.list_collections(genus="Glycine")) == 4
    assert (
        len(catalog.list_collections(genus="Glycine", collection_type="genomes")) == 2
    )
    assert len(catalog.list_collections(has_doi=True)) == 3
    assert len(catalog.list_collections(indexed_only=True)) == 2


# --- the tri-state that must not collapse ------------------------------------
def test_unknown_index_status_is_distinguished_from_no_indexes(catalog):
    """A collection with no CHECKSUM has an empty file list, but that says
    nothing about whether indexes exist. Reporting it as 'no indexes' would mark
    streamable data unreadable."""
    rows = {r["path"]: r for r in catalog.indexed_files(genus="Glycine")}
    assert rows["Glycine/max/qtl/Demo.qtl.X_1990"]["index_status"] == "unknown"
    assert rows["Glycine/max/qtl/Demo.qtl.X_1990"]["files"] == []
    assert "58-161" not in " ".join(rows)  # known + no indexed files -> omitted


def test_indexed_files_build_absolute_urls(catalog):
    rows = catalog.indexed_files(genus="Glycine", collection_type="genomes")
    entry = rows[0]["files"][0]
    assert entry["url"].startswith("https://data.legumeinfo.org/Glycine/max/genomes/")
    assert entry["indexes"] == [".fai"]


# --- HTTP surface ------------------------------------------------------------
# Driven through aiohttp's own test utilities under asyncio.run rather than an
# async-pytest plugin, so these tests add no dependency the service does not
# already have.


class _Handler:
    """Minimal stand-in for RequestHandler: the routes only touch .catalog."""

    def __init__(self, catalog):
        self.catalog = catalog


def _serve(catalog, coro):
    """Run `coro(client)` against an app wired to `catalog`."""

    async def run():
        app = web.Application()
        app.add_routes(routes)
        app["handler"] = _Handler(catalog)
        async with TestClient(TestServer(app)) as client:
            return await coro(client)

    return asyncio.run(run())


def test_meta_endpoint_reports_staleness(catalog):
    async def check(client):
        return await (await client.get("/meta")).json()

    body = _serve(catalog, check)
    assert body["loaded"] is True
    assert body["source_commit"] == "abc123def456"


def test_endpoints_envelope_the_build_stamp(catalog):
    """Every answer states which catalog produced it, so staleness is visible at
    the point of use rather than buried in a file nobody reads."""

    async def check(client):
        return await (await client.get("/assemblies?genus=Glycine&species=max")).json()

    body = _serve(catalog, check)
    assert body["catalog"]["source_commit"] == "abc123def456"
    assert body["count"] == 2
    # the endpoint must state that the order is not a ranking
    assert body["ranked"] is False


def test_endpoints_503_without_a_catalog():
    async def check(client):
        return (
            (await client.get("/collections")).status,
            (await client.get("/meta")).status,
        )

    collections_status, meta_status = _serve(CatalogController(), check)
    assert collections_status == 503
    # /meta still answers, so a client can discover *why* the others are down
    assert meta_status == 200


def test_species_with_requires_a_type_parameter(catalog):
    async def check(client):
        bad = (await client.get("/species-with")).status
        good = await (
            await client.get("/species-with?type=diversity,expression")
        ).json()
        return bad, good

    bad_status, body = _serve(catalog, check)
    assert bad_status == 400
    assert body["count"] == 1


def test_lineage_endpoint_404s_on_a_miss(catalog):
    async def check(client):
        return (await client.get("/lineage/NoSuchThing")).status

    assert _serve(catalog, check) == 404
