# Data Format
## PAF
https://github.com/lh3/miniasm/blob/master/PAF.md

| Column | Name | Type | Description |
|--------|------|------|-------------|
| 1 | Query name | string | Query sequence (chromosome) name |
| 2 | Query length | int | Total length of query sequence |
| 3 | Query start | int | Query start position (0-based) |
| 4 | Query end | int | Query end position (0-based) |
| 5 | Strand | char | Relative strand: "+" or "-" |
| 6 | Target name | string | Target sequence (chromosome) name |
| 7 | Target length | int | Total length of target sequence |
| 8 | Target start | int | Target start position (0-based) |
| 9 | Target end | int | Target end position (0-based) |
| 10 | Matches | int | Number of residue matches |
| 11 | Block length | int | Alignment block length |
| 12 | Mapping quality | int | Mapping quality (0-255, 255=missing) |

### Example

```
aradu.V14167.gnm1.chr01	110876686	1234567	1240000	+	arahy.Tifrunner.gnm1.Arahy.01	119055080	2345678	2351111	1	1	255
aradu.V14167.gnm1.chr01	110876686	5678901	5684000	-	arahy.Tifrunner.gnm1.Arahy.02	118608362	3456789	3462789	1	1	255
```

## JSON
```json

{
  "type": "object",
  "required": ["alignments"],
  "properties": {
    "alignments": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "query",
          "target",
          "strand",
          "numResidueMatches",
          "alignmentBlockLength",
          "mappingQuality"
        ],
        "properties": {
          "query": {
            "type": "object",
            "required": ["name", "length", "start", "end"],
            "properties": {
              "name": {
                "type": "string",
                "description": "Query name"
              },
              "length": {
                "type": "integer",
                "minimum": 1,
                "description": "Total length of query in base pairs"
              },
              "start": {
                "type": "integer",
                "minimum": 0,
                "description": "Alignment start position on query (0-based)"
              },
              "end": {
                "type": "integer",
                "minimum": 0,
                "description": "Alignment end position on query (0-based)"
              }
            }
          },
          "target": {
            "type": "object",
            "required": ["name", "length", "start", "end"],
            "properties": {
              "name": {
                "type": "string",
                "description": "Target name"
              },
              "length": {
                "type": "integer",
                "minimum": 1,
                "description": "Total length of target in base pairs"
              },
              "start": {
                "type": "integer",
                "minimum": 0,
                "description": "Alignment start position on target (0-based)"
              },
              "end": {
                "type": "integer",
                "minimum": 0,
                "description": "Alignment end position on target (0-based)"
              }
            }
          },
          "strand": {
            "type": "string",
            "enum": ["+", "-"],
            "description": "Relative strand orientation"
          },
          "numResidueMatches": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of matching residues in alignment"
          },
          "alignmentBlockLength": {
            "type": "integer",
            "minimum": 0,
            "description": "Length of alignment block"
          },
          "mappingQuality": {
            "type": "integer",
            "minimum": 0,
            "maximum": 255,
            "description": "Mapping quality score (255 indicates missing/unavailable)"
          }
        }
      }
    }
  }
}
```

### Example

```json
{
  "alignments": [
    {
      "query": {
        "name": "aradu.V14167.gnm1.chr01",
        "length": 110876686,
        "start": 1234567,
        "end": 1240000
      },
      "target": {
        "name": "arahy.Tifrunner.gnm1.Arahy.01",
        "length": 119055080,
        "start": 2345678,
        "end": 2351111
      },
      "strand": "+",
      "numResidueMatches": 1,
      "alignmentBlockLength": 1,
      "mappingQuality": 255
    },
    {
      "query": {
        "name": "aradu.V14167.gnm1.chr01",
        "length": 110876686,
        "start": 5678901,
        "end": 5684000
      },
      "target": {
        "name": "arahy.Tifrunner.gnm1.Arahy.02",
        "length": 118608362,
        "start": 3456789,
        "end": 3462789
      },
      "strand": "-",
      "numResidueMatches": 1,
      "alignmentBlockLength": 1,
      "mappingQuality": 255
    }
  ]
}
```
