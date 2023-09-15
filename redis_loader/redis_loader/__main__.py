#!/usr/bin/env python

# Python
import argparse
import os

# module
import redis_loader
from redis_loader.loaders import RediSearchLoader, loadFromChado, loadFromGFF


def chado(redisearch_loader, args):
    """
    Calls the Chado loader with the relevant command-line arguments.

    Parameters:
      redisearch_loader (RediSearchLoader): The loader to use to load data into
        RediSearch.
      args (argsparse.Namespace): A namespace mapping parsed arguments to their values.
    """

    loadFromChado(
        redisearch_loader,
        args.postgres_database,
        args.postgres_user,
        args.postgres_password,
        args.postgres_host,
        args.postgres_port,
        args.uniquename,
        args.sequence_types,
    )


def gff(redisearch_loader, args):
    """
    Calls the GFF loader with the relevant command-line arguments.

    Parameters:
      redisearch_loader (RediSearchLoader): The loader to use to load data into
        RediSearch.
      args (argsparse.Namespace): A namespace mapping parsed arguments to their values.
    """

    loadFromGFF(
        redisearch_loader,
        args.genus,
        args.species,
        args.strain,
        args.chromosome_gff,
        args.gene_gff,
        args.gfa,
    )


class EnvAction(argparse.Action):
    """
    A class that loads argument values from environment variables, resulting in a
    value priority: command line > environment variable > default value
    """

    def __init__(self, envvar, required=False, default=None, **kwargs):
        if envvar in os.environ:
            default = os.environ[envvar]
        if required and default is not None:
            required = False
        super(EnvAction, self).__init__(default=default, required=required, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


def parseArgs():
    """
    Parses command-line arguments.

    Returns:
      argparse.Namespace: A namespace mapping parsed arguments to their values.
    """

    # create the parser and command subparser
    parser = argparse.ArgumentParser(
        prog=redis_loader.__name__,
        description="""
        Loads data from a Chado (PostreSQL) database or GFF files into a RediSearch
        index for use by microservices.
        """,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"""
        %(prog)s {redis_loader.__version__} schema {redis_loader.__schema_version__}
        """,
    )
    subparsers = parser.add_subparsers(title="commands", dest="command", required=True)

    # Redis args
    rdb_envvar = "REDIS_DB"
    parser.add_argument(
        "--redis-db",
        dest="redis_db",
        action=EnvAction,
        envvar=rdb_envvar,
        type=int,
        default=0,
        help=f"""
        The Redis database (can also be specified using the {rdb_envvar} environment
        variable).
        """,
    )
    rpassword_envvar = "REDIS_PASSWORD"
    parser.add_argument(
        "--redis-password",
        dest="redis_password",
        action=EnvAction,
        envvar=rpassword_envvar,
        type=str,
        default="",
        help=f"""
        The Redis password (can also be specified using the {rpassword_envvar}
        environment variable).
        """,
    )
    rhost_envvar = "REDIS_HOST"
    parser.add_argument(
        "--redis-host",
        dest="redis_host",
        action=EnvAction,
        envvar=rhost_envvar,
        type=str,
        default="localhost",
        help=f"""
        The Redis host (can also be specified using the {rhost_envvar} environment
        variable).
        """,
    )
    rport_envvar = "REDIS_PORT"
    parser.add_argument(
        "--redis-port",
        dest="redis_port",
        action=EnvAction,
        envvar=rport_envvar,
        type=int,
        default=6379,
        help=f"""
        The Redis port (can also be specified using the {rport_envvar} environment
        variable).
        """,
    )
    rchunksize_envvar = "CHUNK_SIZE"
    parser.add_argument(
        "--chunk-size",
        dest="chunk_size",
        action=EnvAction,
        envvar=rchunksize_envvar,
        type=int,
        default=100,
        help=f"""
        The chunk size to be used for Redis batch processing (can also be specified
        using the {rchunksize_envvar} environment variable).
        """,
    )
    parser.add_argument(
        "--no-save",
        dest="no_save",
        action="store_true",
        help="Don't save the Redis database to disk after loading.",
    )
    parser.set_defaults(no_save=False)
    load_types = {
        "new": "Will only load indexes if they have to be created first.",
        "reload": "Will remove existing indexes before loading data.",
        "append": "Will add data to an existing index or create a new index.",
    }
    # TODO: prevent argparse from removing line breaks in help text
    loadtype_help = "".join(
        [f"\t{type} - {description} \n " for type, description in load_types.items()]
    )
    loadtype_envvar = "LOAD_TYPE"
    parser.add_argument(
        "--load-type",
        dest="load_type",
        action=EnvAction,
        envvar=loadtype_envvar,
        type=str,
        choices=list(load_types.keys()),
        default="new",
        help=f"""
        How the data should be loaded into Redis:\n{loadtype_help} (can also be
        specified using the {loadtype_envvar} environment variable).
        """,
    )

    sequence_types = {
        "chromosome": "full nuclear chromosomes",
        "supercontig": "scaffolds and contigs",
        "chloroplast": "chloroplast organelle",
        "mitochondrion": "mitochondrial organelle",
    }
    # TODO: add "all" option
    # TODO: prevent argparse from removing line breaks in help text
    sequencetypes_help = "".join(
        [
            f"\t{type} - {description} \n "
            for type, description in sequence_types.items()
        ]
    )
    sequencetypes_envvar = "SEQUENCE_TYPES"
    parser.add_argument(
        "--sequence-types",
        dest="sequence_types",
        action=EnvAction,
        envvar=sequencetypes_envvar,
        type=str,
        nargs="+",
        choices=list(sequence_types.keys()),
        default="chromosome",
        help=f"""
        What sequence types should be loaded into Redis:\n{sequencetypes_help} (can also
        be specified using the {sequencetypes_envvar} environment variable).
        """,
    )

    # Chado args
    chado_parser = subparsers.add_parser(
        "chado",
        help="Load data from a Chado (PostgreSQL) database.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    chado_parser.set_defaults(command=chado)
    pdb_envvar = "POSTGRES_DATABASE"
    chado_parser.add_argument(
        "--postgres-database",
        dest="postgres_database",
        action=EnvAction,
        envvar=pdb_envvar,
        type=str,
        default="chado",
        help=f"""
        The PostgreSQL database (can also be specified using the {pdb_envvar}
        environment variable).
        """,
    )
    puser_envvar = "POSTGRES_USER"
    chado_parser.add_argument(
        "--postgres-user",
        dest="postgres_user",
        action=EnvAction,
        envvar=puser_envvar,
        type=str,
        default="chado",
        help=f"""
        The PostgreSQL username (can also be specified using the {puser_envvar}
        environment variable).
        """,
    )
    ppassword_envvar = "POSTGRES_PASSWORD"
    chado_parser.add_argument(
        "--postgres-password",
        dest="postgres_password",
        action=EnvAction,
        envvar=ppassword_envvar,
        type=str,
        default=None,
        help=f"""
        The PostgreSQL password (can also be specified using the {ppassword_envvar}
        environment variable).
        """,
    )
    phost_envvar = "POSTGRES_HOST"
    chado_parser.add_argument(
        "--postgres-host",
        dest="postgres_host",
        action=EnvAction,
        envvar=phost_envvar,
        type=str,
        default="localhost",
        help=f"""
        The PostgreSQL host (can also be specified using the {phost_envvar} environment
        variable).
        """,
    )
    pport_envvar = "POSTGRES_PORT"
    chado_parser.add_argument(
        "--postgres-port",
        dest="postgres_port",
        action=EnvAction,
        envvar=pport_envvar,
        type=int,
        default=5432,
        help=f"""
        The PostgreSQL port (can also be specified using the {pport_envvar} environment
        variable).
        """,
    )
    chado_parser.add_argument(
        "--uniquename",
        action="store_true",
        help="""
        Load names from the uniquename field of the Chado feature table, otherwise use
        the name field.
        """,
    )
    chado_parser.set_defaults(uniquename=False)

    # GFF args
    gff_parser = subparsers.add_parser(
        "gff",
        help="Load data GFF files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    gff_parser.set_defaults(command=gff)
    genus_envvar = "GENUS"
    gff_parser.add_argument(
        "--genus",
        required=True,
        action=EnvAction,
        envvar=genus_envvar,
        type=str,
        default=argparse.SUPPRESS,  # removes "(default: None)" from help text
        help=f"""
        The genus of the organism being loaded (can also be specified using the
        {genus_envvar} environment variable).
        """,
    )
    species_envvar = "SPECIES"
    gff_parser.add_argument(
        "--species",
        required=True,
        action=EnvAction,
        envvar=species_envvar,
        type=str,
        default=argparse.SUPPRESS,  # removes "(default: None)" from help text
        help=f"""
        The species of the organism being loaded (can also be specified using the
        {species_envvar} environment variable).
        """,
    )
    strain_envvar = "STRAIN"
    gff_parser.add_argument(
        "--strain",
        action=EnvAction,
        envvar=strain_envvar,
        type=str,
        help=f"""
        The strain of the organism being loaded (can also be specified using the
        {strain_envvar} environment variable).
        """,
    )
    gffgene_envvar = "GENE_GFF_FILE"
    gff_parser.add_argument(
        "--gene-gff",
        dest="gene_gff",
        required=True,
        action=EnvAction,
        envvar=gffgene_envvar,
        default=argparse.SUPPRESS,  # removes "(default: None)" from help text
        help=f"""
        The GFF(.gz) file containing gene records (can also be specified using the
        {gffgene_envvar} environment variable).
        """,
    )
    gffchr_envvar = "CHROMOSOME_GFF_FILE"
    gff_parser.add_argument(
        "--chromosome-gff",
        dest="chromosome_gff",
        required=True,
        action=EnvAction,
        envvar=gffchr_envvar,
        default=argparse.SUPPRESS,  # removes "(default: None)" from help text
        help=f"""
        The GFF(.gz) file containing chromosome/supercontig records (can also be
        specified using the {gffchr_envvar} environment variable).
        """,
    )
    gfa_envvar = "GFA_FILE"
    gff_parser.add_argument(
        "--gfa",
        required=True,
        action=EnvAction,
        envvar=gfa_envvar,
        default=argparse.SUPPRESS,  # removes "(default: None)" from help text
        help=f"""
        The GFA(.gz) file containing gene-gene family associations (can also be
        specified using the {gfa_envvar} environment variable).
        """,
    )

    return parser.parse_args()


def main():
    # parse command-line arguments
    args = parseArgs()

    # run the specified command in the context of the RediSearch loader
    kwargs = {
        "host": args.redis_host,
        "port": args.redis_port,
        "db": args.redis_db,
        "password": args.redis_password,
        "load_type": args.load_type,
        "sequence_types": args.sequence_types,
        "no_save": args.no_save,
        "chunk_size": args.chunk_size,
    }
    with RediSearchLoader(**kwargs) as loader:
        args.command(loader, args)


if __name__ == "__main__":
    main()
