"""Whole-store catalog, held in memory and queried directly.

The node digraph in :mod:`dscensor.directed_graph` answers "tell me about this
object". This module answers the complementary question -- "what exists across
the whole store, and how does it relate?" -- which needs the complete catalog
resident rather than a per-object lookup.

The document comes from ``lis-autocontent populate-catalog``: one JSON file
covering every collection, built from a datastore-metadata checkout with no
network access. Loading it is optional; when no catalog is configured the
service behaves exactly as before.

Two invariants callers depend on:

* ``index_status`` is tri-state. ``"known"`` means the collection published a
  CHECKSUM and the file list is authoritative. ``"unknown"`` means it did not,
  so an empty ``files`` list says nothing about whether indexes exist. Treating
  those the same reports streamable data as unreadable.
* Every response carries the catalog's build provenance. A consumer reasoning
  over a catalog built weeks ago must be able to see that it is doing so.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Iterable, Optional

# The schema this build understands. A catalog declaring anything else is
# refused rather than parsed on a guess -- fields move between versions, and a
# silently mis-read catalog is worse than no catalog.
SUPPORTED_SCHEMA = 1


class CatalogError(Exception):
    """Raised when a catalog cannot be loaded or is a version we cannot read."""


class CatalogController:
    """Load a catalog document and answer whole-store questions about it."""

    def __init__(self, catalog_path: Optional[str] = None):
        self.catalog_path = os.path.abspath(catalog_path) if catalog_path else None
        self.document: dict[str, Any] = {}
        self.collections: list[dict[str, Any]] = []
        self._by_path: dict[str, dict[str, Any]] = {}
        self._by_id: dict[str, list[dict[str, Any]]] = {}
        if self.catalog_path:
            self.load()

    # ---------------------------------------------------------------- loading
    @property
    def loaded(self) -> bool:
        """Whether a catalog is available to answer queries."""
        return bool(self.collections)

    def load(self) -> None:
        """Read and index the catalog document."""
        path = self.catalog_path
        logging.info(f"Loading catalog from: {path}...")
        try:
            with open(path, encoding="UTF-8") as handle:
                document = json.load(handle)
        except FileNotFoundError as err:
            raise CatalogError(f"no catalog at {path}") from err
        except (OSError, ValueError) as err:
            raise CatalogError(f"could not read catalog at {path}: {err}") from err

        schema = document.get("schema")
        if schema != SUPPORTED_SCHEMA:
            raise CatalogError(
                f"catalog schema {schema!r} is not supported "
                f"(this build reads schema {SUPPORTED_SCHEMA})"
            )

        self.document = document
        self.collections = document.get("collections", [])
        self._by_path = {c["path"]: c for c in self.collections}
        self._by_id = {}
        for collection in self.collections:
            self._by_id.setdefault(collection["id"], []).append(collection)
        logging.info(
            f"Loaded {len(self.collections)} collections "
            f"from catalog built {document.get('built_at')} "
            f"@ {str(document.get('source_commit'))[:8]}"
        )

    # --------------------------------------------------------------- metadata
    def provenance(self) -> dict[str, Any]:
        """Build stamp for the loaded catalog.

        Returned alongside every query result so staleness is visible at the
        point of use rather than buried in a file nobody reads.
        """
        return {
            "loaded": self.loaded,
            "schema": self.document.get("schema"),
            "built_at": self.document.get("built_at"),
            "source_commit": self.document.get("source_commit"),
            "datastore_url": self.document.get("datastore_url"),
            "stats": self.document.get("stats", {}),
        }

    # ---------------------------------------------------------------- queries
    def _filter(
        self,
        genus: str = "",
        species: str = "",
        collection_type: str = "",
        has_doi: bool = False,
        indexed_only: bool = False,
    ) -> Iterable[dict[str, Any]]:
        genus = (genus or "").lower()
        species = (species or "").lower()
        collection_type = (collection_type or "").lower()
        for collection in self.collections:
            if genus and collection["genus"].lower() != genus:
                continue
            if species and collection["species"].lower() != species:
                continue
            if collection_type and collection["type"].lower() != collection_type:
                continue
            if has_doi and not collection.get("publication_doi"):
                continue
            if indexed_only and not any("i" in f for f in collection.get("files", [])):
                continue
            yield collection

    def list_collections(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Collections matching the given filters."""
        return list(self._filter(**kwargs))

    def get_collection(self, path: str) -> Optional[dict[str, Any]]:
        """One collection by its ``Genus/species/type/identifier`` path."""
        return self._by_path.get(path)

    def list_types(self, genus: str = "", species: str = "") -> dict[str, int]:
        """Collection types available, with counts.

        Answers "what kinds of data exist for this species", which over HTTP
        needs a directory listing per type and cannot report zero.
        """
        counts: dict[str, int] = {}
        for collection in self._filter(genus=genus, species=species):
            counts[collection["type"]] = counts.get(collection["type"], 0) + 1
        return dict(sorted(counts.items()))

    def species_with(self, types: Iterable[str]) -> list[dict[str, Any]]:
        """Species holding a collection of *every* named type.

        The co-availability question behind most study design ("which species
        have both diversity and expression data"). Crawling cannot answer it,
        because it requires knowing the whole store at once.
        """
        wanted = {t.lower() for t in types if t}
        if not wanted:
            return []
        available: dict[tuple, set] = {}
        for collection in self.collections:
            key = (collection["genus"], collection["species"])
            available.setdefault(key, set()).add(collection["type"].lower())
        out = []
        for (genus, species), present in sorted(available.items()):
            if wanted <= present:
                out.append(
                    {
                        "genus": genus,
                        "species": species,
                        "types": sorted(present),
                    }
                )
        return out

    def rank_assemblies(
        self, genus: str = "", species: str = ""
    ) -> list[dict[str, Any]]:
        """Genome collections ordered by assembly quality, best first.

        Intended ordering is BUSCO completeness then contig N50: without it a
        client takes whatever a directory listing returns first, which is
        alphabetical -- that is how a request for a soybean annotation lands on
        ``58-161`` instead of ``Wm82``.

        NOTE: ranking is currently disabled because the catalog does not yet emit
        assembly metrics. Check :meth:`assemblies_are_ranked` before describing
        the result as ranked.
        """
        rows = []
        for collection in self._filter(
            genus=genus, species=species, collection_type="genomes"
        ):
            # NOTE: assembly metrics are not emitted by the catalog builder yet
            # (see the matching NOTE in LIS-autocontent scripts/catalog.py). Until
            # they are, this cannot rank and returns genomes in catalog order.
            # Re-enable by uncommenting the two blocks below.
            # busco = collection.get("busco") or {}
            # counts = collection.get("counts") or {}
            rows.append(
                {
                    "path": collection["path"],
                    "id": collection["id"],
                    "genus": collection["genus"],
                    "species": collection["species"],
                    "genotype": collection.get("genotype"),
                    # "busco_complete_pct": busco.get("complete_pct"),
                    # "contig_n50": counts.get("contig_n50"),
                    # "scaffold_n50": counts.get("scaffold_n50"),
                    # "total_length": counts.get("total_length"),
                    "chromosome_prefix": collection.get("chromosome_prefix"),
                    "publication_doi": collection.get("publication_doi"),
                }
            )
        # NOTE: quality ordering is deferred with the metrics above. Sorting on
        # absent fields would silently produce catalog order while looking ranked,
        # so the sort is off rather than inert, and `ranked` says which you got.
        # rows.sort(
        #     key=lambda r: (
        #         r["busco_complete_pct"] if r["busco_complete_pct"] is not None else -1,
        #         r["contig_n50"] or 0,
        #     ),
        #     reverse=True,
        # )
        return rows

    @staticmethod
    def assemblies_are_ranked() -> bool:
        """Whether :meth:`rank_assemblies` can currently order on quality.

        False while assembly metrics are deferred. Exposed so a caller can say
        "unranked" rather than presenting catalog order as a quality ordering.
        """
        return False

    def lineage(self, identifier: str) -> dict[str, Any]:
        """Ancestry of a collection, with every publication it depends on.

        Walking ``derived_from`` and collecting DOIs turns "cite everything this
        result rests on" into one traversal.
        """
        seen: list[dict[str, Any]] = []
        dois: list[str] = []
        queue = list(self._by_id.get(identifier, []))
        if not queue:
            return {"identifier": identifier, "found": False, "chain": [], "dois": []}
        visited = set()
        while queue:
            collection = queue.pop(0)
            if collection["path"] in visited:
                continue
            visited.add(collection["path"])
            seen.append(
                {
                    "path": collection["path"],
                    "id": collection["id"],
                    "type": collection["type"],
                    "publication_doi": collection.get("publication_doi"),
                    "publication_title": collection.get("publication_title"),
                    "license": collection.get("license"),
                }
            )
            doi = collection.get("publication_doi")
            if doi and doi not in dois:
                dois.append(doi)
            for parent_id in collection.get("derived_from", []) or []:
                queue.extend(self._by_id.get(parent_id, []))
        return {
            "identifier": identifier,
            "found": True,
            "chain": seen,
            "dois": dois,
        }

    def pairwise(
        self, genome: str = "", partner: str = "", kind: str = ""
    ) -> list[dict[str, Any]]:
        """Genome-pair relationships (synteny blocks, whole-genome alignments).

        Pairwise files are stored once, under whichever genome is the reference, so a
        genome appears as ``a`` in its own collection and as ``b`` in other species'.
        Filtering on ``genome`` matches EITHER side and normalises the result so the
        requested genome is always ``a`` -- without that, a genome that owns no
        collection of its own (Medicago owns none) looks like it has no relationships
        at all.
        """
        genome = (genome or "").strip()
        partner = (partner or "").strip()
        kind = (kind or "").strip()
        out = []
        for pair in self.document.get("pairwise", []):
            if kind and pair.get("kind") != kind:
                continue
            if genome and genome not in (pair["a"], pair["b"]):
                continue
            record = dict(pair)
            if genome and pair["b"] == genome and pair["a"] != genome:
                # Seen from the query genome's side: swap so `a` is always the caller's
                # genome, and say so, because block coordinates follow the file's own
                # orientation and the caller needs to know which side is which.
                record["a"], record["b"] = pair["b"], pair["a"]
                record["direction"] = "query"
            else:
                record["direction"] = "reference"
            if partner and record["b"] != partner:
                continue
            out.append(record)
        return out

    def genome_assemblies(self, genus: str = "", species: str = "") -> list[str]:
        """Assembly identifiers (``abbrev.strain.gnmN``) available for a scope.

        Lets a caller answer "which assemblies exist for this species" without
        listing collections -- the question behind most cross-assembly mistakes.
        """
        out = set()
        for collection in self._filter(
            genus=genus, species=species, collection_type="genomes"
        ):
            abbrev = collection.get("scientific_name_abbrev")
            stem = ".".join(collection["id"].split(".")[:2])
            if abbrev and stem:
                out.add(f"{abbrev}.{stem}")
        return sorted(out)

    def resolve_symbol(
        self, symbol: str, abbrev: str = ""
    ) -> list[dict[str, Any]]:
        """Curated gene symbol -> gene id, from the catalog's ``gene_symbols`` map.

        Sourced from ``gene_functions/<abbrev>.traits.yml``, which also supplies the
        gene's own publication DOI. Matching is case-insensitive. Pass ``abbrev`` to
        scope to one species; without it a symbol may legitimately match in several.
        """
        wanted = (symbol or "").strip().lower()
        if not wanted:
            return []
        out = []
        for species_abbrev, index in self.document.get("gene_symbols", {}).items():
            if abbrev and species_abbrev != abbrev.lower():
                continue
            entry = index.get(wanted)
            if entry:
                record = dict(entry)
                record["abbrev"] = species_abbrev
                out.append(record)
        return out

    def indexed_files(
        self, genus: str = "", species: str = "", collection_type: str = ""
    ) -> list[dict[str, Any]]:
        """Files that can be range-read over HTTP, with their access mode.

        The store's directory index hides ``.fai``/``.tbi`` siblings, so this is
        derived from CHECKSUM and is not reproducible by listing the store.
        Collections whose ``index_status`` is ``"unknown"`` are reported as such
        rather than omitted, so a caller can tell "no indexes" from "not known".
        """
        out = []
        for collection in self._filter(
            genus=genus, species=species, collection_type=collection_type
        ):
            if collection.get("index_status") != "known":
                out.append(
                    {
                        "path": collection["path"],
                        "index_status": collection.get("index_status", "unknown"),
                        "files": [],
                    }
                )
                continue
            files = [
                {
                    "name": f["n"],
                    "url": f"{collection['base_url']}/{f['n']}",
                    "indexes": f["i"],
                    "description": f.get("description"),
                }
                for f in collection.get("files", [])
                if "i" in f
            ]
            if files:
                out.append(
                    {
                        "path": collection["path"],
                        "index_status": "known",
                        "files": files,
                    }
                )
        return out
