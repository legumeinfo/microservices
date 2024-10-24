# request_handler.py
import json
import pysam
from fastapi import HTTPException, status
import urllib
import os
import itertools

ALLOWED_URLS = os.environ.get("ALLOWED_URLS", "").split(",")

class RequestHandler:
    def __init__(self):
        pass

    def check_url(self, url):
        url = urllib.parse.unquote(url)
        if not any(url.startswith(allowed_url) for allowed_url in ALLOWED_URLS):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="url not allowed")
        return url

    def send_400_resp(self, msg):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    def index(self):
        return "fasta-api"

    def fasta_range(self, url: str, seqid: str, start: int = None, end: int = None):
        try:
            seq = pysam.FastaFile(self.check_url(url)).fetch(reference=seqid, start=start, end=end)
            return { "sequence" : seq }
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")
        except KeyError as e:
            self.send_400_resp(f"Unable to find feature: {e}")
        except ValueError as e:
            self.send_400_resp(f"Unable to interpret coordinates: {e}")

    def fasta_references(self, url: str):
        try:
            return { "references": pysam.FastaFile(self.check_url(url)).references }
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")

    def fasta_lengths(self, url: str):
        try:
            return { "lengths": pysam.FastaFile(self.check_url(url)).lengths }
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")

    def fasta_nreferences(self, url: str):
        try:
            return { "nreferences": pysam.FastaFile(self.check_url(url)).nreferences }
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")

    def gff_references(self, url: str):
        try:
            return { "contigs": pysam.TabixFile(self.check_url(url)).contigs }
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")

    def gff_features(self, url: str, seqid: str, start: int = None, end: int = None):
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
                      in pysam.TabixFile(self.check_url(url)).fetch(seqid, start, end, parser=pysam.asGFF3()) ]
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")
        except KeyError as e:
            self.send_400_resp(f"Unable to find feature: {e}")
        except ValueError as e:
            self.send_400_resp(f"Unable to find index: {e}")

    def bed_features(self, url: str, seqid: str, start: int = None, end: int = None):
        try:
            bedcols = ('contig', 'start', 'end', 'name', 'score', 'strand', 'thickStart', 'thickEnd', 'itemRGB', 'blockCount', 'blockSizes', 'blockStarts')
            return [dict(itertools.starmap(lambda k,v: (k, int(v) if k in ['start', 'end', 'thickStart', 'thickEnd'] else float(v) if k == 'score' else v), zip(bedcols, feature)))
                      for feature
                      in pysam.TabixFile(self.check_url(url)).fetch(seqid, start, end, parser=pysam.asBed()) ]
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")
        except KeyError as e:
            self.send_400_resp(f"Unable to find feature: {e}")
        except ValueError as e:
            self.send_400_resp(f"Unable to find index: {e}")

    def vcf_contigs(self, url: str):
        try:
            return { "contigs": list(pysam.VariantFile(urllib.parse.unquote(url)).header.contigs) }
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")

    def vcf_features(self, url: str, seqid: str, start: int = None, end: int = None):
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
                      in pysam.VariantFile(self.check_url(url)).fetch(seqid, start, end) ]
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")
        except KeyError as e:
            self.send_400_resp(f"Unable to find feature: {e}")

    def alignment_references(self, url: str):
        try:
            return { "references": pysam.AlignmentFile(self.check_url(url)).references }
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")

    def alignment_unmapped(self, url: str):
        try:
            return { "unmapped": pysam.AlignmentFile(self.check_url(url)).unmapped }
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")

    def alignment_nreferences(self, url: str):
        try:
            return { "nreferences": pysam.AlignmentFile(self.check_url(url)).nreferences }
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")

    def alignment_nocoordinate(self, url: str):
        try:
            return { "nocoordinate": pysam.AlignmentFile(self.check_url(url)).nocoordinate }
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")

    def alignment_mapped(self, url: str):
        try:
            return { "mapped": pysam.AlignmentFile(self.check_url(url)).mapped }
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")

    def alignment_lengths(self, url: str):
        try:
            return { "lengths": pysam.AlignmentFile(self.check_url(url)).lengths }
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")

    def alignment_index_statistics(self, url: str):
        try:
            return { "index_statistics": pysam.AlignmentFile(self.check_url(url)).get_index_statistics() }
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")

    def alignment_count(self, url: str, contig: str, start: int, stop: int):
        try:
            count = pysam.AlignmentFile(self.check_url(url)).count(contig, start, stop)
            return { "count": count }
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")

    def alignment_count_coverage(self, url: str, contig: str, start: int, stop: int):
        try:
            count_coverage = pysam.AlignmentFile(self.check_url(url)).count_coverage(contig, start, stop)
            return [{"A" : json.dumps([x for x in count_coverage[0]]),
                     "B" : json.dumps([x for x in count_coverage[1]]),
                     "C" : json.dumps([x for x in count_coverage[2]]),
                     "D" : json.dumps([x for x in count_coverage[3]])
                    }]
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")
        except KeyError as e:
            self.send_400_resp(f"Unable to find feature: {e}")

    def alignment_fetch(self, url: str, contig: str, start: int = None, stop: int = None):
        try:
            return [feature.to_dict()
                    for feature
                    in pysam.AlignmentFile(self.check_url(url)).fetch(contig=contig, start=start, stop=stop) ]
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")
        except KeyError as e:
            self.send_400_resp(f"Unable to find feature: {e}")

    def alignment_reference_lengths(self, reference: str , url: str):
        try:
           return { "length": pysam.AlignmentFile(self.check_url(url)).get_reference_length(reference) }
        except OSError as e:
            self.send_400_resp(f"Unable to open file: {e}")

