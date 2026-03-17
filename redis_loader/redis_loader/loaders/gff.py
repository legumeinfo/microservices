# Python
import codecs
import csv
import gzip
import tempfile
from collections import defaultdict
from urllib.request import urlopen, urlparse

# dependencies
import pyranges1 as pr


def _open_gff_source(source):
    """
    Opens a GFF source (local path or URL, optionally gzipped) and returns
    a path that PyRanges can read.

    PyRanges read_gff3 expects a local file path, so for URLs we download
    to a temporary file first.

    Parameters:
        source (str): Local path or URL to a GFF file (may be gzipped).

    Returns:
        str: Path to a readable GFF file.
    """
    parsed = urlparse(source)
    is_remote = parsed.scheme in ("http", "https", "ftp")

    if not is_remote:
        # Local file - pyranges handles gzip automatically based on extension
        return source

    # Remote URL - download to temp file
    suffix = ".gff3.gz" if source.endswith(".gz") else ".gff3"
    with tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False) as tmp:
        with urlopen(source) as response:
            tmp.write(response.read())
        return tmp.name


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
        set[str]: A set containing the names of all the chromosomes that were loaded.
    """
    gff_path = _open_gff_source(chromosome_gff)
    gff = pr.read_gff3(gff_path)

    # Filter to chromosome and supercontig features only
    chromosomes = gff[gff.Feature.isin(["chromosome", "supercontig"])]

    # index the chromosomes
    chromosome_names = set()
    for row in chromosomes.itertuples():
        name = row.Chromosome
        # End is already converted to 0-based exclusive by pyranges,
        # which equals the length for a feature starting at position 1
        length = row.End
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
        chromosome_names (set[str]): A set containing the names of all the chromosomes
            that have been loaded.
    """
    gff_path = _open_gff_source(gene_gff)
    gff = pr.read_gff3(gff_path)

    # Filter to gene features only
    genes_df = gff[gff.Feature == "gene"]

    # Build gene lookup and chromosome groupings
    strand_map = {"+": 1, "-": -1}
    gene_lookup = {}
    chromosome_genes = defaultdict(list)

    for row in genes_df.itertuples():
        chr_name = row.Chromosome
        if chr_name not in chromosome_names:
            continue

        gene_id = row.ID if hasattr(row, "ID") else row.Index
        # PyRanges uses 0-based half-open coordinates [start, end)
        # GFF3/gffutils uses 1-based closed coordinates [start, end]
        # Convert back to 1-based to match original gffutils behavior
        gene = {
            "name": gene_id,
            "fmin": row.Start + 1,  # Convert 0-based to 1-based
            "fmax": row.End,  # End is same in both systems
            "strand": strand_map.get(row.Strand, 0),
            "family": "",
        }
        gene_lookup[gene_id] = gene
        chromosome_genes[chr_name].append(gene)

    # Load family assignments from GFA file
    _load_gene_families(gfa, gene_lookup)

    # Index the genes
    for chr_name, genes in chromosome_genes.items():
        redisearch_loader.indexChromosomeGenes(chr_name, genes)


def _load_gene_families(gfa, gene_lookup):
    """
    Loads gene family assignments from a GFA file into the gene lookup dict.

    Parameters:
        gfa (str): Local path or URL to a GFA file (may be gzipped).
        gene_lookup (dict): Dictionary mapping gene IDs to gene dicts.
    """
    parsed = urlparse(gfa)
    is_remote = parsed.scheme in ("http", "https", "ftp")

    with open(gfa, "rb") if not is_remote else urlopen(gfa) as fileobj:
        tsv = gzip.GzipFile(fileobj=fileobj) if gfa.endswith(".gz") else fileobj
        for line in csv.reader(codecs.iterdecode(tsv, "utf-8"), delimiter="\t"):
            # Skip comment and metadata lines
            if not line or line[0].startswith("#") or line[0] == "ScoreMeaning":
                continue
            gene_id = line[0]
            if gene_id in gene_lookup:
                gene_lookup[gene_id]["family"] = line[1]


def loadFromGFF(
    redisearch_loader, genus, species, strain, chromosome_gff, gene_gff, gfa
):
    """
    Loads data from GFF files into a RediSearch database.

    Parameters:
        redisearch_loader (RediSearchLoader): The loader to use to load data into
            RediSearch.
        genus (str): The genus of the data being loaded.
        species (str): The species of the data being loaded.
        strain (str): The strain of the data being loaded.
        chromosome_gff (str): The path or URL to the GFF to load chromosomes from.
        gene_gff (str): The path or URL to the GFF to load genes from.
        gfa (str): The path or URL to a GFA file containing gene family
            associations for the genes being loaded.
    """
    # HACK the species to contain the strain name if given
    if strain is not None:
        species += ":" + strain
    chromosome_names = transferChromosomes(
        redisearch_loader, genus, species, chromosome_gff
    )
    transferGenes(redisearch_loader, gene_gff, gfa, chromosome_names)
