# Orchestrates yuck -> FASTA retrieval across genes (gRPC), dscensor (HTTP), and
# ds_utilities (HTTP). The genome path additionally owns the strand-aware flank
# math and reverse-complement (which deliberately do NOT live in ds_utilities).
#
# Transport lives entirely in clients.py (see § 3.1) — this module stays domain
# logic and never imports aiohttp/grpc directly.
#
# Python
import asyncio

# module
from sequences.clients import (
    ServiceError,
    fetch_fasta,
    get_files_for_prefix,
    get_gene_locations,
    make_session,
)
from sequences.fasta import (
    PRIMARY_MRNA_SUFFIX,
    clamp_flank,
    compute_flank_region,
    extract_full_yuck_prefix,
    format_fasta,
    reverse_complement,
    strand_sign,
)

VALID_TYPES = ("protein", "cds", "genome")


class RequestError(Exception):
    """A client-facing error (bad input or a fatal upstream miss). `status` is
    the HTTP code the handler should return."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


class RequestHandler:
    def __init__(self, genes_address, dscensor_url, ds_utilities_url):
        self.genes_address = genes_address
        self.dscensor_url = dscensor_url
        self.ds_utilities_url = ds_utilities_url

    async def process(self, yucks, seq_type, upstream=0, downstream=0):
        """Resolve every yuck to a sequence and return one assembled FASTA string.

        Fails the whole request (raises RequestError) if any yuck can't be
        resolved — no partial FASTA is returned."""
        if seq_type not in VALID_TYPES:
            raise RequestError(
                f"Invalid type '{seq_type}'. Use one of: {', '.join(VALID_TYPES)}.",
                status=400,
            )
        if not yucks:
            raise RequestError("No gene IDs supplied.", status=400)

        # Coerce + clamp the flanks once here so the fetch math and the record
        # header both use the actual applied values (the transport passes the raw
        # query strings, which may be None or non-numeric).
        upstream = clamp_flank(upstream)
        downstream = clamp_flank(downstream)

        # Map each yuck to its annotation prefix up front so a malformed ID fails
        # fast with a clear message before any network calls.
        try:
            prefixes = {yuck: extract_full_yuck_prefix(yuck) for yuck in yucks}
        except ValueError as e:
            raise RequestError(str(e), status=400)

        try:
            async with make_session() as session:
                # Resolve dscensor file URLs once per distinct prefix.
                files_by_prefix = await self._resolve_files(
                    session, set(prefixes.values())
                )
                # The genome path needs coordinates + strand from genes (one gRPC
                # call covers the whole batch); protein/CDS need neither.
                locations = {}
                if seq_type == "genome":
                    locations = await self._resolve_locations(yucks)
                # Fetch every record concurrently, preserving input order.
                records = await asyncio.gather(
                    *[
                        self._fetch_record(
                            session,
                            yuck,
                            seq_type,
                            files_by_prefix[prefixes[yuck]],
                            locations.get(yuck),
                            upstream,
                            downstream,
                        )
                        for yuck in yucks
                    ]
                )
        except ServiceError as e:
            raise RequestError(e.message, status=e.status)

        return format_fasta(records)

    async def _resolve_files(self, session, prefixes):
        results = await asyncio.gather(
            *[get_files_for_prefix(session, self.dscensor_url, p) for p in prefixes]
        )
        return dict(zip(prefixes, results))

    async def _resolve_locations(self, yucks):
        locations = await get_gene_locations(yucks, self.genes_address)
        missing = [y for y in yucks if y not in locations]
        if missing:
            raise RequestError(
                "The genes service has no location for: " + ", ".join(missing),
                status=404,
            )
        return locations

    async def _fetch_record(
        self, session, yuck, seq_type, files, location, upstream, downstream
    ):
        if seq_type == "genome":
            return await self._fetch_genome(
                session, yuck, files, location, upstream, downstream
            )
        return await self._fetch_protein_cds(session, yuck, seq_type, files)

    async def _fetch_protein_cds(self, session, yuck, seq_type, files):
        url = files.get(f"{seq_type}_url")
        if not url:
            raise RequestError(
                f"dscensor catalog has no {seq_type}_url for "
                f'prefix "{extract_full_yuck_prefix(yuck)}".',
                status=404,
            )
        reference = f"{yuck}{PRIMARY_MRNA_SUFFIX}"
        sequence = await fetch_fasta(session, self.ds_utilities_url, reference, url)
        return (f"{reference} {seq_type} gene={yuck}", sequence)

    async def _fetch_genome(self, session, yuck, files, location, upstream, downstream):
        url = files.get("genome_url")
        if not url:
            raise RequestError(
                f"dscensor catalog has no genome_url for "
                f'prefix "{extract_full_yuck_prefix(yuck)}".',
                status=404,
            )
        # genes fmin/fmax are 1-based inclusive (loader uses gffutils); convert to
        # the 0-based half-open span pysam (via ds_utilities) expects.
        start = location["fmin"] - 1
        end = location["fmax"]
        strand = location["strand"]
        fetch_start, fetch_end = compute_flank_region(
            start, end, strand, upstream, downstream
        )
        sequence = await fetch_fasta(
            session,
            self.ds_utilities_url,
            location["chromosome"],
            url,
            start=fetch_start,
            end=fetch_end,
        )
        # pysam silently truncates a fetch whose end runs past the reference so
        # report the span we actually got rather than the one we asked for
        fetch_end = fetch_start + len(sequence)
        # ds_utilities serves plus-strand reference bases; flip minus-strand genes
        # so the record reads 5'->3' along the transcribed strand.
        if strand == -1:
            sequence = reverse_complement(sequence)
        header = (
            f"{location['chromosome']}:{fetch_start}-{fetch_end} genome "
            f"gene={yuck} strand={strand_sign(strand)} "
            f"flanks={upstream}/{downstream}"
        )
        return (header, sequence)
