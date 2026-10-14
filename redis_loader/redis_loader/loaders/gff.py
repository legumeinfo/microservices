# Python
import codecs
import csv
import gzip
from collections import defaultdict
from contextlib import contextmanager
from urllib.parse import unquote
from urllib.request import Request, urlopen, urlparse

# dependencies
import pysam


@contextmanager
def openFile(path):
    """
    Opens a local file or URL for binary reading, decompressing it if gzipped.

    Parameters:
      path (str): The local path or URL of the file to open.

    Yields:
      file: A binary file-like object.
    """

    with (
        open(path, "rb")
        if urlparse(path).scheme == ""
        else urlopen(Request(path, headers={"User-Agent": "NCGR Redis Loader"}))
    ) as fileobj:
        yield gzip.GzipFile(fileobj=fileobj) if path.endswith("gz") else fileobj


class GFF3Reader:
    """
    Adapts a GFF3 stream for pysam.tabix_iterator, which cannot parse a ##FASTA
    section and requires every line to end with a newline.
    """

    closed = False

    def __init__(self, fileobj):
        self.fileobj = fileobj

    def readline(self):
        line = self.fileobj.readline()
        if line.startswith(b"##FASTA"):
            return b""
        if line and not line.endswith(b"\n"):
            line += b"\n"
        return line


def readFeatures(path, types):
    """
    Reads features of the given types from a GFF3 file.

    Parameters:
      path (str): The local path or URL to the GFF3 file to read.
      types (set[str]): The feature types (column 3) to read.

    Yields:
      pysam.libctabixproxies.GFF3Proxy: Each feature of the given types.
    """

    parser = pysam.asGFF3()
    parser.set_encoding("utf-8")
    with openFile(path) as fileobj:
        for feature in pysam.tabix_iterator(GFF3Reader(fileobj), parser):
            if feature.feature in types:
                yield feature


def transferChromosomes(redisearch_loader, genus, species, chromosome_gff):
    """
    Loads chromosomes from a GFF file into a RediSearch database.

    Parameters:
      redisearch_loader (RediSearchLoader): The loader to use to load data into
        RediSearch.
      genus (str): The genus of the chromosomes being loaded.
      species (str): The species of the chromosomes being loaded.
      chromosome_gff (str): The local path or URL to the GFF to load chromosomes from.

    Returns:
      set[str]: A set containing the names of all the chromosomes that were
        loaded.
    """

    # index the chromosomes
    chromosome_names = set()
    for chr in readFeatures(chromosome_gff, {"chromosome", "supercontig"}):
        name = chr.contig
        length = chr.end
        chromosome_names.add(name)
        redisearch_loader.indexChromosome(name, length, genus, species)

    return chromosome_names


def transferGenes(redisearch_loader, gene_gff, gfa, chromosome_names):
    """
    Loads genes from a GFF file into a RediSearch database.

    Parameters:
      redisearch_loader (RediSearchLoader): The loader to use to load data into
        RediSearch.
      gene_gff (str): The local path or URL to the GFF to load genes from.
      gfa (str): The local path or URL to a GFA file containing gene family
        associations for the genes being loaded.
      chromosome_names (set[str]): A containing the names of all the chromosomes
        that have been loaded.
    """

    # index all the genes in the GFF
    gene_lookup = dict()
    chromosome_genes = defaultdict(list)
    # only "gene" features are loaded; ncRNA_gene, pseudogene, etc. are ignored
    for gffgene in readFeatures(gene_gff, {"gene"}):
        chr_name = gffgene.contig
        # genes without an ID can't be keyed in Redis or matched to the GFA
        if chr_name in chromosome_names and "ID" in gffgene.keys():
            strand = 0
            if gffgene.strand == "+":
                strand = 1
            if gffgene.strand == "-":
                strand = -1
            # pysam coordinates are 0-based, half-open
            gene = {
                "name": unquote(gffgene.ID),
                "fmin": gffgene.start + 1,
                "fmax": gffgene.end,
                "strand": strand,
                "family": "",
            }
            gene_lookup[gene["name"]] = gene
            chromosome_genes[chr_name].append(gene)
    # deal with family assignments (for non-orphans) from GFA
    with openFile(gfa) as tsv:
        for line in csv.reader(codecs.iterdecode(tsv, "utf-8"), delimiter="\t"):
            # skip comment and metadata lines
            if line[0].startswith("#") or line[0] == "ScoreMeaning":
                continue
            gene_id = line[0]
            if gene_id in gene_lookup:
                gene = gene_lookup[gene_id]
                genefamily_id = line[1]
                gene["family"] = genefamily_id

    # index the genes
    for chr_name, genes in chromosome_genes.items():
        redisearch_loader.indexChromosomeGenes(chr_name, genes)


def loadFromGFF(
    redisearch_loader, genus, species, strain, chromosome_gff, gene_gff, gfa
):
    """
    Loads data from a GFF files into a RediSearch database.

    Parameters:
      redisearch_loader (RediSearchLoader): The loader to use to load data into
        RediSearch.
      genus (str): The genus of the data being loaded.
      species (str): The species of the data being loaded.
      strain (str): The strain of the data being loaded.
      chromosome_gff (pathlib.Path): The path to the GFF to load chromosomes from.
      gene_gff (pathlib.Path): The path to the GFF to load genes from.
      gfa (pathlib.Path): The path to a GFA file containing gene family
        associations for the genes being loaded.
    """

    # HACK the species to contain the strain name if given
    if strain is not None:
        species += ":" + strain
    chromosome_names = transferChromosomes(
        redisearch_loader, genus, species, chromosome_gff
    )
    transferGenes(redisearch_loader, gene_gff, gfa, chromosome_names)
