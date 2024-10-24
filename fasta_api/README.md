# Linkouts Microservice

This directory contains linkout microservices, ie services primarily intended for generating links to other user-facing endpoints given some information like a gene id. For example, an application displaying genes from many species may wish to allow the user to obtain possible destinations that are species specific, and the gene linkout service would mediate this so that all applications within a site can rely on the same logic and provide consistent user experience. 

## Setup

The easiest way to install the linkouts microservice is with Docker. 

## Running

The easiest way to run the linkouts microservice is with docker compose. You will need to set the DATA environment variable used in the compose file to the root of a directory hierarchy containing LINKOUTS.\*.yml files with linkout specifications (e.g. by cloning the legumeinfo/datastore-metadata repo if you are working for the legume).

The syntax of a linkout file allows an identifier prefix to be associated with one or more URLs; when the service is queried with a set of identifiers, each will have its prefix checked for possible links, and then the identifier (or component parts parsed from it) will be substituted into placeholders in the link template. 

```
prefix: vigun.CB5-2.gnm1.ann1

gene_linkouts:
  -
    method: GET
    href: https://vigna.legumeinfo.org/tools/gcv/gene;vigna={GENE_ID}
    text: "View {GENE_ID} in Genome Context Viewer"
  -
    method: GET
    href: https://mines.legumeinfo.org/cowpeamine/gene:{GENE_ID}
    text: "View {GENE_ID} in VignaMine"

```
```
prefix: vigun.CB5-2.gnm1

genomic_region_linkouts:
  -
    method: GET
    href: https://vigna.legumeinfo.org/tools/gcv/search?q={GENOMIC_REGION}&sources=vigna
    text: "View {GENOMIC_REGION} in Genome Context Viewer"
  -
    method: GET
    href: https://vigna.legumeinfo.org/tools/jbrowse2?config=vigna.json&session=spec-%7B%22views%22%3A%5B%7B%22assembly%22%3A%22vigun.CB5-2.gnm1%22%2C%22loc%22%3A%22{GENOMIC_REGION_CHR_ID}%3A{GENOMIC_REGION_START}-{GENOMIC_REGION_END}%22%2C%22type%22%3A%20%22LGV%22%2C%22tracks%22%3A%5B%22gene_models_main%22%5D%7D%5D%7D
    text: "View {GENOMIC_REGION} in JBrowse2"
```

## Use

The microservice can be queried via HTTP GET.

The default request URLs are :
- `localhost:8080/gene_linkouts?genes=<comma-delimited geneid list>`
- `localhost:8080/genomic_region_linkouts?genomic_regions=<comma-delimited list of seqid:start-end>`

The **production** URLs are:
- `https://services.lis.ncgr.org/gene_linkouts?genes=<comma-delimited geneid list>`
- `https://services.lis.ncgr.org/genomic_region_linkouts?genomic_regions=<comma-delimited list of seqid:start-end>`
