# DSCensor
Provide Web Facing RESTFUL API of LIS-Datastore Formatted Nodes

# Setup

Generate a set of DSCensor nodes using LIS-autocontent. This will be in "./autocontent" by default.

[Generate DSCensor Nodes](https://github.com/legumeinfo/LIS-autocontent)

The default output of the `lis-autocontent dscensor` subcommand is the `"./autocontent"` directory. This will be read by the app when docker compose is run.

## Catalog (optional)

The node endpoints above answer "tell me about this object". Passing a **catalog**
adds the complementary set -- "what exists across the whole store, and how does it
relate?" -- which needs the complete store resident rather than a per-object lookup.

Build one with LIS-autocontent (offline, ~1s for the whole store):

```
lis-autocontent populate-catalog --from_github ./datastore-metadata \
                                 --catalog_out ./autocontent/catalog.json
dscensor --nodes ./autocontent --catalog ./autocontent/catalog.json
```

`CATALOG` works as an environment variable too. The catalog is optional: without
one the node endpoints are unchanged and the catalog endpoints return `503`
explaining what to pass. A catalog that fails to load is logged and skipped rather
than taking the service down.

| Endpoint | Answers |
|---|---|
| `GET /meta` | Is a catalog loaded, when was it built, from which metadata commit |
| `GET /catalog` | The whole document, for clients that hold it in memory themselves |
| `GET /collections` | Collections filtered by `genus`, `species`, `type`, `has_doi`, `indexed` |
| `GET /types` | Which collection types exist for a scope, with counts |
| `GET /species-with?type=a&type=b` | Species holding *every* named type -- co-availability |
| `GET /assemblies` | Genomes ranked by BUSCO completeness then contig N50 |
| `GET /lineage/{id}` | A collection's ancestry and every DOI it depends on |
| `GET /indexed-files` | Files that can be range-read over HTTP, with their index type |

Every catalog response is enveloped with the build stamp under a `catalog` key, so
a client can see how stale the answer is at the point of use rather than having to
go looking. `/meta` answers even when nothing is loaded.

Two behaviours to preserve:

* **Schema is checked, not guessed.** A catalog declaring an unsupported schema is
  refused. Fields move between versions, and a silently mis-read catalog is worse
  than no catalog.
* **`index_status` is tri-state.** `"unknown"` (the collection published no
  CHECKSUM) is reported as itself, never folded into "no indexes" -- the two mean
  different things and roughly 45% of collections are `"unknown"`.

# Docker

Run local development build from cwd.

`docker compose -f compose.yaml -f compose.dev.yaml up`

Run production build from tagged image.

`docker compose -f compose.yaml -f compose.prod.yaml up`

# Development

## Install Pre-commit Hooks

Install pre-commit hooks before developing. The github will force you to subscribe on PR if you don't so please do!

`pre-commit install`

## Install DScensor

`python ./setup.py install`

`dscensor --help`
