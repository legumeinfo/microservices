# Thin wrappers around the three services `sequences` orchestrates:
#   - genes        (gRPC)  -> gene location + strand for the genome path
#   - dscensor     (HTTP)  -> canonical protein/CDS/genome FASTA URLs by prefix
#   - ds_utilities (HTTP)  -> the actual bytes, via the unchanged /fasta/fetch
#
# This module is the service's transport-out boundary: it owns the aiohttp
# session factory and the gRPC channel so request_handler.py can stay free of
# transport libraries (ARCHITECTURE.md § 3.1), the same way `search` confines
# its gRPC to grpc_client.py.
#
# Python
import logging
import urllib.parse

# dependencies
import aiohttp
from grpc.experimental import aio

# module
# isort: off
# from sequences.proto.genes_service.v1 import genes_pb2, genes_pb2_grpc
# NOTE: the following imports are a temporary workaround for a known protobuf
# bug; the commented imports above should be used when the bug is fixed:
# https://github.com/protocolbuffers/protobuf/issues/10075
from sequences import proto  # noqa: F401
from genes_service.v1 import genes_pb2, genes_pb2_grpc

# isort: on


class ServiceError(Exception):
    """Raised when an upstream service fails or returns no usable result. Carries
    an HTTP-ish status so the request handler can surface a faithful code."""

    def __init__(self, message, status=502):
        super().__init__(message)
        self.message = message
        self.status = status


def make_session():
    """The aiohttp session for the dscensor/ds_utilities calls. One per request,
    reused across the batch's fetches; created here so request_handler.py never
    imports aiohttp directly (ARCHITECTURE.md § 3.1)."""
    return aiohttp.ClientSession()


async def get_gene_locations(names, address):
    """Resolve gene yucks to {name, chromosome, fmin, fmax, strand} via the genes
    service's gRPC `Get`. Returns a dict keyed by gene name; yucks the index
    doesn't know are simply absent from the reply (the caller decides whether a
    missing yuck is fatal)."""
    # Open the channel per call to support dynamic services (matches the `search`
    # microservice's client convention); the context manager closes it so we
    # don't leak a channel + its resources on every request.
    async with aio.insecure_channel(address) as channel:
        stub = genes_pb2_grpc.GenesStub(channel)
        try:
            reply = await stub.Get(genes_pb2.GenesGetRequest(names=list(names)))
        except Exception as e:
            logging.error(e)
            raise ServiceError(f"genes service request failed: {e}", status=502)
    return {
        gene.name: {
            "chromosome": gene.chromosome,
            "fmin": gene.fmin,
            "fmax": gene.fmax,
            "strand": gene.strand,
        }
        for gene in reply.genes
    }


async def get_files_for_prefix(session, base_url, prefix):
    """Fetch dscensor's canonical FASTA URLs for a full-yuck annotation prefix."""
    url = f"{base_url.rstrip('/')}/files/{urllib.parse.quote(prefix, safe='')}"
    async with session.get(url) as resp:
        if resp.status == 404:
            raise ServiceError(
                f'dscensor has no catalog entry for prefix "{prefix}".',
                status=404,
            )
        if resp.status != 200:
            raise ServiceError(
                f"dscensor /files returned HTTP {resp.status} for "
                f'prefix "{prefix}".',
                status=502,
            )
        return await resp.json()


async def fetch_fasta(session, base_url, seqid, fasta_url, start=None, end=None):
    """Fetch a single record (or slice) from ds_utilities' unchanged /fasta/fetch
    endpoint and return the raw sequence string."""
    path = (
        f"{base_url.rstrip('/')}/fasta/fetch/"
        f"{urllib.parse.quote(seqid, safe='')}/"
        f"{urllib.parse.quote(fasta_url, safe='')}"
    )
    params = {}
    if start is not None and end is not None:
        params = {"start": start, "end": end}
    async with session.get(path, params=params) as resp:
        if resp.status != 200:
            message = f"HTTP {resp.status}"
            try:
                body = await resp.json()
                if isinstance(body, dict) and body.get("error"):
                    message = body["error"]
            except Exception:
                pass
            # ds_utilities surfaces a missing reference as a 400 "Unable to find
            # feature"; treat any non-200 here as fatal for the whole batch.
            status = 404 if resp.status in (400, 404) else 502
            raise ServiceError(
                f'ds_utilities /fasta/fetch failed for "{seqid}": {message}',
                status=status,
            )
        body = await resp.json()
        sequence = body.get("sequence")
        if not isinstance(sequence, str):
            raise ServiceError(
                f'ds_utilities /fasta/fetch returned no sequence for "{seqid}".',
                status=502,
            )
        return sequence
