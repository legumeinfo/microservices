# AGENTS.md

Agent guide for this monorepo of Python microservices (LIS / AgBio). This file
is intentionally short; the authority is **[ARCHITECTURE.md](./ARCHITECTURE.md)**.

## Before you touch code

- **Read [ARCHITECTURE.md](./ARCHITECTURE.md)** — it is normative (MUST / SHOULD /
  AVOID). Start with its *Quick map* to jump to the relevant section.
- For an existing service, also read that service's `README.md` and
  `git log -- <service>/` for recent context.
- Check *Known deviations*
  ([§ 17](./ARCHITECTURE.md#17-known-deviations-from-this-spec)) to see if the
  file you're touching is already on a migration list.

## The rules that catch people most often

- **Three-module split**
  ([§ 3.1](./ARCHITECTURE.md#31-the-three-module-split)): `__main__.py`
  (CLI + loop), `http_server.py` / `grpc_server.py` (transport only),
  `request_handler.py` (domain logic, and it MUST NOT import `aiohttp`/`grpc`).
  Orchestration services add `clients.py` for all outbound calls
  ([§ 3.2](./ARCHITECTURE.md#32-orchestration-service-layout-the-clientspy-boundary)).
- **Generated artifacts are never committed** — protobuf stubs and built YAML are
  produced at install time
  ([§ 4](./ARCHITECTURE.md#4-packaging), [§ 9](./ARCHITECTURE.md#9-grpc-conventions)).
- **Match the house style, not your instinct**: terse comments, the
  `# Python / # dependencies / # module` import banners, the `EnvArg` pattern.

## Always, before you push

```sh
pre-commit run --all-files          # lint + format (black, flake8, isort)
```

Then verify behavior over the wire against a locally running service with
`curl` (see the service's `README.md` for examples).

## Keep the docs true

Cross-cutting changes MUST update `ARCHITECTURE.md` in the same PR. When you fix
something on the *Known deviations* list, delete that row.

**Describe only the present.** `ARCHITECTURE.md` and code comments document the
codebase as it exists **now**. Do NOT write historical narrative — no "previously
X, now Y", no "was removed / used to / older revision", and no references to past
GitHub issues or PRs (`#1234`) unless that issue/PR describes a condition that is
still true today. When behavior changes, replace the old description with the new
one; don't append the story of the change. The reason a rule exists may stay only
if stated as a present-tense fact (e.g. "setuptools ≥ 80 does not ship
`pkg_resources`"), not as a chronicle of what we changed.
