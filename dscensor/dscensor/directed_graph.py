"""Controls the creation of a directed graph using networkx.

   populates self.digraph.nodes and self.digraph.edges from dscensor JSON nodes
"""

import glob
import json
import logging
import os

import networkx as nx


class DirectedGraphController:
    """Imported by application to build and query directed graph"""

    def __init__(self, dscensor_nodes="./autocontent"):
        # collection of all objects for lookup in edge building
        self.all_objects = {}
        # directory to load object.json files from lis-autocontent populate-dscensor
        self.dscensor_nodes = os.path.abspath(dscensor_nodes)
        # initialize digraph
        self.digraph = nx.DiGraph()
        self.parse_dscensor_nodes()
        self.generate_digraph()

    def parse_dscensor_nodes(self):
        """Read all object.json files from self.dscensor_nodes directory"""
        dscensor_nodes = self.dscensor_nodes
        logging.info(f"Parsing DSCensor Nodes from: {dscensor_nodes}...")
        for dsnode in glob.glob(
            f"{dscensor_nodes}/*.json"
        ):  # find all json objects in dscensor_nodes directory
            logging.debug(dsnode)
            dsjson = None
            metadata = {"metadata": {}, "counts": {}, "busco": {}}
            with open(dsnode, encoding="UTF-8") as nopen:
                dsjson = json.loads(nopen.read())
            logging.debug(dsjson)
            for k in dsjson:
                v = dsjson[k]
                if k == "counts" or k == "busco":
                    metadata[k] = v
                    continue
                metadata["metadata"][k] = v
            name = dsjson["filename"]
            self.all_objects[
                name
            ] = metadata  # add object to self.all_objects for edge lookup later
            logging.debug(self.all_objects[name])

    def generate_digraph(self):
        """Create directed graph for use in DSCensor in memory service"""
        digraph = self.digraph
        logging.info("Generating directed graph...")
        if not self.all_objects.items():
            logging.warning("No Objects Loaded! Check nodes directory!")
        parent_count = 0
        children_count = 0
        for name, node in self.all_objects.items():
            logging.debug(node)
            if name in digraph:  # already added node as parent
                continue
            digraph.add_node(name, **node)  # add node and **attrs
            parents = node["metadata"]["derived_from"]
            logging.debug(parents)
            if parents:
                children_count += 1
            for parent in parents:
                if not parent:
                    continue
                parent_node = self.all_objects.get(parent, None)
                if not parent_node:  # in case parent not found REPORT AND FIX
                    logging.error(f"No parent for {parent}")
                    continue
                parent_count += 1
                logging.debug(parent_node)
                digraph.add_node(parent, **parent_node)  # add parent and **attrs
                digraph.add_edge(name, parent)  # add derived_from edge equivalent
        logging.info(f"Loaded {parent_count} Parents and {children_count} Children.")

    def dump_nodes(self):
        """Dump digraph nodes as a list of dictionaries"""
        logging.info("Dumping Nodes...")
        my_nodes = {"nodes": list(self.digraph.nodes(data=True))}
        return json.dumps(my_nodes, indent=4)

    def dump_edges(self):
        """Dump digraph edges as a list"""
        logging.info("Dumping Edges...")
        my_edges = {"edges": list(self.digraph.edges())}
        return json.dumps(my_edges, indent=4)
