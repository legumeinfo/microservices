import glob
import logging
import re

import yaml

HREF = "href"
METHOD = "method"
TEXT = "text"

GENE_LINKOUTS = "gene_linkouts"
GENE_REGEX = re.compile("{GENE_ID}")
UNPREFIXED_GENE_REGEX = re.compile("{UNPREFIXED_GENE_ID}")

GENOMIC_REGION_LINKOUTS = "genomic_region_linkouts"
GENOMIC_REGION_SPECIFIER_REGEX = re.compile(r"^([^:]+):(\d+)(-|\.\.)(\d+)$")
GENOMIC_REGION_REGEX = re.compile("{GENOMIC_REGION}")
GENOMIC_REGION_CHR_ID_REGEX = re.compile("{GENOMIC_REGION_CHR_ID}")
GENOMIC_REGION_START_REGEX = re.compile("{GENOMIC_REGION_START}")
GENOMIC_REGION_END_REGEX = re.compile("{GENOMIC_REGION_END}")

GENE_FAMILY_LINKOUTS = "gene_family_linkouts"
GENE_FAMILY_REGEX = re.compile("{GENE_FAMILY_ID}")

PAN_GENE_SET_LINKOUTS = "pan_gene_set_linkouts"
PAN_GENE_SET_REGEX = re.compile("{PAN_GENE_SET_ID}")


class RequestHandler:
    def __init__(self, lglob_root):
        self.linkout_lookup = {}
        try:
            for lfile in glob.glob(
                "**/LINKOUTS.*.yml", root_dir=lglob_root, recursive=True
            ):
                self._read_linkouts(lglob_root + "/" + lfile)
        except Exception as e:
            logging.error("failed to read linkouts from " + lglob_root + "/" + lfile)
            logging.error(e)

    def _read_linkouts(self, lfile):
        f = open(lfile, "r")
        yml = yaml.load(f.read(), Loader=yaml.FullLoader)
        prefix = yml["prefix"]

        for linkable_type in [
            GENE_LINKOUTS,
            GENOMIC_REGION_LINKOUTS,
            GENE_FAMILY_LINKOUTS,
            PAN_GENE_SET_LINKOUTS,
        ]:
            if yml.get(linkable_type) is not None:
                for linkout in yml[linkable_type]:
                    if self.linkout_lookup.get(linkable_type) is None:
                        self.linkout_lookup[linkable_type] = {}
                    type_lookup = self.linkout_lookup[linkable_type]
                    if type_lookup.get(prefix) is None:
                        type_lookup[prefix] = []
                    type_lookup[prefix].append(linkout)

    def process_genes(self, ids):
        linkouts = []
        if self.linkout_lookup.get(GENE_LINKOUTS) is None:
            return linkouts

        type_lookup = self.linkout_lookup.get(GENE_LINKOUTS)

        for id in ids:
            prefix = ".".join(id.split(".")[0:4])
            unprefixed_id = ".".join(id.split(".")[4:])
            if type_lookup.get(prefix) is not None:
                templates = type_lookup[prefix]
                for template in templates:
                    linkout = {}
                    linkout[METHOD] = template[METHOD]
                    # TODO: if method is POST, we probably need to do something with the
                    # request body content
                    linkout[HREF] = GENE_REGEX.sub(id, template[HREF])
                    linkout[HREF] = UNPREFIXED_GENE_REGEX.sub(
                        unprefixed_id, linkout[HREF]
                    )
                    linkout[TEXT] = GENE_REGEX.sub(id, template[TEXT])
                    linkout[TEXT] = UNPREFIXED_GENE_REGEX.sub(
                        unprefixed_id, linkout[TEXT]
                    )
                    linkouts.append(linkout)
        return linkouts

    def process_genomic_regions(self, ids):
        linkouts = []
        if self.linkout_lookup.get(GENOMIC_REGION_LINKOUTS) is None:
            return linkouts

        type_lookup = self.linkout_lookup.get(GENOMIC_REGION_LINKOUTS)

        for id in ids:
            m = GENOMIC_REGION_SPECIFIER_REGEX.match(id)
            if m is None:
                continue
            chr = m.group(1)
            start = m.group(2)
            end = m.group(4)

            prefix = ".".join(chr.split(".")[0:3])
            if type_lookup.get(prefix) is not None:
                templates = type_lookup[prefix]
                for template in templates:
                    linkout = {}
                    linkout[METHOD] = template[METHOD]
                    # TODO: if method is POST, we probably need to do something with the
                    # request body content
                    linkout_href = GENOMIC_REGION_REGEX.sub(id, template[HREF])
                    linkout_href = GENOMIC_REGION_CHR_ID_REGEX.sub(chr, linkout_href)
                    linkout_href = GENOMIC_REGION_START_REGEX.sub(start, linkout_href)
                    linkout_href = GENOMIC_REGION_END_REGEX.sub(end, linkout_href)
                    linkout[HREF] = linkout_href
                    linkout[TEXT] = GENOMIC_REGION_REGEX.sub(id, template[TEXT])
                    linkouts.append(linkout)
        return linkouts

    def process_gene_families(self, ids):
        linkouts = []
        if self.linkout_lookup.get(GENE_FAMILY_LINKOUTS) is None:
            return linkouts

        type_lookup = self.linkout_lookup.get(GENE_FAMILY_LINKOUTS)

        for id in ids:
            prefix = ".".join(id.split(".")[0:1])
            if type_lookup.get(prefix) is not None:
                templates = type_lookup[prefix]
                for template in templates:
                    linkout = {}
                    linkout[METHOD] = template[METHOD]
                    # TODO: if method is POST, we probably need to do something with the
                    # request body content
                    linkout[HREF] = GENE_FAMILY_REGEX.sub(id, template[HREF])
                    linkout[TEXT] = GENE_FAMILY_REGEX.sub(id, template[TEXT])
                    linkouts.append(linkout)
        return linkouts

    def process_pan_gene_sets(self, ids):
        linkouts = []
        if self.linkout_lookup.get(PAN_GENE_SET_LINKOUTS) is None:
            return linkouts

        type_lookup = self.linkout_lookup.get(PAN_GENE_SET_LINKOUTS)

        for id in ids:
            prefix = ".".join(id.split(".")[0:2])
            if type_lookup.get(prefix) is not None:
                templates = type_lookup[prefix]
                for template in templates:
                    linkout = {}
                    linkout[METHOD] = template[METHOD]
                    # TODO: if method is POST, we probably need to do something with the
                    # request body content
                    linkout[HREF] = PAN_GENE_SET_REGEX.sub(id, template[HREF])
                    linkout[TEXT] = PAN_GENE_SET_REGEX.sub(id, template[TEXT])
                    linkouts.append(linkout)
        return linkouts
