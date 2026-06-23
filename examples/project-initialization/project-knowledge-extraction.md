# Project Knowledge Extraction

Status: Example
Run: example-project-initialization
Mode: knowledge-extraction
Extraction depth: standard
Persistence scope: run-level
Source: project-documentation-disposition.yaml

This example records only the knowledge needed by the initialization example. It
does not rewrite the source project documentation and does not claim that the
extracted notes are long-lived project policy.

## Adoption Decision

- Mode: knowledge-extraction
- Extraction depth: standard
- Persistence scope: run-level
- Human decision: human-decisions.yaml#documentation-legacy-adoption
- Agent may select this mode without human confirmation: false

## Source Documents

| Path | Disposition | Used For | Evidence Notes |
|---|---|---|---|
| README.md | keep-authoritative | project overview | Current project overview for initialization. |
| Docs/adr/ADR-0001.md | extract-and-normalize | ADR classification question | Needs human confirmation before authority is inferred. |

## Observed Facts

- `README.md` is the current project overview for this example.
- `Docs/adr/ADR-0001.md` exists as ADR history, but accepted-decision authority
  is not inferred without human confirmation.

## Human-Confirmed Decisions

- The project uses `knowledge-extraction` with `extraction_depth: standard` and
  `persistence_scope: run-level` for documentation legacy adoption in this
  example run.

## Extracted Normalized Knowledge

- Treat the README as the current overview.
- Treat the ADR file as a source for a human authority question, not as accepted
  policy by default.

## Background Or Historical Context

- No additional historical context is imported by this example.

## Unresolved Questions

| ID | Question | Classification | Blocks Current Run? |
|---|---|---|---|
| Q-ADR-001 | Which ADR entries are accepted decisions rather than historical context? | blocking-material | yes |

## Not Migrated Or Rewritten

- Source documentation remains unchanged by initialization.
