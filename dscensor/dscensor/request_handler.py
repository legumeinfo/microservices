# dependencies
from typing import Optional, TypedDict

from dscensor.directed_graph import DirectedGraphController

GENE_MODELS_GFF_SUFFIX = "gene_models_main.gff3.gz"
GENE_MODELS_BED_SUFFIX = "gene_models_main.bed.gz"
PROTEIN_FASTA_SUFFIX = "protein_primary.faa.gz"
CDS_FASTA_SUFFIX = "cds_primary.fna.gz"


class FilesForPrefix(TypedDict):
    """URLs and identifying metadata for a single LIS annotation.

    All URL fields are Optional because the caller may not have a confirmed
    naming-convention match (protein/CDS/BED come from suffix substitution
    off the GFF URL, genome from a derived_from edge); returning None is
    safer than fabricating a URL the caller would treat as authoritative.
    """

    protein_url: Optional[str]
    cds_url: Optional[str]
    bed_url: Optional[str]
    genome_url: Optional[str]
    genus: Optional[str]
    species: Optional[str]
    infraspecies: Optional[str]


class RequestHandler:
    def __init__(self, nodes):
        self.controller = DirectedGraphController(nodes)

    def list_genus(self):
        genus_list = {}
        for node in list(self.controller.digraph.nodes(data=True)):
            # data part of node tuple with genus key
            node_genus = node[1]["metadata"]["genus"]
            genus_list[node_genus] = 1
        return [genus for genus in genus_list]

    def list_species(self):
        species_list = {}
        for node in list(self.controller.digraph.nodes(data=True)):
            # data part of node tuple with species key
            node_species = node[1]["metadata"]["species"]
            species_list[node_species] = 1
        return [species for species in species_list]

    def list_genomes(self, genus="", species=""):
        genus = genus.lower()
        species = species.lower()
        genomes_main = {}
        for node in list(self.controller.digraph.nodes(data=True)):
            node_genus = node[1]["metadata"]["genus"].lower()
            node_species = node[1]["metadata"]["species"].lower()
            node_canonical_type = node[1]["metadata"]["canonical_type"]
            if node_canonical_type != "genome_main":
                continue
            # if genus provided only take matching genus
            if genus:
                if node_genus != genus:
                    continue
                # if genus and species make sure species within genus
                if species:
                    if node_species != species:
                        continue
            # lets you specify species without genus which is probably stupid
            if species:
                if node_species != species:
                    continue
            genomes_main[node[0]] = node[1]
        return [genomes_main[genome] for genome in genomes_main]

    def files_for_prefix(self, prefix: str) -> Optional[FilesForPrefix]:
        """Resolve a full-yuck annotation prefix to its canonical file URLs.

        Returns None when no matching gene_models_main node is in the digraph.
        Protein/CDS FASTA and gene_models_main BED URLs are derived by suffix
        substitution off the annotation GFF URL (the LIS datastore naming
        convention); they are None when the annotation URL doesn't follow that
        convention. The genome URL is taken from the genome_main node reachable
        via a `derived_from` edge.
        """
        digraph = self.controller.digraph
        annotation_name = None
        annotation_metadata = None
        for name, attrs in digraph.nodes(data=True):
            metadata = attrs.get("metadata", {})
            if (
                metadata.get("filename") == prefix
                and metadata.get("canonical_type") == "gene_models_main"
            ):
                annotation_name = name
                annotation_metadata = metadata
                break
        if annotation_metadata is None:
            return None

        gff_url = annotation_metadata.get("url", "")
        if gff_url.endswith(GENE_MODELS_GFF_SUFFIX):
            stem = gff_url[: -len(GENE_MODELS_GFF_SUFFIX)]
            protein_url = stem + PROTEIN_FASTA_SUFFIX
            cds_url = stem + CDS_FASTA_SUFFIX
            bed_url = stem + GENE_MODELS_BED_SUFFIX
        else:
            protein_url = None
            cds_url = None
            bed_url = None

        genome_url = None
        for parent in digraph.successors(annotation_name):
            parent_metadata = digraph.nodes[parent].get("metadata", {})
            if parent_metadata.get("canonical_type") == "genome_main":
                genome_url = parent_metadata.get("url")
                break

        return {
            "protein_url": protein_url,
            "cds_url": cds_url,
            "bed_url": bed_url,
            "genome_url": genome_url,
            "genus": annotation_metadata.get("genus"),
            "species": annotation_metadata.get("species"),
            "infraspecies": annotation_metadata.get("infraspecies"),
        }

    def list_gene_models(self, genus, species):
        gene_models_main = {}
        for node in list(self.controller.digraph.nodes(data=True)):
            node_genus = node[1]["metadata"]["genus"].lower()
            node_species = node[1]["metadata"]["species"].lower()
            node_canonical_type = node[1]["metadata"]["canonical_type"]
            if node_canonical_type != "gene_models_main":
                continue
            # if genus provided only take matching genus
            if genus:
                if node_genus != genus:
                    continue
                # if genus and species make sure species within genus
                if species:
                    if node_species != species:
                        continue
            # lets you specify species without genus which is probably stupid
            if species:
                if node_species != species:
                    continue
            gene_models_main[node[0]] = node[1]
        return [gene_models_main[genome] for genome in gene_models_main]
