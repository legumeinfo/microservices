# dependencies
from dscensor.directed_graph import DirectedGraphController


class RequestHandler:
    def __init__(self, nodes):
        self.controller = DirectedGraphController(nodes)

    async def list_genus(self):
        genus_list = {}
        for node in list(self.controller.digraph.nodes(data=True)):
            # data part of node tuple with genus key
            node_genus = node[1]["metadata"]["genus"]
            genus_list[node_genus] = 1
        return [genus for genus in genus_list]

    async def list_species(self):
        species_list = {}
        for node in list(self.controller.digraph.nodes(data=True)):
            # data part of node tuple with species key
            node_species = node[1]["metadata"]["species"]
            species_list[node_species] = 1
        return [species for species in species_list]

    async def list_genomes(self, genus="", species=""):
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

    async def list_gene_models(self, genus, species):
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
