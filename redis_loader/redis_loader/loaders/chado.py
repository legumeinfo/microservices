# Python
from collections import defaultdict

# dependencies
import psycopg2


def makePostgresConnectionString(database, user, password, host, port):
    """
    Creates a connection string that can be used by psycopg2 to connect to a
    PostgreSQL database.

    Parameters:
      database (str): The name of the database to connect to.
      user (str): The name of the user to connect as.
      password (str, optional): The password of the user.
      host (str, optional): The host to connect to.
      port (int): The port on the host to connect to.

    Returns:
      str: A libpq connection string.
    """

    db_string = f"dbname={database} user={user}"

    if password is not None:
        db_string += f" password={password}"
    if host is not None:
        db_string += f" host={host}"
    if port is not None:
        db_string += f" port={port}"

    return db_string


def getCvterm(c, name, cv=None):
    """
    Loads a CV term from a Chado (PostgreSQL) database by name and, optionally, by
    CV name.

    Parameters:
      c (psycopg2.cursor): A cursor associated with a connection to a PostgreSQL
        database.
      name (str): The name of the CV term to be loaded.
      cv (str, optional): The name a CV term's CV must have.

    Returns:
      int: The Chado database ID of the specified CV term.
    """

    # get the cvterm
    query = "SELECT cvterm_id " "FROM cvterm " "WHERE name='" + name + "'"
    if cv is not None:
        query += " AND cv_id = (select cv_id from cv where name='" + cv + "')"
    query += ";"
    c.execute(query)
    # does it exist?
    if not c.rowcount:
        raise Exception('Failed to retrieve the "' + name + '" cvterm entry')
    (term,) = c.fetchone()

    return term


def transferChromosomes(
    postgres_connection, redisearch_loader, uniquename, sequence_types
):
    """
    Loads chromosomes from a Chado (PostgreSQL) database into a RediSearch
    database.

    Parameters:
      postgres_connection (psycopg2.connection): A connection to the PostgreSQL
        database to load data from.
      redisearch_loader (RediSearchLoader): The loader to use to load data into
        RediSearch.
      uniquename (bool): Whether or not the chromosome names should come from the
        "uniquename" field of the Chado Feature table.

    Returns:
      dict[int, str]: A dictionary mapping Chado database IDs of chromosomes to
        the name they were loaded into Redis with.
    """

    # load the data
    with postgres_connection.cursor() as c:
        # get cvterms
        sequencetype_ids = [getCvterm(c, s, "sequence") for s in sequence_types]
        # chromosome_id = getCvterm(c, 'chromosome', 'sequence')
        # supercontig_id = getCvterm(c, 'supercontig', 'sequence')

        # get all the organisms
        i = 0
        query = "SELECT organism_id, genus, species FROM organism;"
        c.execute(query)
        organism_id_map = {}
        for (
            pk,
            genus,
            species,
        ) in c:
            organism_id_map[pk] = {"genus": genus, "species": species}

        # get all the chromosomes
        name_field = "uniquename" if uniquename else "name"
        query = (
            f"SELECT feature_id, {name_field}, organism_id, seqlen "
            "FROM feature "
            "WHERE type_id IN (" + str(",".join(sequencetype_ids)) + ");"
        )
        #         'OR type_id=' + str(supercontig_id) + ';')
        c.execute(query)

        # index the chromosomes
        chromosome_id_name_map = {}
        for (
            pk,
            name,
            organism_id,
            length,
        ) in c:
            chromosome_id_name_map[pk] = name
            organism = organism_id_map[organism_id]
            redisearch_loader.indexChromosome(
                name, length, organism["genus"], organism["species"]
            )

        return chromosome_id_name_map


def transferGenes(
    postgres_connection, redisearch_loader, chromosome_id_name_map, uniquename
):
    """
    Loads genes from a Chado (PostgreSQL) database into a RediSearch database.

    Parameters:
      postgres_connection (psycopg2.connection): A connection to the PostgreSQL
        database to load data from.
      redisearch_loader (RediSearchLoader): The loader to use to load data into
        RediSearch.
      chromosome_id_name_map (dict[int, str]): A dictionary mapping Chado database
        IDs of chromosomes to the name they were loaded into Redis with.
      uniquename (bool): Whether or not the genes names should come from the
        "uniquename" field of the Chado Feature table.
    """

    with postgres_connection.cursor() as c:
        # get cvterms
        gene_id = getCvterm(c, "gene", "sequence")
        genefamily_id = getCvterm(c, "gene family")

        # get all the gene annotations
        query = (
            "SELECT feature_id, value "
            "FROM featureprop "
            "WHERE type_id=" + str(genefamily_id) + ";"
        )
        c.execute(query)
        gene_id_family_map = dict(
            (g_id, g_family)
            for (
                g_id,
                g_family,
            ) in c
        )

        # get all the genes
        name = "uniquename" if uniquename else "name"
        query = (
            f"SELECT fl.srcfeature_id, f.feature_id, f.{name}, fl.fmin, "
            "fl.fmax, fl.strand "
            "FROM featureloc fl, feature f "
            "WHERE fl.feature_id=f.feature_id "
            "AND f.type_id=" + str(gene_id) + ";"
        )
        c.execute(query)

        # prepare genes for indexing
        chromosome_genes = defaultdict(list)
        for (
            chr_id,
            g_id,
            g_name,
            g_fmin,
            g_fmax,
            g_strand,
        ) in c:
            if chr_id in chromosome_id_name_map:
                gene = {
                    "name": g_name,
                    "fmin": g_fmin,
                    "fmax": g_fmax,
                    "strand": g_strand,
                    "family": gene_id_family_map.get(g_id, ""),
                }
                chromosome_genes[chr_id].append(gene)

        # index the genes
        for chr_id, genes in chromosome_genes.items():
            chr_name = chromosome_id_name_map[chr_id]
            redisearch_loader.indexChromosomeGenes(chr_name, genes)


def loadFromChado(
    redisearch_loader, database, user, password, host, port, uniquename, sequence_types
):
    """
    Loads data from a Chado (PostgreSQL) database into a RediSearch database.

    Parameters:
      redisearch_loader (RediSearchLoader): The loader to use to load data into
        RediSearch.
      database (str): The name of the PostgreSQL database to load data from.
      user (str): The user to connect to the PostgreSQl database as.
      password (str): The password to use when connecting to the PostgreSQL
        database.
      host (str): The host the PostgreSQL database is on.
      post (int): The port to connect to on the host the PostgreSQL database is
        on.
      uniquename (bool): Whether or not the genes names should come from the
        "uniquename" field of the Chado Feature table.
    """

    # connect to Postgres
    postgres_connection_string = makePostgresConnectionString(
        database, user, password, host, port
    )
    with psycopg2.connect(postgres_connection_string) as postgres_connection:
        # load chromosomes
        chromosome_id_name_map = transferChromosomes(
            postgres_connection, redisearch_loader, uniquename, sequence_types
        )
        # load genes
        transferGenes(
            postgres_connection, redisearch_loader, chromosome_id_name_map, uniquename
        )
