# Run Artifact Curation

## Purpose

AgentsFlow run history is evidence for a concrete local run. It should not enter
the upstream methodology repository by default.

## Current Tracked State

As of the 2026-07-01 cleanup pass, tracked run artifacts in this repository are
limited to the curated end-to-end example under:

```text
examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/
```

The root local run directories are ignored:

```text
/.agentsflow/
/run-artifacts/
```

Local files under those paths may exist on a developer machine, but they are not
source artifacts and should not be committed.

## Promotion Rule

Promote run evidence into git only when it becomes a curated example or test
fixture. Promoted artifacts should live under `examples/`, be intentionally
small, and be validated by the repository checks.

Do not promote raw local run history, provider transcripts, temporary review
bundles, stale-review evidence, or generated work-in-progress run directories.

## Enforcement

`scripts/validate_repo.py --root .` rejects tracked local run artifacts under
root `.agentsflow/` and `run-artifacts/`. Use
`scripts/validate_repo.py --root . --tracked-only` when checking a commit or PR
for tracked-only repository state.
