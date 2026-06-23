# Project Knowledge Extraction

Status: Draft
Run: <run-id>
Mode: knowledge-extraction
Extraction depth: <light|standard|deep>
Persistence scope: <run-level|project-level>
Source: project-documentation-disposition.yaml

This artifact records normalized knowledge extracted from existing project
documentation for the current AgentsFlow run. It does not rewrite project
documentation in place and does not make extracted items authoritative unless a
human-confirmed decision or accepted project contract says so.

## Adoption Decision

- Mode: knowledge-extraction
- Extraction depth: <light|standard|deep>
- Persistence scope: <run-level|project-level>
- Human decision: <human-decisions.yaml#...>
- Agent may select this mode without human confirmation: false

## Extraction Depth

For `extraction_depth: light`, include only the knowledge needed by the current
run or target workflow. Light extraction is not sufficient to unlock an
implementation phase unless the human explicitly accepts that risk or the
workflow upgrades extraction depth to `standard` or `deep`.

For `extraction_depth: standard`, include the normalized knowledge needed to
prepare an implementation-oriented target workflow. For `deep`, include broader
normalization intended to seed project packs, ADR candidates, workflow bindings,
or operating decisions across future workflows.

## Source Documents

| Path | Disposition | Used For | Evidence Notes |
|---|---|---|---|
| <path> | <disposition> | <target workflow/context> | <notes> |

## Observed Facts

- <fact with source path>

## Human-Confirmed Decisions

- <decision with source decision record>

## Extracted Normalized Knowledge

- <normalized item with source path and confidence>

## Background Or Historical Context

- <background item with source path>

## Unresolved Questions

| ID | Question | Classification | Blocks Current Run? |
|---|---|---|---|
| Q-001 | <question> | <blocking-material|nonblocking-follow-up|out-of-scope> | <yes|no> |

## Not Migrated Or Rewritten

- <source document or topic intentionally not rewritten>
