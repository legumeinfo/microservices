# request_handler.py
import hashlib
import itertools
import json
import os
import shutil
import threading
import time
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict

import pysam

ALLOWED_URLS = os.environ.get("ALLOWED_URLS", "").split(",")

# Per-socket-operation timeout for index downloads. Bounds a slow/hung datastore
# so a stuck download can't pin an executor thread (and the per-URL lock it
# holds) indefinitely; on timeout the open falls back to a plain remote fetch.
INDEX_DOWNLOAD_TIMEOUT = 30


class RequestHandler:
    def __init__(self, index_cache_dir=None):
        # Optional on-disk cache of remote FASTA index siblings (.fai/.gzi).
        # Opening a remote FASTA re-downloads its index over HTTPS every call,
        # and a protein/CDS .fai can be several MB; caching it once and reusing
        # it via pysam's filepath_index makes repeated opens of the same file
        # cheap. None disables caching (pysam fetches the index remotely as
        # before).
        self._index_cache_dir = Path(index_cache_dir) if index_cache_dir else None
        if self._index_cache_dir is not None:
            self._index_cache_dir.mkdir(parents=True, exist_ok=True)
        # Per-index locks so a cold-cache burst (e.g. a batch of genes hitting
        # one FASTA) downloads each index once, not once per concurrent request.
        self._index_locks_guard = threading.Lock()
        self._index_locks = defaultdict(threading.Lock)

    def _index_lock(self, key):
        with self._index_locks_guard:
            return self._index_locks[key]

    def _local_index(self, url, ext):
        """Path to a locally cached copy of ``url + ext``, downloaded on first
        use. Returns None when caching is disabled or the index can't be
        fetched, in which case the caller lets pysam fetch it remotely as
        before. The index URL inherits the already-allowlisted base URL, so it
        needs no separate check_url."""
        if self._index_cache_dir is None:
            return None
        key = hashlib.sha256(url.encode()).hexdigest()[:16] + ext
        dest = self._index_cache_dir / key
        if dest.exists():
            return str(dest)
        with self._index_lock(key):
            if dest.exists():  # another thread won the race while we waited
                return str(dest)
            tmp = dest.with_name(dest.name + ".tmp")
            try:
                # urlopen(timeout=) rather than urlretrieve (which has no timeout)
                # so a hung datastore can't stall this thread + lock forever.
                with urllib.request.urlopen(
                    url + ext, timeout=INDEX_DOWNLOAD_TIMEOUT
                ) as resp, open(tmp, "wb") as out:
                    shutil.copyfileobj(resp, out)
                os.replace(tmp, dest)  # atomic publish
                return str(dest)
            except Exception:
                tmp.unlink(missing_ok=True)
                return None

    def prune_index_cache(self, max_age_seconds):
        """Delete cached index files older than max_age_seconds (by mtime, i.e.
        download time). No-op when caching is disabled. Best-effort: entries that
        vanish mid-sweep are ignored. A file in active use keeps mtime≈download
        time, so it is only removed once it is genuinely stale and is then simply
        re-downloaded on next use."""
        if self._index_cache_dir is None:
            return
        cutoff = time.time() - max_age_seconds
        for entry in self._index_cache_dir.iterdir():
            try:
                if entry.is_file() and entry.stat().st_mtime < cutoff:
                    entry.unlink()
            except OSError:
                pass

    def _open_fasta(self, url):
        """Open a (possibly remote) FASTA, reusing locally cached index files so
        the open doesn't re-download the .fai/.gzi every call. Falls back to a
        plain remote open when the full local index set isn't available, so it
        never opens in a half-cached state."""
        kwargs = {}
        fai = self._local_index(url, ".fai")
        if fai is not None:
            if url.endswith(".gz"):
                # A bgzipped FASTA needs both .fai and .gzi; only use the local
                # pair when we have both.
                gzi = self._local_index(url, ".gzi")
                if gzi is not None:
                    kwargs["filepath_index"] = fai
                    kwargs["filepath_index_compressed"] = gzi
            else:
                kwargs["filepath_index"] = fai
        return pysam.FastaFile(url, **kwargs)

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

    def send_404_resp(self, msg: str) -> Dict[str, Any]:
        return {"error": msg, "status": 404}

    def index(self):
        return "ds_utilities"

    def fasta_range(self, url: str, seqid: str, start: int = None, end: int = None):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            seq = self._open_fasta(url).fetch(reference=seqid, start=start, end=end)
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
            return {"references": self._open_fasta(url).references}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")

    def fasta_lengths(self, url: str):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return {"lengths": self._open_fasta(url).lengths}
        except OSError as e:
            return self.send_400_resp(f"Unable to open file: {e}")

    def fasta_nreferences(self, url: str):
        url = self.check_url(url)
        if isinstance(url, dict):
            return url
        try:
            return {"nreferences": self._open_fasta(url).nreferences}
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
                            (
                                int(v)
                                if k in ["start", "end", "thickStart", "thickEnd"]
                                else float(v) if k == "score" else v
                            ),
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
        self,
        url: str,
        seqid: str,
        start: int,
        end: int,
        samples: str = None,
        encoding: str = "hap",
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
                    invalid_samples = [
                        s for s in requested if s not in available_samples
                    ]
                else:
                    valid_samples = list(vcf.header.samples)
                    invalid_samples = []

                if not valid_samples:
                    available = ", ".join(sorted(available_samples))
                    return self.send_400_resp(
                        f"No valid samples found. Available: {available}"
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

                    variants.append(
                        {
                            "position": record.pos,
                            "ref": ref,
                            "alt": ",".join(alts) if alts else ".",
                            "genotypes": genotypes,
                        }
                    )

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
