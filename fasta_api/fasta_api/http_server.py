# http_server.py
import aiohttp_cors
from aiohttp import web
from importlib import resources
import yaml


async def http_index(request):
    return web.Response(text="Index")


async def http_help(request):
    resources = [str(resource) for resource in request.app.router.resources()]
    return web.json_response(resources)

async def http_request(request, fasta_func, match_info=[]):
    request_func_args = (lambda ml: [
        int(request.match_info.get(m)) if m in ["start", "stop", "end"] else request.match_info.get(m) for m in ml
    ])(match_info)
    url = request.match_info.get("url", "")
    handler = request.app["handler"]
    if hasattr(handler, fasta_func):
        request_func = getattr(handler, fasta_func)
        fasta_result = request_func(url, *request_func_args)
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

async def http_vcf_contigs(request):
    return await http_request(request, "vcf_contigs")

async def http_vcf_features(request):
    return await http_request(request, "vcf_features", ["seqid", "start", "end"])

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
    return await http_request(request, "alignment_contig", ["contig", "start", "stop"])

async def http_alignment_count_coverage(request):
    return await http_request(request, "alignment_count_coverage", ["contig", "start", "stop"])

async def http_alignment_fetch(request):
    return await http_request(request, "alignment_fetch", ["contig", "start", "stop"])

async def http_alignment_reference_lengths(request):
    return await http_request(request, "alignment_reference_lengths", ["reference"])

def run_http_server(host, port, handler):
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
    # Load the YAML file
    files = resources.files('fasta_api')
    api_path = files / 'fasta_api.yaml'
    with api_path.open('r') as file:
        spec = yaml.safe_load(file)

    # Iterate through the paths and add routes
    for path, methods in spec["paths"].items():
        for method, details in methods.items():
            if method == "get":
                operation_id = details.get("operationId")
                if operation_id:
                    route = app.router.add_get(path, globals()[operation_id])
                    cors.add(route)
    # run the app
    web.run_app(app)
