import json
import hashlib
import unittest
import urllib.request

class TestMainEndpoints(unittest.TestCase):


    def fetch_url(self, url):
        try:
            with urllib.request.urlopen(url) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            return f"HTTPError: {e.code} - {e.reason}"
        except urllib.error.URLError as e:
            return f"URLError: {e.reason}"


    # return a sha256 hash of a (JSON) response
    # for use in large/complex responses
    def response_hash(self, response):
        return hashlib.sha256(json.dumps(response, sort_keys=True).encode('utf-8')).hexdigest()


    def test_fasta_range(self):
        url = "http://localhost:8080/fasta/fetch/lotja.MG20.gnm3.Lj0:1-100/https:%2F%2Fdata.legumeinfo.org%2FLotus%2Fjaponicus%2Fgenomes%2FMG20.gnm3.QPGB%2Flotja.MG20.gnm3.QPGB.genome_main.fna.gz"
        expected_response = {"sequence": "ATCCTTTTTCAAACGATCAGATTTCATTATCAAAACCGTTGAGCAAACCTACAAGCTCAGATCTGATGATGAAGAAATCCATCTGCTTTCCGAGAAAAG"}
        response = self.fetch_url(url)
        self.assertEqual(response, expected_response)


    def test_fasta_references(self):
        url = "http://localhost:8080/fasta/references/https:%2F%2Fdata.legumeinfo.org%2FLotus%2Fjaponicus%2Fgenomes%2FMG20.gnm3.QPGB%2Flotja.MG20.gnm3.QPGB.genome_main.fna.gz"
        expected_response = {"references":["lotja.MG20.gnm3.Lj0","lotja.MG20.gnm3.Lj1","lotja.MG20.gnm3.Lj2","lotja.MG20.gnm3.Lj3","lotja.MG20.gnm3.Lj4","lotja.MG20.gnm3.Lj5","lotja.MG20.gnm3.Lj6","lotja.MG20.gnm3.LjC","lotja.MG20.gnm3.LjM"]}
        response = self.fetch_url(url)
        self.assertEqual(response, expected_response)


    def test_fasta_lengths(self):
        url = "http://localhost:8080/fasta/lengths/https:%2F%2Fdata.legumeinfo.org%2FLotus%2Fjaponicus%2Fgenomes%2FMG20.gnm3.QPGB%2Flotja.MG20.gnm3.QPGB.genome_main.fna.gz"
        expected_response = {"lengths":[192322135,62285374,43247325,45610869,42341900,34192293,26885540,150519,380861]}
        response = self.fetch_url(url)
        self.assertEqual(response, expected_response)
 

    def test_fasta_nreferences(self):
        url = "http://localhost:8080/fasta/nreferences/https:%2F%2Fdata.legumeinfo.org%2FLotus%2Fjaponicus%2Fgenomes%2FMG20.gnm3.QPGB%2Flotja.MG20.gnm3.QPGB.genome_main.fna.gz"
        expected_response = {"nreferences": 9}
        response = self.fetch_url(url)
        self.assertEqual(response, expected_response)
 

    def test_gff_references(self):
        url = "http://localhost:8080/gff/contigs/https:%2F%2Fdata.legumeinfo.org%2FLotus%2Fjaponicus%2Fannotations%2FMG20.gnm3.ann1.WF9B%2Flotja.MG20.gnm3.ann1.WF9B.gene_models_main.gff3.gz"
        expected_response = {"contigs":["lotja.MG20.gnm3.Lj0","lotja.MG20.gnm3.Lj1","lotja.MG20.gnm3.Lj2","lotja.MG20.gnm3.Lj3","lotja.MG20.gnm3.Lj4","lotja.MG20.gnm3.Lj5","lotja.MG20.gnm3.Lj6","lotja.MG20.gnm3.Ljchloro","lotja.MG20.gnm3.Ljmito"]}
        response = self.fetch_url(url)
        self.assertEqual(response, expected_response)
 

    def test_gff_features(self):
        url = "http://localhost:8080/gff/fetch/glycy.G1267.gnm1.Chr01:1-50000/https:%2F%2Fdata.legumeinfo.org%2FGlycine%2Fcyrtoloba%2Fannotations%2FG1267.gnm1.ann1.HRFD%2Fglycy.G1267.gnm1.ann1.HRFD.gene_models_main.gff3.gz"
        expected_response = "c4ed8163a9fbb6eb870c88fb22668ab4bb148620361fd356e7a45404a61e01ae"
        response = self.fetch_url(url)
        self.assertEqual(self.response_hash(response), expected_response)


    def test_bed_features(self):
        url = "http://localhost:8080/bed/fetch/chr1:2522705-2522714/https:%2F%2Fgist.github.com%2Fmatthewwiese%2F62c5dc478f6524b01be583be935e8da4%2Fraw%2Ff6c115046807a56c39f6adaae22237d67cc84ddc%2Fmaize_b73_chr1.bed.gz"
        expected_response = [{'contig': 'chr1', 'start': 2522705, 'end': 2522706, 'name': 'variant_104', 'score': 242375.0, 'strand': '+'}, {'contig': 'chr1', 'start': 2522707, 'end': 2522708, 'name': 'variant_105', 'score': 326.91, 'strand': '+'}, {'contig': 'chr1', 'start': 2522713, 'end': 2522714, 'name': 'variant_106', 'score': 13509.2, 'strand': '+'}]
        response = self.fetch_url(url)
        self.assertEqual(response, expected_response)
 

    def test_vcf_contigs(self):
        url = "http://localhost:8080/vcf/contigs/https:%2F%2Fdata.legumeinfo.org%2FCicer%2Farietinum%2Fdiversity%2FCDCFrontier.div.vonWettberg_Chang_2018%2Fcicar.CDCFrontier.div.vonWettberg_Chang_2018_sub10k.vcf.gz"
        expected_response = {"contigs":["cicar.CDCFrontier.gnm1.Ca1","cicar.CDCFrontier.gnm1.Ca2","cicar.CDCFrontier.gnm1.Ca3","cicar.CDCFrontier.gnm1.Ca4","cicar.CDCFrontier.gnm1.Ca5","cicar.CDCFrontier.gnm1.Ca6","cicar.CDCFrontier.gnm1.Ca7","cicar.CDCFrontier.gnm1.Ca8"]}
        response = self.fetch_url(url)
        self.assertEqual(response, expected_response)


    def test_vcf_features(self):
        url = "http://localhost:8080/vcf/fetch/cicar.CDCFrontier.gnm1.Ca2:1-10000/https:%2F%2Fdata.legumeinfo.org%2FCicer%2Farietinum%2Fdiversity%2FCDCFrontier.div.vonWettberg_Chang_2018%2Fcicar.CDCFrontier.div.vonWettberg_Chang_2018_sub10k.vcf.gz"
        expected_response = "74c30efb273b26b9a2ac7431ee8f691a27e6caa6236891f8b92c0082e935b625"
        response = self.fetch_url(url)
        self.assertEqual(self.response_hash(response), expected_response)


    def test_alignment_references(self):
        url = "http://localhost:8080/alignment/references/https:%2F%2Fdata.legumeinfo.org%2FArachis%2Fhypogaea%2Fgenome_alignments%2FTifrunner.gnm2.wga.DWM1%2Farahy.Tifrunner.gnm2.x.aradu.V14167.gnm2.DWM1.bam"
        expected_response = "f21042d23297cd95d9ea696e9841fa27cf59df906c4f51e53302ba8a9ff4bcd1"
        response = self.fetch_url(url)
        self.assertEqual(self.response_hash(response), expected_response)

    def test_alignment_unmapped(self):
        url = "http://localhost:8080/alignment/unmapped/https:%2F%2Fdata.legumeinfo.org%2FArachis%2Fhypogaea%2Fgenome_alignments%2FTifrunner.gnm2.wga.DWM1%2Farahy.Tifrunner.gnm2.x.aradu.V14167.gnm2.DWM1.bam"
        expected_response = {"unmapped": 1}
        response = self.fetch_url(url)
        self.assertEqual(response, expected_response)
 
    def test_alignment_nreferences(self):
        url = "http://localhost:8080/alignment/nreferences/https:%2F%2Fdata.legumeinfo.org%2FArachis%2Fhypogaea%2Fgenome_alignments%2FTifrunner.gnm2.wga.DWM1%2Farahy.Tifrunner.gnm2.x.aradu.V14167.gnm2.DWM1.bam"
        expected_response = {"nreferences": 442}
        response = self.fetch_url(url)
        self.assertEqual(response, expected_response)
 
    def test_alignment_nocoordinate(self):
        url = "http://localhost:8080/alignment/nocoordinate/https:%2F%2Fdata.legumeinfo.org%2FArachis%2Fhypogaea%2Fgenome_alignments%2FTifrunner.gnm2.wga.DWM1%2Farahy.Tifrunner.gnm2.x.aradu.V14167.gnm2.DWM1.bam"
        expected_response = {"nocoordinate": 1}
        response = self.fetch_url(url)
        self.assertEqual(response, expected_response)


    def test_alignment_mapped(self):
        url = "http://localhost:8080/alignment/mapped/https:%2F%2Fdata.legumeinfo.org%2FArachis%2Fhypogaea%2Fgenome_alignments%2FTifrunner.gnm2.wga.DWM1%2Farahy.Tifrunner.gnm2.x.aradu.V14167.gnm2.DWM1.bam"
        expected_response = {"mapped": 69528}
        response = self.fetch_url(url)
        self.assertEqual(response, expected_response)


    def test_alignment_lengths(self):
        url = "http://localhost:8080/alignment/lengths/https:%2F%2Fdata.legumeinfo.org%2FArachis%2Fhypogaea%2Fgenome_alignments%2FTifrunner.gnm2.wga.DWM1%2Farahy.Tifrunner.gnm2.x.aradu.V14167.gnm2.DWM1.bam"
        expected_response = "90498e8fcb52cca87f8fb1fb8b0ec19476e91986b16c1e4249872c10d2b15468"
        response = self.fetch_url(url)
        self.assertEqual(self.response_hash(response), expected_response)


    def test_alignment_index_statistics(self):
        url = "http://localhost:8080/alignment/index_statistics/https:%2F%2Fdata.legumeinfo.org%2FArachis%2Fhypogaea%2Fgenome_alignments%2FTifrunner.gnm2.wga.DWM1%2Farahy.Tifrunner.gnm2.x.aradu.V14167.gnm2.DWM1.bam"
        expected_response = "adbfa009fa1f55d0070c1e1ce2bb6fb122dbaa7dc768b352f72d6ac0440a30e3"
        response = self.fetch_url(url)
        self.assertEqual(self.response_hash(response), expected_response)


    def test_alignment_count(self):
        url = "http://localhost:8080/alignment/count/arahy.Tifrunner.gnm2.chr01:1-1000000/https:%2F%2Fdata.legumeinfo.org%2FArachis%2Fhypogaea%2Fgenome_alignments%2FTifrunner.gnm2.wga.DWM1%2Farahy.Tifrunner.gnm2.x.aradu.V14167.gnm2.DWM1.bam"
        expected_response = {"count": 32}
        response = self.fetch_url(url)
        self.assertEqual(response, expected_response)


    def test_alignment_count_coverage(self):
       url = "http://localhost:8080/alignment/count_coverage/arahy.Tifrunner.gnm2.chr01:1-100/https:%2F%2Fdata.legumeinfo.org%2FArachis%2Fhypogaea%2Fgenome_alignments%2FTifrunner.gnm2.wga.DWM1%2Farahy.Tifrunner.gnm2.x.aradu.V14167.gnm2.DWM1.bam"
       expected_response = "b9eed979e6cf1d3befb608d1f156b866180f73303eb37653c95d3e82267f2cbb"
       response = self.fetch_url(url)
       self.assertEqual(self.response_hash(response), expected_response)


    def test_alignment_fetch(self):
        url = "http://localhost:8080/alignment/fetch/arahy.Tifrunner.gnm2.chr01:1-5000/https:%2F%2Fdata.legumeinfo.org%2FArachis%2Fhypogaea%2Fgenome_alignments%2FTifrunner.gnm2.wga.DWM1%2Farahy.Tifrunner.gnm2.x.aradu.V14167.gnm2.DWM1.bam"
        expected_response = [{"name": "aradu.V14167.gnm2.chr01", "flag": "2048", "ref_name": "arahy.Tifrunner.gnm2.chr01", "ref_pos": "4254", "map_quality": "60", "cigar": "176820H774M1I1455M1I91M9I380M1D1275M1D157M105882458H", "next_ref_name": "*", "next_ref_pos": "0", "length": "0", "seq": "TAAATAAAAATATTTAAAATTTAAAATTTATTTTATATATGGAGTAATTTATTGAACGATCAATTTTTTAATAAAATTCTAATCTATAACAAATTATTAGTTTTTAATTTATTAGACTACATTAAAAGATACTCTGATCTATAACAAAAAAATAACTTGTTAACCAAATCTTTATATACAAGTCAAACACAAAAATACAAAAGGCTTATAAGAATCTCTCTCTTTCTCTAATTAACTTTTGAACTGCATGCGCTGTGCAATCATTCAACCCATATTTAGTTTCCAAATATATACTACTTGATATTTGATACTATATTTAGAGTATCCCTTAGACAGATGTGCTTCACTTAAGTTTGTCGAGCAAAGAAAATTATAAAAATATTCCTAGGATTGAACAGACACCATTCACTTTTAGTATAATTAATATAATATAATACAATTCTAAGTGGAGGGAATGTACTGGAGAATCTCCTTCTTTTCTGCAGGGTCCATGTTAATTGATGCCATATATGTTGGACATAAATATTCTTAATTTTTTTGTTATCATAACTACTCGACCATTCGTACCTGTTTATATTACTTTGCCTTTTATGTCTAATGCCTATTATTCTTAGTTACTTTTTAAAAAAGCTCAGATTATATTTAAAACATTGTACTTGTGGTTGAAAATGCTAATTAGGGATCTTGACTTTTATAAATGATTTTCTATATATGTCTTGTTGTTTTTAATGTAAGTAAATTGCAGTGAAATTAAAGTTTTGAATACTATATTTTAAAAAAAAAAAGTAAATCACGCCAGAAATAAATCACATCAAGTTCGTTGTTGCGATTTAAAACCAAGACGTGAATCTCCCTTATCCAATGCGATTTAAGTTCATCTTTAATTAAAAGAAAAAAGCTTAAATCGCACCATGGCATGTGTGTTTATAAAAATAAATAAATAACATAAATTCACCACCAGGTGGGAATGCGATTCAAGAACAAATTGACTTTAGTGAAGTTACACCATGCTTATGGGATTTAGTTTATTTCACTTAGCAGTTTCGCACCATTAAGCTTGAACACGCAGGTGAATAATACAAACTTTTCATCAGAAATACATCTCGTATTAACACTATACTACATTTTCATTCCATGAGAGAAAAGGTCAGAAAGCTACTTTAATTTGTTCTTGTTTACCACAACAATGGAAAAATTATAGAAACGACTGAGAAAACATATTTATGCTCTTTAATTTTAATTTGTATAGAAATAGTCTTTAGTCTCTCGAGTTAGGAAATATTGTGGACAACAAAAAAAATTTAGGTCATCGCATTCGAGTAAGGATATGTCCAATATTAGAGTTTTCACATGGTGAGTGATAGCAAGATGCAAATTTTCTTTCATTAGTAATCGAAATTTTTAGCAATTCACATAGTCAAGCTATTTGTCAAGGTTGATGAGAAGATATTTGTGAATTTTGGAGGAACTGAAGGGAGTTATTGTTGGAAAACTTTGAAAGGCATATTTGCCTCATTTGTAGTATATAACGATATAAATAATGTTCATTAGGAAAATGATGAGGCAGCTCTAGGTGATGGTCTATCCTTTGGGCAATTTTGAAACTTTGATTAATGTGTTACAAATATTGCAGAGGAAGTATAATTTGAGATGAGGAGGATGAGTAGGAGCCAATGAATATTCTATTCAACGATATTATGATTCTAACCCTTTCCTTATGTGGCTATTAGCTAGGTATCTCTACTATAAATACTCAAGCATATATAGCACCTAATGTAATCAATCTAATACAATCTCAACTTACTTCGTCATCTTATCCGTCTCTCTACCTCTCGCTCAAGCCTAACAGAAAGAAACTTAATAATACGATTTAATAACTAAATAGCTTGGATGTTTCTAATAAGAGATTTGATAAAATCACCCCTAAAGACAAGATATTTTACATGTATGAATTAGACCTGCAAAATGTAATTTTCCAACATTTACAACAGTGAGACAACTTCCAAAATATCAATTATAAGTATCAAAGTTTCGTTATATATAAGAGCATTATCTTACAAGTCATGTATATATGTCTCTAGGAAAAGAATTTTATGATAAATAGTTGTGAAATATTGGAGTCTAATAAAACATTTTTCTATAAGATGAGTGGATTTTACAAATAAACTTTTAGGTTGGACTAGATCTTATGAAGTATGAATAGTTATTTAACACCTTACAATTTCGATATAAAAAAAAAAAAAAACAAAGGAATAGAGGATGAGTCACACAAACTTAATAAGGGTATATGAACATAGCAGCAACAAGAGAAAAGAAAACCCAAATAATAATAATAATAATAATAATAATAATAATAATAATAATAATAATAATAAGTTTTGAAAAAACGAAGCAGATTTGGGAAATCAAATAAACACCATGCCACAAAATATAAATCATTATTTATCTTCTATAGTTGTACACTTGTACTAAGTAATTAAATAAATGAAATGTCGACCTATCGGTTATTTCTAATAAACACTATTATATTCTTTTGAAATTTGGATCTTTTAGATTTTAAATTTTTATTTTATAAAATAAAGTAAGATCTCTTACTATTAAATGTTTTTTCTTTTATATTTTTTTTGTCCAATTTCACCTATAAAATAAATGGTGATAAATCATACTTTACTCTCTAAAGCGAAATTCAAAATTTAAATGATCCAAATTCATTTTTTTTAAGTGACAAACTAATTTTTTCCGCATTATCTTAGCTTTAGTGTAGTAGGAGAATTTCTTTATATATTTATTATTTATAAATTACTTTTATTTTCTATATTTGTACTCAAGTACGCATTAAGAAAAATATAGGAAAATAATGTTTTTTTTAATAACGTAATAAGTTAAAAAAAATAAAAATAAATTTTAATTTCAAAAATTAAAATTTGAATTAATTAGGTTTAATCATAATTTTAAATCTTTCTTTTTAATTTTTGCCGCAACCACTCTCTTACAATTATGTGCCACCGCCGCCAATGTTGTATCGCAATCTCGGGTTCTCTATAACTTCTGTCCTGTTATTTATTTTTTAAAATCTAGGTTGGATGTTCATTTTATTTGGTTCTTTTCATTCTAAAGATGATATTTCTTTAGGTATACTATTGGTATTTTACTTGATTTATTTGATTCTGCATGCACATGTTTCGTAGGATATTCATTTTAATATGTATGTAGATAGTTATTTTTACTAAGATGTACATAGATGTTTATTTGGATCATACTATTTGGGTGAACGAAGCAGAGCAATACGCGATGAAAATGGCAAAGACAAGACCCAACAGCGTGAAAGCAATGATAAAAGTGTAGCATTACAGCAGCCGTGGAACAATGCCTCTAGCTCGACGACGATGCGACATTACTTCGTGGGCTTCGAAATGGACAGAGCAGCGGTGCGCGAAGGATGGGGAGAAGACGCAACTACGTAATGGTGACACGACGACAGTGGTGCGCATCCGAGTAAGGGGACTCCTCGGCGAATTAGCGAGATCAGAAGAGCAGTGACGTGCGGTGGTTGAGGATAAAACGCAACAGTAAGTCCTTAAAGATAAAAGTACATGAAAATAATAGTGAGACCGATAGTTAAGTTAAATACTGTCTTTTTATTGATATGTACATATTAACATATAATGAGAGATTTATAAAAAAATAAAAGTATGTTATTAATAGTAATTAAACGACGTTCGAGTCTCCTTTATTAAAAAAATTACCCAAAAAAATTAAGGATCAAAGAAATTTCCTGCTATTATTAATAATATTATACATTGTTTCCCTAAAATCATGTGAAAGATAAATTATTAAATATATTTTTAGTATTATACATTGAAAGGGTCTCATTCAATAAATTTGTTATCAGCAAATAGACTATTCAGCATGGATTTTCAAATATGAGAATATATTTGTAGAAATTTATTAATCACATTTAAATATCTCAATGTAACTATTTAACCTTTTATACTTGTATACATGTTACTTTGAAACAAAATTATATAAAGTGAGAATCATTGTAAAGTTGAAATTGAGAAACCGATATTTTTGAGTAATTTTAGTAGGATTCACATTTATTTATCAGTTAATGACTGGCACCAAGCCACCAACCTAGCTAGC", "qual": "*", "tags": ["RG:Z:aradu.V14167.gnm2", "NM:i:27", "ms:i:4017", "AS:i:4006", "nn:i:0", "tp:A:P", "cm:i:713", "s1:i:4093", "s2:i:10038", "de:f:0.0046", "zd:i:1", "cs:Z::34*ca:18*ag:67*ct:652+a:1204*tc:250+a:1*ta:89+aataataat:218*ct:38*tc:69*ga:50*tc:1-t:490*ca:13*ga:8*ct:302*ca:139*cg:318-t:157", "rl:i:22209493"]}]
        response = self.fetch_url(url)
        self.assertEqual(response, expected_response)

if __name__ == '__main__':
    unittest.main()