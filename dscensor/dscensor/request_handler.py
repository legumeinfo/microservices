"""Query the DSCensor directed graph on behalf of the HTTP routes."""

from __future__ import annotations

from typing import Any, Optional

from dscensor.directed_graph import DirectedGraphController


class RequestHandler:
    """Thin query layer over :class:`DirectedGraphController`."""

    def __init__(self, nodes: str):
        self.controller = DirectedGraphController(nodes)

    def _nodes(self):
        """Yield the ``(name, data)`` tuples of every node in the graph."""
        return self.controller.digraph.nodes(data=True)

    def list_genus(self) -> list[str]:
        """Return every genus present in the graph, in insertion order."""
        genus_list: dict[str, None] = {}
        for _, data in self._nodes():
            genus_list[data["metadata"]["genus"]] = None
        return list(genus_list)

    def list_species(self, genus: str = "") -> list[str]:
        """Return every species in the graph, optionally limited to ``genus``.

        :param genus: Case-insensitive genus filter; empty means all genera.
        """
        genus = genus.lower()
        species_list: dict[str, None] = {}
        for _, data in self._nodes():
            metadata = data["metadata"]
            if genus and metadata["genus"].lower() != genus:
                continue
            species_list[metadata["species"]] = None
        return list(species_list)

    def _list_by_type(
        self,
        canonical_type: str,
        genus: str = "",
        species: str = "",
        results: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Return nodes of ``canonical_type`` matching the taxon filters.

        :param canonical_type: e.g. ``genome_main`` or ``gene_models_main``.
        :param genus: Case-insensitive genus filter; empty means any.
        :param species: Case-insensitive species filter within ``genus``;
            ignored unless ``genus`` is also given.
        :param results: If given, return at most this many nodes.
        """
        genus = genus.lower()
        species = species.lower() if genus else ""
        matches: list[dict[str, Any]] = []
        for _, data in self._nodes():
            metadata = data["metadata"]
            if metadata["canonical_type"] != canonical_type:
                continue
            if genus and metadata["genus"].lower() != genus:
                continue
            if species and metadata["species"].lower() != species:
                continue
            matches.append(data)
            if results is not None and len(matches) >= results:
                break
        return matches

    def list_genomes(
        self, genus: str = "", species: str = "", results: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Return ``genome_main`` nodes; see :meth:`_list_by_type`."""
        return self._list_by_type("genome_main", genus, species, results)

    def list_gene_models(
        self, genus: str = "", species: str = "", results: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Return ``gene_models_main`` nodes; see :meth:`_list_by_type`."""
        return self._list_by_type("gene_models_main", genus, species, results)

    def list_proteins(
        self, genus: str = "", species: str = "", results: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Return ``protein`` nodes; see :meth:`_list_by_type`."""
        return self._list_by_type("protein", genus, species, results)

    def list_proteins_primary(
        self, genus: str = "", species: str = "", results: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Return ``protein_primary`` nodes; see :meth:`_list_by_type`."""
        return self._list_by_type("protein_primary", genus, species, results)
