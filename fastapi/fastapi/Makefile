.POSIX:

run:
	. venv/bin/activate && uvicorn main:app

install:
	python3 -mvenv venv
	. venv/bin/activate \
	&& pip install --upgrade --no-cache-dir pip \
	&& pip install --no-cache-dir wheel \
	&& pip install --no-cache-dir -r requirements.txt

CURL = curl --silent --show-error --fail -o /dev/null

test:
	$(CURL) http://localhost:8000/fasta/references/https://data.legumeinfo.org/Glycine/max/genomes/Wm82.gnm2.DTC4/glyma.Wm82.gnm2.DTC4.genome_main.fna.gz
	$(CURL) http://localhost:8000/fasta/fetch/glyma.Wm82.gnm2.scaffold_2709/https://data.legumeinfo.org/Glycine/max/genomes/Wm82.gnm2.DTC4/glyma.Wm82.gnm2.DTC4.genome_main.fna.gz
	$(CURL) http://localhost:8000/fasta/fetch/glyma.Wm82.gnm2.Gm01:1-100/https://data.legumeinfo.org/Glycine/max/genomes/Wm82.gnm2.DTC4/glyma.Wm82.gnm2.DTC4.genome_main.fna.gz
	$(CURL) http://localhost:8000/gff/contigs/https://data.legumeinfo.org/Glycine/max/annotations/Wm82.gnm2.ann1.RVB6/glyma.Wm82.gnm2.ann1.RVB6.gene_models_main.gff3.gz
	$(CURL) http://localhost:8000/gff/fetch/glyma.Wm82.gnm2.Gm01:1-100000/https://data.legumeinfo.org/Glycine/max/annotations/Wm82.gnm2.ann1.RVB6/glyma.Wm82.gnm2.ann1.RVB6.gene_models_main.gff3.gz
	$(CURL) http://localhost:8000/vcf/contigs/https://data.legumeinfo.org/Glycine/max/diversity/Wm82.gnm1.div.ContrerasSoto_Mora_2017/glyma.Wm82.gnm1.div.ContrerasSoto_Mora_2017.SNPs.vcf.gz
	$(CURL) http://localhost:8000/vcf/fetch/glyma.Wm82.gnm1.Gm16:1-100000/https://data.legumeinfo.org/Glycine/max/diversity/Wm82.gnm1.div.ContrerasSoto_Mora_2017/glyma.Wm82.gnm1.div.ContrerasSoto_Mora_2017.SNPs.vcf.gz
	$(CURL) http://localhost:8000/alignment/fetch/aradu.V14167.gnm2.chr01:1-100000/https://data.legumeinfo.org/Arachis/duranensis/genome_alignments/V14167.gnm2.wga.96TT/aradu.V14167.gnm2.x.araca.K10017.gnm1.96TT.bam
## Can't handle; non-standard 7-column BED
#	$(CURL) http://localhost:8000/bed/fetch/glyma.Wm82.gnm4.Gm01:1-100000/https://data.legumeinfo.org/Glycine/max/annotations/Wm82.gnm4.ann1.T8TQ/glyma.Wm82.gnm4.ann1.T8TQ.gene_models_main.bed.gz
	
