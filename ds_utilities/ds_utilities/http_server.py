# http_server.py
from pathlib import Path

import aiohttp_cors
import yaml
from aiohttp import web


async def http_index(request):
    return web.Response(text="Index")


async def http_help(request):
    resources = [str(resource) for resource in request.app.router.resources()]
    return web.json_response(resources)


async def http_request(request, fasta_func, match_info=[], query_info={}):
    # A handler is registered against multiple route patterns (with and without
    # coordinates); match_info only has start/end when the coord-bearing route
    # fired, so skip the int cast when the slot is absent rather than calling
    # int(None) and 500-ing.
    def _coerce(name):
        val = request.match_info.get(name)
        if val is not None and name in ("start", "stop", "end"):
            return int(val)
        return val

    request_func_args = [_coerce(m) for m in match_info]
    # Extract query parameters with defaults
    query_args = [request.query.get(k, v) for k, v in query_info.items()]
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
    return await http_request(request, "fasta_range", ["seqid", "start", "end"])


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
    # Load the YAML file from the openapi/ tree that ships next to the
    # package (MANIFEST.in includes it). Matches dscensor's pattern — one
    # source of truth, no install-time copy step.
    api_path = Path(__file__).parent.parent / "openapi/ds_utilities/v1/ds_utilities.yaml"
    with open(api_path, "r") as file:
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
