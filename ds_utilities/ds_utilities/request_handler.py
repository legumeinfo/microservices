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
            return {
                "error": "url not allowed or missing query parameters",
                "status": 403,
            }
        return url

    def send_400_resp(self, msg):
        return {"error": msg, "status": 400}

    def index(self):
        return "ds_utilities"

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

    def vcf_samples(self, url: str):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return {"samples": list(pysam.VariantFile(url).header.samples)}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")
        except KeyError as e:
            return self.send_400_resp(f"Unable to find feature: {e}")

    def format_vcf_genotype(self, genotype):
        """Format genotype as VCF string (e.g., '0/1', '1/1').

        Args:
            genotype: Tuple of allele indices from pysam (e.g., (0, 1))

        Returns:
            VCF-style genotype string, or './.' for missing data
        """
        if genotype is None or None in genotype:
            return "./."
        return "/".join(str(g) for g in genotype)

    def format_hapmap_genotype(self, ref, alts, genotype):
        """Format genotype as HapMap string (e.g., 'AA', 'AT').

        Args:
            ref: Reference allele string
            alts: List of alternate allele strings
            genotype: Tuple of allele indices from pysam

        Returns:
            HapMap-style allele string, or 'NN' for missing data
        """
        if genotype is None or None in genotype:
            return "NN"

        all_alleles = [ref] + list(alts) if alts else [ref]
        try:
            return "".join(all_alleles[g] for g in genotype if g < len(all_alleles))
        except (IndexError, TypeError):
            return "NN"

    def vcf_alleles(
        self, url: str, seqid: str, start: int, end: int,
        samples: str = None, encoding: str = "hap"
    ):
        """Extract alleles for specified samples in a genomic region.

        Args:
            url: URL-encoded path to VCF file
            seqid: Chromosome/contig identifier
            start: Start position (1-based)
            end: End position (1-based, inclusive)
            samples: Comma-separated sample names (optional, defaults to all)
            encoding: Output format - 'hap', 'vcf', or 'both'

        Returns:
            JSON object with variants and formatted genotypes
        """
        url = self.check_url(url)
        if isinstance(url, dict):
            return url

        # Validate encoding parameter
        if encoding not in ("hap", "vcf"):
            return self.send_400_resp(
                f"Invalid encoding '{encoding}'. Use 'hap' or 'vcf'."
            )

        try:
            with pysam.VariantFile(url) as vcf:
                # Determine which samples to include
                available_samples = set(vcf.header.samples)

                if samples:
                    requested = [s.strip() for s in samples.split(",")]
                    valid_samples = [s for s in requested if s in available_samples]
                    invalid_samples = [s for s in requested if s not in available_samples]
                else:
                    valid_samples = list(vcf.header.samples)
                    invalid_samples = []

                if not valid_samples:
                    return self.send_400_resp(
                        f"No valid samples found. Available: {', '.join(sorted(available_samples))}"
                    )

                # Extract variants
                variants = []
                for record in vcf.fetch(seqid, start - 1, end):  # pysam uses 0-based
                    ref = record.ref
                    alts = list(record.alts) if record.alts else []

                    genotypes = {}
                    for sample_name in valid_samples:
                        gt = record.samples[sample_name]["GT"]

                        if encoding == "vcf":
                            genotypes[sample_name] = self.format_vcf_genotype(gt)
                        else:  # hap
                            genotypes[sample_name] = self.format_hapmap_genotype(
                                ref, alts, gt
                            )

                    variants.append({
                        "position": record.pos,
                        "ref": ref,
                        "alt": ",".join(alts) if alts else ".",
                        "genotypes": genotypes,
                    })

                return {
                    "region": {
                        "chromosome": seqid,
                        "start": start,
                        "end": end,
                    },
                    "encoding": encoding,
                    "samples": valid_samples,
                    "invalid_samples": invalid_samples,
                    "variant_count": len(variants),
                    "variants": variants,
                }

        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")
        except ValueError as e:
            return self.send_400_resp(f"Invalid coordinates or region: {e}")

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
