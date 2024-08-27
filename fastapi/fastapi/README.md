Minimal example of a partial [FastAPI](https://fastapi.tiangolo.com/)-generated API for querying a BGZF-compressed & faidx-indexed FASTA file using [pysam](https://pysam.readthedocs.io/).

## Example

```
% make install # one-time environment setup
...
% make
```

In another terminal, execute `make test`, or manually enter the following commands:
```
$ curl http://localhost:8000/fasta/references/https://data.legumeinfo.org/Glycine/max/genomes/Wm82.gnm2.DTC4/glyma.Wm82.gnm2.DTC4.genome_main.fna.gz
{"references":["glyma.Wm82.gnm2.Gm01","glyma.Wm82.gnm2.Gm02",...
$ curl http://localhost:8000/fasta/fetch/glyma.Wm82.gnm2.scaffold_2709/https://data.legumeinfo.org/Glycine/max/genomes/Wm82.gnm2.DTC4/glyma.Wm82.gnm2.DTC4.genome_main.fna.gz 
$ curl http://localhost:8000/fasta/fetch/glyma.Wm82.gnm2.Gm01:1-100/https://data.legumeinfo.org/Glycine/max/genomes/Wm82.gnm2.DTC4/glyma.Wm82.gnm2.DTC4.genome_main.fna.gz 
{"sequence":"GTTTGGTGTTTGGGTTTTAGGTTTTAGGTTTTAGGTTTTACGGTTTAGGGTTTATGGTTTATGGTTTAGGGTTTAGGGTTAGGAAATAATTTGGGTCTT"}
$ curl http://localhost:8000/gff/contigs/https://data.legumeinfo.org/Glycine/max/annotations/Wm82.gnm2.ann1.RVB6/glyma.Wm82.gnm2.ann1.RVB6.gene_models_main.gff3.gz 
{"contigs":["glyma.Wm82.gnm2.Gm01","glyma.Wm82.gnm2.Gm02",...
$ curl http://localhost:8000/gff/fetch/glyma.Wm82.gnm2.Gm01:1-100000/https://data.legumeinfo.org/Glycine/max/annotations/Wm82.gnm2.ann1.RVB6/glyma.Wm82.gnm2.ann1.RVB6.gene_models_main.gff3.gz
[{"contig":"glyma.Wm82.gnm2.Gm01","feature":"gene","source":"phytozomev10","start":27354,"end":28320,"score":null,"strand":"-","frame":null,"attributes":"ID=glyma.Wm82.gnm2.ann1.Glyma.01G000100;...
$ curl http://localhost:8000/vcf/contigs/https://data.legumeinfo.org/Glycine/max/diversity/Wm82.gnm1.div.ContrerasSoto_Mora_2017/glyma.Wm82.gnm1.div.ContrerasSoto_Mora_2017.SNPs.vcf.gz
{"contigs":["scaffold_148","scaffold_2079","scaffold_639","scaffold_648","scaffold_1961","scaffold_1902","scaffold_1416","scaffold_1649","scaffold_2267",...
$ curl http://localhost:8000/vcf/fetch/glyma.Wm82.gnm1.Gm16:1-100000/https://data.legumeinfo.org/Glycine/max/diversity/Wm82.gnm1.div.ContrerasSoto_Mora_2017/glyma.Wm82.gnm1.div.ContrerasSoto_Mora_2017.SNPs.vcf.gz
[{"chrom":"glyma.Wm82.gnm1.Gm16","pos":35846,"id":"M4191","ref":"A","alts":["G"],"qual":null,"filter":[],"info":[],"format":["GT"],"samples":["ANTA","A6001-RR"...
$ curl http://localhost:8000/alignment/fetch/aradu.V14167.gnm2.chr01:1-100000/https://data.legumeinfo.org/Arachis/duranensis/genome_alignments/V14167.gnm2.wga.96TT/aradu.V14167.gnm2.x.araca.K10017.gnm1.96TT.bam
[{"name":"araca.K10017.gnm1.chr01","flag":"2048","ref_name":"aradu.V14167.gnm2.chr01","ref_pos":"45008","map_quality":"60","cigar":"191657H159M11I364M10D109M2D685M10I111...
```

## ALLOWED_URLS

In production, the `ALLOWED_URLS` environment variable can be set to a comma-separated list of target URL prefixes to allow.
If the requested URL begins with any of the URLs in the list, the request will be allowed; otherwise, an HTTP 403 status code will result.

```
$ ALLOWED_URLS='https://data.legumeinfo.org/,https://www.soybase.org/data/v2/' make
... `make test` works ...
$ ALLOWED_URLS='https://www.example.com/' make
... `make test` fails ...
```

## API documentation

See also http://localhost:8000/docs for the FastAPI [Interactive API docs](https://fastapi.tiangolo.com/#interactive-api-docs)
