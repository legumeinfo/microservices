# request_handler.py
import itertools
import json
import os
import urllib

import pysam

ALLOWED_URLS = os.environ.get("ALLOWED_URLS", "").split(",")


class RequestHandler:
    def __init__(self):
        pass

    def check_url(self, url):
        url = urllib.parse.unquote(url)
        if not any(url.startswith(allowed_url) for allowed_url in ALLOWED_URLS):
            return {"error": "url not allowed or missing query parameters",
                    "status": 403}
        return url

    def send_400_resp(self, msg):
        return {"error": msg, "status": 400}

    def index(self):
        return "fasta_api"

    def fasta_range(self, url: str, seqid: str, start: int = None, end: int = None):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            seq = pysam.FastaFile(url).fetch(reference=seqid, start=start, end=end)
            return {"sequence": seq}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")
        except KeyError as e:
            return self.send_400_resp(f"Unable to find feature: {e}")
        except ValueError as e:
            return self.send_400_resp(f"Unable to interpret coordinates: {e}")

    def fasta_references(self, url: str):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return {"references": pysam.FastaFile(url).references}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")

    def fasta_lengths(self, url: str):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return {"lengths": pysam.FastaFile(url).lengths}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")

    def fasta_nreferences(self, url: str):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return {"nreferences": pysam.FastaFile(url).nreferences}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")

    def gff_references(self, url: str):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return {"contigs": pysam.TabixFile(url).contigs}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")

    def gff_features(self, url: str, seqid: str, start: int = None, end: int = None):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return [
                {
                    "contig": feature.contig,
                    "feature": feature.feature,
                    "source": feature.source,
                    "start": feature.start,
                    "end": feature.end,
                    "score": feature.score,
                    "strand": feature.strand,
                    "frame": feature.frame,
                    "attributes": dict(
                        a.split("=") for a in feature.attributes.split(";") if a != ""
                    ),
                }
                for feature in pysam.TabixFile(url).fetch(
                    seqid, start, end, parser=pysam.asGFF3()
                )
            ]
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")
        except KeyError as e:
            return self.send_400_resp(f"Unable to find feature: {e}")
        except ValueError as e:
            return self.send_400_resp(f"Unable to find index: {e}")

    def bed_features(self, url: str, seqid: str, start: int = None, end: int = None):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            bedcols = (
                "contig",
                "start",
                "end",
                "name",
                "score",
                "strand",
                "thickStart",
                "thickEnd",
                "itemRGB",
                "blockCount",
                "blockSizes",
                "blockStarts",
            )
            return [
                dict(
                    itertools.starmap(
                        lambda k, v: (
                            k,
                            int(v)
                            if k in ["start", "end", "thickStart", "thickEnd"]
                            else float(v)
                            if k == "score"
                            else v,
                        ),
                        zip(bedcols, feature),
                    )
                )
                for feature in pysam.TabixFile(url).fetch(
                    seqid, start, end, parser=pysam.asBed()
                )
            ]
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")
        except KeyError as e:
            return self.send_400_resp(f"Unable to find feature: {e}")
        except ValueError as e:
            return self.send_400_resp(f"Unable to find index: {e}")

    def vcf_contigs(self, url: str):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return {"contigs": list(pysam.VariantFile(url).header.contigs)}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")

    def vcf_features(self, url: str, seqid: str, start: int = None, end: int = None):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return [
                {
                    "chrom": feature.chrom,
                    "pos": feature.pos,
                    "id": feature.id,
                    "ref": feature.ref,
                    "alts": feature.alts,
                    "qual": feature.qual,
                    "filter": list(feature.filter),
                    "info": list(feature.info),
                    "format": list(feature.format),
                    "samples": list(feature.samples),
                    "alleles": feature.alleles,
                }
                for feature in pysam.VariantFile(url).fetch(seqid, start, end)
            ]
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")
        except KeyError as e:
            return self.send_400_resp(f"Unable to find feature: {e}")

    def alignment_references(self, url: str):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return {"references": pysam.AlignmentFile(url).references}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")

    def alignment_unmapped(self, url: str):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return {"unmapped": pysam.AlignmentFile(url).unmapped}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")

    def alignment_nreferences(self, url: str):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return {"nreferences": pysam.AlignmentFile(url).nreferences}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")

    def alignment_nocoordinate(self, url: str):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return {"nocoordinate": pysam.AlignmentFile(url).nocoordinate}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")

    def alignment_mapped(self, url: str):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return {"mapped": pysam.AlignmentFile(url).mapped}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")

    def alignment_lengths(self, url: str):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return {"lengths": pysam.AlignmentFile(url).lengths}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")

    def alignment_index_statistics(self, url: str):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return {"index_statistics": pysam.AlignmentFile(url).get_index_statistics()}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")

    def alignment_count(self, url: str, contig: str, start: int, stop: int):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            count = pysam.AlignmentFile(url).count(contig, start, stop)
            return {"count": count}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")

    def alignment_count_coverage(self, url: str, contig: str, start: int, stop: int):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            count_coverage = pysam.AlignmentFile(url).count_coverage(
                contig, start, stop
            )
            return [
                {
                    "A": json.dumps([x for x in count_coverage[0]]),
                    "B": json.dumps([x for x in count_coverage[1]]),
                    "C": json.dumps([x for x in count_coverage[2]]),
                    "D": json.dumps([x for x in count_coverage[3]]),
                }
            ]
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")
        except KeyError as e:
            return self.send_400_resp(f"Unable to find feature: {e}")

    def alignment_fetch(
        self, url: str, contig: str, start: int = None, stop: int = None
    ):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return [
                feature.to_dict()
                for feature in pysam.AlignmentFile(url).fetch(
                    contig=contig, start=start, stop=stop
                )
            ]
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")
        except KeyError as e:
            return self.send_400_resp(f"Unable to find feature: {e}")

    def alignment_reference_lengths(self, reference: str, url: str):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return {"length": pysam.AlignmentFile(url).get_reference_length(reference)}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")

            return {"unmapped": pysam.AlignmentFile(url).unmapped}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")
