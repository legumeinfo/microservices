# http_server.py
from importlib import resources

import aiohttp_cors
import yaml
from aiohttp import web


async def http_index(request):
    return web.Response(text="Index")


async def http_help(request):
    resources = [str(resource) for resource in request.app.router.resources()]
    return web.json_response(resources)


# Coordinate-shaped parameter names that get int-coerced wherever they appear
# (path or query). Listed centrally so adding e.g. /vcf/alleles or a future
# range-shaped endpoint doesn't need to rediscover the convention.
_INT_PARAMS = frozenset({"start", "stop", "end"})


def _coerce_int(name, raw, default=None):
    """Best-effort int-coerce; return default for None or empty-string."""
    if raw is None or raw == "":
        return default
    if name in _INT_PARAMS:
        return int(raw)
    return raw


async def http_request(request, fasta_func, match_info=[], query_info={}):
    # match_info only carries start/end when the coord-bearing route fired, so
    # skip the int cast when the slot is absent rather than calling int(None).
    request_func_args = [_coerce_int(m, request.match_info.get(m)) for m in match_info]
    # Query params with their declared defaults; coordinate-named ones also
    # get int-coerced so handlers can receive them as the int type their
    # pysam calls require.
    query_args = [
        _coerce_int(k, request.query.get(k), default=v) for k, v in query_info.items()
    ]
    url = request.match_info.get("url", "")
    handler = request.app["handler"]
    if hasattr(handler, fasta_func):
        request_func = getattr(handler, fasta_func)
        fasta_result = request_func(url, *request_func_args, *query_args)
        if "error" in fasta_result:
            return web.json_response(fasta_result, status=fasta_result["status"])
        return web.json_response(fasta_result)
    else:
        return web.Response(status=404, text=f"Handler has no method '{fasta_func}'")


async def http_fasta_range(request):
    # start/end now live in the query string. Two reasons: (1) embedding `:` /
    # `-` as in-segment separators (the old /fasta/fetch/{seqid}:{start}-{end}
    # form) clashes with clients that run encodeURIComponent on the region —
    # the encoded `%3A` doesn't match aiohttp's pattern matcher, falling
    # through to the no-coord route with the whole "seqid:start-end" string
    # treated as the contig name. (2) Optional integer ranges are the
    # canonical use-case for query parameters anyway.
    return await http_request(
        request,
        "fasta_range",
        ["seqid"],
        {"start": None, "end": None},
    )


async def http_fasta_references(request):
    return await http_request(request, "fasta_references")


async def http_fasta_lengths(request):
    return await http_request(request, "fasta_lengths")


async def http_fasta_nreferences(request):
    return await http_request(request, "fasta_nreferences")


async def http_gff_references(request):
    return await http_request(request, "gff_references")


async def http_gff_features(request):
    return await http_request(request, "gff_features", ["seqid", "start", "end"])


async def http_bed_features(request):
    return await http_request(request, "bed_features", ["seqid", "start", "end"])


async def http_bed_lookup_gene(request):
    return await http_request(
        request,
        "bed_lookup_gene",
        ["gene_id"],
        {"longest": "false"},
    )


async def http_bed_lookup_gene_region(request):
    return await http_request(
        request,
        "bed_lookup_gene_region",
        ["gene_id", "seqid", "start", "end"],
        {"longest": "false"},
    )


async def http_vcf_contigs(request):
    return await http_request(request, "vcf_contigs")


async def http_vcf_features(request):
    return await http_request(request, "vcf_features", ["seqid", "start", "end"])


async def http_vcf_samples(request):
    return await http_request(request, "vcf_samples")


async def http_vcf_alleles(request):
    return await http_request(
        request,
        "vcf_alleles",
        ["seqid", "start", "end"],
        {"samples": None, "encoding": "hap"},
    )


async def http_alignment_references(request):
    return await http_request(request, "alignment_references")


async def http_alignment_unmapped(request):
    return await http_request(request, "alignment_unmapped")


async def http_alignment_nreferences(request):
    return await http_request(request, "alignment_nreferences")


async def http_alignment_nocoordinate(request):
    return await http_request(request, "alignment_nocoordinate")


async def http_alignment_mapped(request):
    return await http_request(request, "alignment_mapped")


async def http_alignment_lengths(request):
    return await http_request(request, "alignment_lengths")


async def http_alignment_index_statistics(request):
    return await http_request(request, "alignment_index_statistics")


async def http_alignment_count(request):
    return await http_request(request, "alignment_count", ["contig", "start", "stop"])


async def http_alignment_count_coverage(request):
    return await http_request(
        request, "alignment_count_coverage", ["contig", "start", "stop"]
    )


async def http_alignment_fetch(request):
    return await http_request(request, "alignment_fetch", ["contig", "start", "stop"])


async def http_alignment_reference_lengths(request):
    return await http_request(request, "alignment_reference_lengths", ["reference"])


async def run_http_server(host, port, handler):
    # make the app
    app = web.Application()
    app["handler"] = handler
    # define the route and enable CORS
    cors = aiohttp_cors.setup(
        app,
        defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        },
    )
    # Resolve the OpenAPI spec via importlib.resources so the file is found
    # whether the package was installed editable (pip install -e .) or as a
    # built wheel into site-packages (pip install . / docker image). The
    # openapi/ tree ships under the package itself, so the same path works
    # in both cases. The earlier Path(__file__).parent.parent approach only
    # worked in editable mode and broke installs by raising FileNotFoundError.
    api_path = (
        resources.files("ds_utilities") / "openapi/ds_utilities/v1/ds_utilities.yaml"
    )
    with api_path.open("r") as file:
        spec = yaml.safe_load(file)

    # Iterate through the paths and add routes
    for path, methods in spec["paths"].items():
        for method, details in methods.items():
            if method == "get":
                operation_id = details.get("operationId")
                if operation_id:
                    route = app.router.add_get(path, globals()[operation_id])
                    cors.add(route)
    # AppRunner + TCPSite respects the host/port args and lets the surrounding
    # uvloop in __main__.py keep running; web.run_app() would spawn its own
    # event loop and ignore both. Matches the genes / chromosome / gene_search
    # pattern used by the rest of the microservices.
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
