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

    def __init__(self, logger, dscensor_nodes="./autocontent"):
        self.logger = logger
        self.all_objects = {}  # collection of all objects for lookup in edge building
        self.dscensor_nodes = os.path.abspath(
            dscensor_nodes
        )  # directory to load object.json files from lis-autocontent populate-dscensor
        self.digraph = nx.DiGraph()  # initialize digraph
        self.parse_dscensor_nodes()
        self.generate_digraph()

    def parse_dscensor_nodes(self):
        """Read all object.json files from self.dscensor_nodes directory"""
        logger = self.logger
        dscensor_nodes = self.dscensor_nodes
        logger.info(f"Parsing DSCensor Nodes from: {dscensor_nodes}...")
        for dsnode in glob.glob(
            f"{dscensor_nodes}/*.json"
        ):  # find all json objects in dscensor_nodes directory
            logger.debug(dsnode)
            dsjson = None
            metadata = {"metadata": {}, "counts": {}, "busco": {}}
            with open(dsnode, encoding="UTF-8") as nopen:
                dsjson = json.loads(nopen.read())
            logger.debug(dsjson)
            for k in dsjson:
                v = dsjson[k]
                if k == "counts" or k == "busco":
                    metadata[k] = v
                    continue
                metadata["metadata"][k] = v
            name = dsjson["filename"]
            self.all_objects[name] = (
                metadata  # add object to self.all_objects for edge lookup later
            )
            logger.debug(self.all_objects[name])

    def generate_digraph(self):
        """Create directed graph for use in DSCensor in memory service"""
        logger = self.logger
        digraph = self.digraph
        logger.info("Generating directed graph...")
        if not self.all_objects.items():
            logger.warning("No Objects Loaded! Check nodes directory!")
        parent_count = 0
        children_count = 0
        for name, node in self.all_objects.items():
            logger.debug(node)
            if name in digraph:  # already added node as parent
                continue
            digraph.add_node(name, **node)  # add node and **attrs
            parents = node["metadata"]["derived_from"]
            logger.debug(parents)
            if parents:
                children_count += 1
            for parent in parents:
                if not parent:
                    continue
                parent_node = self.all_objects.get(parent, None)
                if not parent_node:  # in case parent not found REPORT AND FIX
                    logger.error(f"No parent for {parent}")
                    continue
                parent_count += 1
                logger.debug(parent_node)
                digraph.add_node(parent, **parent_node)  # add parent and **attrs
                digraph.add_edge(name, parent)  # add derived_from edge equivalent
        logger.info(f"Loaded {parent_count} Parents and {children_count} Children.")

    def dump_nodes(self):
        """Dump digraph nodes as a list of dictionaries"""
        logger = self.logger
        logger.info("Dumping Nodes...")
        my_nodes = {"nodes": list(self.digraph.nodes(data=True))}
        return json.dumps(my_nodes, indent=4)

    def dump_edges(self):
        """Dump digraph edges as a list"""
        logger = self.logger
        logger.info("Dumping Edges...")
        my_edges = {"edges": list(self.digraph.edges())}
        return json.dumps(my_edges, indent=4)


if __name__ == "__main__":

    def setup_logging(log_file, log_level, process):  # should remove this
        """initializes a logger object with a common format"""
        log_level = getattr(
            logging, log_level.upper(), logging.INFO
        )  # set provided or set INFO
        msg_format = "%(asctime)s|%(name)s|[%(levelname)s]: %(message)s"
        logging.basicConfig(format=msg_format, datefmt="%m-%d %H:%M", level=log_level)
        log_handler = logging.FileHandler(log_file, mode="w")
        formatter = logging.Formatter(msg_format)
        log_handler.setFormatter(formatter)
        logger = logging.getLogger(
            f"{process}"
        )  # sets what will be printed for the log process
        logger.addHandler(log_handler)
        return logger

    my_graph = DirectedGraphController(
        setup_logging("./dscensor-digraph.log", "debug", "generate-digraph"),
        dscensor_nodes="./autocontent",
    )  # test digraph instance with local ./autocontent
    print(my_graph.dump_nodes())
    print(my_graph.dump_edges())
