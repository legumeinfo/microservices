# https://pysam.readthedocs.io/en/latest/api.html#fasta-files
import json
import pysam
from fastapi import FastAPI, HTTPException, Request, status
import urllib
import itertools
import os

ALLOWED_URLS = os.environ.get("ALLOWED_URLS", "").split(",")

app = FastAPI()

def check_url(url):
    url = urllib.parse.unquote(url)
    if not any(url.startswith(allowed_url) for allowed_url in ALLOWED_URLS):
        print("Raise 403 exception");
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="url not allowed")
    return url

def send_400_resp(msg):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@app.get("/")
def index():
    return "fasta-api"

@app.get("/fasta/fetch/{seqid}:{start}-{end}/{url:path}")
def fasta_range(url: str, seqid: str, start: int, end: int):
    try:
        seq = pysam.FastaFile(check_url(url)).fetch(reference=seqid, start = start, end = end)
        return { "sequence" : seq }
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")
    except KeyError as e:
        send_400_resp(f"Unable to find feature: {e}")
    except ValueError as e:
        send_400_resp(f"Unable to interpret coordinates: {e}")

@app.get("/fasta/fetch/{seqid}/{url:path}")
def fasta_range(url: str, seqid: str):
    try:
        seq = pysam.FastaFile(check_url(url)).fetch(reference=seqid)
        return { "sequence" : seq }
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")
    except KeyError as e:
        send_400_resp(f"Unable to find feature: {e}")

@app.get("/fasta/references/{url:path}")
def fasta_references(url: str):
    try:
        return { "references": pysam.FastaFile(check_url(url)).references }
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")

@app.get("/fasta/lengths/{url:path}")
def fasta_lengths(url: str):
    try:
        return { "lengths": pysam.FastaFile(check_url(url)).lengths }
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")

@app.get("/fasta/nreferences/{url:path}")
def fasta_nreferences(url: str):
    try:
        return { "nreferences": pysam.FastaFile(check_url(url)).nreferences }
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")

@app.get("/gff/contigs/{url:path}")
def gff_references(url: str):
    try:
        return { "contigs": pysam.TabixFile(check_url(url)).contigs }
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")

@app.get("/gff/fetch/{seqid}:{start}-{end}/{url:path}")
def gff_features(url: str, seqid: str, start: int, end: int):
  try:
    return [ {"contig": feature.contig,
              "feature": feature.feature,
              "source": feature.source,
              "start": feature.start,
              "end": feature.end,
              "score": feature.score,
              "strand": feature.strand,
              "frame": feature.frame,
              "attributes": dict(a.split("=") for a in feature.attributes.split(";") if a != "")} 
              for feature 
              in pysam.TabixFile(check_url(url)).fetch(seqid, start, end, parser=pysam.asGFF3()) ]
  except OSError as e:
    send_400_resp(f"Unable to open file: {e}")
  except KeyError as e:
    send_400_resp(f"Unable to find feature: {e}")
  except ValueError as e:
    send_400_resp(f"Unable to find index: {e}")

@app.get("/gff/fetch/{seqid}/{url:path}")
def gff_features(url: str, seqid: str):
  try:
    return [ {"contig": feature.contig,
              "feature": feature.feature,
              "source": feature.source,
              "start": feature.start,
              "end": feature.end,
              "score": feature.score,
              "strand": feature.strand,
              "frame": feature.frame,
              "attributes": dict(a.split("=") for a in feature.attributes.split(";") if a != "")} 
              for feature 
              in pysam.TabixFile(check_url(url)).fetch(seqid, parser=pysam.asGFF3()) ]
  except OSError as e:
    send_400_resp(f"Unable to open file: {e}")
  except KeyError as e:
    send_400_resp(f"Unable to find feature: {e}")

#As itemRgb, blockSizes, and blockStarts columns are rare, their types have not been determined and may change.
@app.get("/bed/fetch/{seqid}:{start}-{end}/{url:path}")
def bed_features(url: str, seqid: str, start: int, end: int):
  try:
    bedcols = ('contig', 'start', 'end', 'name', 'score', 'strand', 'thickStart', 'thickEnd', 'itemRGB', 'blockCount', 'blockSizes', 'blockStarts')
    return [dict(itertools.starmap(lambda k,v: (k, int(v) if k in ['start', 'end', 'thickStart', 'thickEnd'] else float(v) if k == 'score' else v), zip(bedcols, feature)))
              for feature 
              in pysam.TabixFile(check_url(url)).fetch(seqid, start, end, parser=pysam.asBed()) ]
  except OSError as e:
    send_400_resp(f"Unable to open file: {e}")
  except KeyError as e:
    send_400_resp(f"Unable to find feature: {e}")
  except ValueError as e:
    send_400_resp(f"Unable to find index: {e}")

@app.get("/bed/fetch/{seqid}/{url:path}")
def bed_features(url: str, seqid: str):
  try:
    bedcols = ('contig', 'start', 'end', 'name', 'score', 'strand', 'thickStart', 'thickEnd', 'itemRGB', 'blockCount', 'blockSizes', 'blockStarts')
    return [dict(itertools.starmap(lambda k,v: (k, int(v) if k in ['start', 'end', 'thickStart', 'thickEnd'] else float(v) if k == 'score' else v), zip(bedcols, feature)))
              for feature 
              in pysam.TabixFile(check_url(url)).fetch(seqid, parser=pysam.asBed()) ]
  except OSError as e:
    send_400_resp(f"Unable to open file: {e}")
  except KeyError as e:
    send_400_resp(f"Unable to find feature: {e}")

@app.get("/vcf/contigs/{url:path}")
def vcf_contigs(url: str):
  try:
    return { "contigs": list(pysam.VariantFile(urllib.parse.unquote(url)).header.contigs) }
  except OSError as e:
    send_400_resp(f"Unable to open file: {e}")

@app.get("/vcf/fetch/{seqid}:{start}-{end}/{url:path}")
def vcf_features(url: str, seqid: str, start: int, end: int):
  try:
    return [ {"chrom":   feature.chrom,
              "pos":     feature.pos,
              "id":      feature.id,
              "ref":     feature.ref,
              "alts":    feature.alts,
              "qual":    feature.qual,
              "filter":  list(feature.filter),
              "info":    list(feature.info),
              "format":  list(feature.format),
              "samples": list(feature.samples),
              "alleles": feature.alleles}
              for feature 
              in pysam.VariantFile(check_url(url)).fetch(seqid, start, end) ]
  except OSError as e:
    send_400_resp(f"Unable to open file: {e}")
  except KeyError as e:
    send_400_resp(f"Unable to find feature: {e}")

@app.get("/vcf/fetch/{seqid}/{url:path}")
def vcf_features(url: str, seqid: str):
  try:
    return [ {"chrom":   feature.chrom,
              "pos":     feature.pos,
              "id":      feature.id,
              "ref":     feature.ref,
              "alts":    feature.alts,
              "qual":    feature.qual,
              "filter":  list(feature.filter),
              "info":    list(feature.info),
              "format":  list(feature.format),
              "samples": list(feature.samples),
              "alleles": feature.alleles}
              for feature 
              in pysam.VariantFile(check_url(url)).fetch(seqid) ]
  except OSError as e:
    send_400_resp(f"Unable to open file: {e}")
  except KeyError as e:
    send_400_resp(f"Unable to find feature: {e}")

@app.get("/alignment/references/{url:path}")
def alignment_references(url: str):
    try:
        return { "references": pysam.AlignmentFile(check_url(url)).references }
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")

@app.get("/alignment/unmapped/{url:path}")
def alignment_unmapped(url: str):
    try:
        return { "unmapped": pysam.AlignmentFile(check_url(url)).unmapped }
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")

@app.get("/alignment/nreferences/{url:path}")
def alignment_nreferences(url: str):
    try:
        return { "nreferences": pysam.AlignmentFile(check_url(url)).nreferences }
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")

@app.get("/alignment/nocoordinate/{url:path}")
def alignment_nocoordinate(url: str):
    try:
        return { "nocoordinate": pysam.AlignmentFile(check_url(url)).nocoordinate }
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")

@app.get("/alignment/mapped/{url:path}")
def alignment_mapped(url: str):
    try:
        return { "mapped": pysam.AlignmentFile(check_url(url)).mapped }
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")

@app.get("/alignment/lengths/{url:path}")
def alignment_lengths(url: str):
    try:
        return { "lengths": pysam.AlignmentFile(check_url(url)).lengths }
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")

@app.get("/alignment/index_statistics/{url:path}")
def alignment_index_statistics(url: str):
    try:
        return { "index_statistics": pysam.AlignmentFile(check_url(url)).get_index_statistics() }
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")

@app.get("/alignment/count/{contig}:{start}-{stop}/{url:path}")
def alignment_count(url: str, contig: str, start: int, stop: int):
    try:
        count = pysam.AlignmentFile(check_url(url)).count(contig, start, stop)
        return { "count": count }
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")

@app.get("/alignment/count_coverage/{contig}:{start}-{stop}/{url:path}")
def alignment_count_coverage(url: str, contig: str, start: int, stop: int):
    try:
        count_coverage = pysam.AlignmentFile(check_url(url)).count_coverage(contig, start, stop)
        return [{"A" : json.dumps([x for x in count_coverage[0]]),
                 "B" : json.dumps([x for x in count_coverage[1]]),
                 "C" : json.dumps([x for x in count_coverage[2]]),
                 "D" : json.dumps([x for x in count_coverage[3]])
                }]
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")
    except KeyError as e:
        send_400_resp(f"Unable to find feature: {e}")

@app.get("/alignment/fetch/{contig}:{start}-{stop}/{url:path}")
def alignment_fetch(url: str, contig: str, start: int, stop: int):
    try:
        return [feature.to_dict()
                for feature
                in pysam.AlignmentFile(check_url(url)).fetch(contig=contig, start = start, stop = stop) ]
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")
    except KeyError as e:
        send_400_resp(f"Unable to find feature: {e}")

@app.get("/alignment/fetch/{contig}/{url:path}")
def alignment_fetch(url: str, contig: str):
    try:
        return [feature.to_dict()
                for feature
                in pysam.AlignmentFile(check_url(url)).fetch(contig=contig) ]
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")
    except KeyError as e:
        send_400_resp(f"Unable to find feature: {e}")

@app.get("/alignment/length/{reference}/{url:path}")
def alignment_lengths(reference: str , url: str):
    try:
       return { "length": pysam.AlignmentFile(check_url(url)).get_reference_length(reference) }
    except OSError as e:
        send_400_resp(f"Unable to open file: {e}")

