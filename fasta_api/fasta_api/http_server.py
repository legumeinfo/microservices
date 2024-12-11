# http_server.py
import aiohttp_cors
from aiohttp import web


async def http_index(request):
    return web.Response(text="Index")


async def http_help(request):
    resources = [str(resource) for resource in request.app.router.resources()]
    return web.json_response(resources)


async def http_fasta_range(request):
    seqid = request.match_info.get("seqid")
    start = request.match_info.get("start")
    end = request.match_info.get("end")
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    range = handler.fasta_range(url, seqid, int(start), int(end))
    if "error" in range:
        return web.json_response(range, status=range["status"])
    return web.json_response(range)


async def http_fasta_references(request):
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    references = handler.fasta_references(url)
    if "error" in references:
        return web.json_response(references, status=references["status"])
    return web.json_response(references)


async def http_fasta_lengths(request):
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    lengths = handler.fasta_lengths(url)
    if "error" in lengths:
        return web.json_response(lengths, status=lengths["status"])
    return web.json_response(lengths)


async def http_fasta_nreferences(request):
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    nreferences = handler.fasta_nreferences(url)
    if "error" in nreferences:
        return web.json_response(nreferences, status=nreferences["status"])
    return web.json_response(nreferences)


async def http_gff_references(request):
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    references = handler.gff_references(url)
    if "error" in references:
        return web.json_response(references, status=references["status"])
    return web.json_response(references)


async def http_gff_features(request):
    seqid = request.match_info.get("seqid")
    start = request.match_info.get("start")
    end = request.match_info.get("end")
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    features = handler.gff_features(url, seqid, int(start), int(end))
    if "error" in features:
        return web.json_response(features, status=features["status"])
    return web.json_response(features)


async def http_bed_features(request):
    seqid = request.match_info.get("seqid")
    start = request.match_info.get("start")
    end = request.match_info.get("end")
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    features = handler.bed_features(url, seqid, int(start), int(end))
    if "error" in features:
        return web.json_response(features, status=features["status"])
    return web.json_response(features)


async def http_vcf_contigs(request):
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    contigs = handler.vcf_contigs(url)
    if "error" in contigs:
        return web.json_response(contigs, status=contigs["status"])
    return web.json_response(contigs)


async def http_vcf_features(request):
    seqid = request.match_info.get("seqid")
    start = request.match_info.get("start")
    end = request.match_info.get("end")
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    features = handler.vcf_features(url, seqid, int(start), int(end))
    if "error" in features:
        return web.json_response(features, status=features["status"])
    return web.json_response(features)


async def http_alignment_references(request):
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    references = handler.alignment_references(url)
    if "error" in references:
        return web.json_response(references, status=references["status"])
    return web.json_response(references)


async def http_alignment_unmapped(request):
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    unmapped = handler.alignment_unmapped(url)
    if "error" in unmapped:
        return web.json_response(unmapped, status=unmapped["status"])
    return web.json_response(unmapped)


async def http_alignment_nreferences(request):
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    nreferences = handler.alignment_nreferences(url)
    if "error" in nreferences:
        return web.json_response(nreferences, status=nreferences["status"])
    return web.json_response(nreferences)


async def http_alignment_nocoordinate(request):
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    nocoordinate = handler.alignment_nocoordinate(url)
    if "error" in nocoordinate:
        return web.json_response(nocoordinate, status=nocoordinate["status"])
    return web.json_response(nocoordinate)


async def http_alignment_mapped(request):
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    mapped = handler.alignment_mapped(url)
    if "error" in mapped:
        return web.json_response(mapped, status=mapped["status"])
    return web.json_response(mapped)


async def http_alignment_lengths(request):
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    lengths = handler.alignment_lengths(url)
    if "error" in lengths:
        return web.json_response(lengths, status=lengths["status"])
    return web.json_response(lengths)


async def http_alignment_index_statistics(request):
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    statistics = handler.alignment_index_statistics(url)
    if "error" in statistics:
        return web.json_response(statistics, status=statistics["status"])
    return web.json_response(statistics)


async def http_alignment_count(request):
    contig = request.match_info.get("contig")
    start = request.match_info.get("start")
    stop = request.match_info.get("stop")
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    count = handler.alignment_count(url, contig, int(start), int(stop))
    if "error" in count:
        return web.json_response(count, status=count["status"])
    return web.json_response(count)


async def http_alignment_count_coverage(request):
    contig = request.match_info.get("contig")
    start = request.match_info.get("start")
    stop = request.match_info.get("stop")
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    coverage = handler.alignment_count_coverage(url, contig, int(start), int(stop))
    if "error" in coverage:
        return web.json_response(coverage, status=coverage["status"])
    return web.json_response(coverage)


async def http_alignment_fetch(request):
    contig = request.match_info.get("contig")
    start = request.match_info.get("start")
    stop = request.match_info.get("stop")
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    fetch = handler.alignment_fetch(url, contig, int(start), int(stop))
    if "error" in fetch:
        return web.json_response(fetch, status=fetch["status"])
    return web.json_response(fetch)


async def http_alignment_reference_lengths(request):
    reference = request.match_info.get("reference")
    url = request.rel_url.query.get("url", "")
    handler = request.app["handler"]
    lengths = handler.alignment_reference_lengths(url, reference)
    if "error" in lengths:
        return web.json_response(lengths, status=lengths["status"])
    return web.json_response(lengths)


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
    route = app.router.add_get("/", http_index)
    cors.add(route)
    route = app.router.add_get("/help", http_help)
    cors.add(route)
    route = app.router.add_get("/fasta/fetch/{seqid}:{start}-{end}", http_fasta_range)
    cors.add(route)
    route = app.router.add_get("/fasta/fetch/{seqid}", http_fasta_range)
    cors.add(route)
    route = app.router.add_get("/fasta/references", http_fasta_references)
    cors.add(route)
    route = app.router.add_get("/fasta/lengths", http_fasta_lengths)
    cors.add(route)
    route = app.router.add_get("/fasta/nreferences", http_fasta_nreferences)
    cors.add(route)
    route = app.router.add_get("/gff/contigs", http_gff_references)
    cors.add(route)
    route = app.router.add_get("/gff/fetch/{seqid}:{start}-{end}", http_gff_features)
    cors.add(route)
    route = app.router.add_get("/gff/fetch/{seqid}", http_gff_features)
    cors.add(route)
    route = app.router.add_get("/bed/fetch/{seqid}:{start}-{end}", http_bed_features)
    cors.add(route)
    route = app.router.add_get("/bed/fetch/{seqid}", http_bed_features)
    cors.add(route)
    route = app.router.add_get("/vcf/contigs", http_vcf_contigs)
    cors.add(route)
    route = app.router.add_get("/vcf/fetch/{seqid}:{start}-{end}", http_vcf_features)
    cors.add(route)
    route = app.router.add_get("/vcf/fetch/{seqid}", http_vcf_features)
    cors.add(route)
    route = app.router.add_get("/alignment/references", http_alignment_references)
    cors.add(route)
    route = app.router.add_get("/alignment/unmapped", http_alignment_unmapped)
    cors.add(route)
    route = app.router.add_get("/alignment/nreferences", http_alignment_nreferences)
    cors.add(route)
    route = app.router.add_get("/alignment/nocoordinate", http_alignment_nocoordinate)
    cors.add(route)
    route = app.router.add_get("/alignment/mapped", http_alignment_mapped)
    cors.add(route)
    route = app.router.add_get("/alignment/lengths", http_alignment_lengths)
    cors.add(route)
    route = app.router.add_get(
        "/alignment/index_statistics", http_alignment_index_statistics
    )
    cors.add(route)
    route = app.router.add_get(
        "/alignment/count/{contig}:{start}-{stop}", http_alignment_count
    )
    cors.add(route)
    route = app.router.add_get(
        "/alignment/count_coverage/{contig}:{start}-{stop}",
        http_alignment_count_coverage,
    )
    cors.add(route)
    route = app.router.add_get(
        "/alignment/fetch/{contig}:{start}-{stop}", http_alignment_fetch
    )
    cors.add(route)
    route = app.router.add_get("/alignment/fetch/{contig}", http_alignment_fetch)
    cors.add(route)
    route = app.router.add_get(
        "/alignment/length/{reference}", http_alignment_reference_lengths
    )
    cors.add(route)
    # run the app
    web.run_app(app)
