# Checkpoint: Documentation Legacy Adoption Requires Human Confirmation

## Status

Accepted on 2026-06-20.

## Decision

For existing-project `project-initialization` modes, documentation legacy
adoption is an explicit human-confirmed decision. The main/orchestrating agent
may recommend an option, but must not choose the mode without human confirmation.

The decision is recorded in `project-documentation-disposition.yaml` under
`documentation_legacy_adoption` and references the normalized
`human-decisions.yaml` record.

Supported documentation legacy adoption modes:

```text
preserve-as-is
knowledge-extraction
rewrite-migration
archive-delete
```

When `knowledge-extraction` is selected, extraction depth is recorded separately:

```text
light
standard
deep
```

`light` depth is used when the workflow extracts only the knowledge needed by
the current run or target workflow and does not rewrite the source documentation.
It does not unlock an implementation phase unless the human explicitly accepts
that risk or the workflow upgrades depth to `standard` or `deep`.

When `knowledge-extraction` is selected, the run must produce a recognizable
extraction artifact such as `project-knowledge-extraction.md`.

## Rationale

The Bro pilot showed that hiding documentation adoption inside "documentation
disposition defaults" is too implicit. AgentsFlow must make the human choice
visible because it affects which project documents become authority, evidence,
background, extraction input, migration input, or archive/delete candidates.

## Consequences

- `schemas/project-documentation-disposition.schema.json` requires
  `documentation_legacy_adoption`.
- `agent_may_select_without_human` is always `false`.
- `human_confirmation.required` is always `true`.
- Pending or agent-only choices are invalid disposition artifacts.
- `workflows/project-initialization/workflow.yaml` declares the required human
  question and the conditional extraction output.
- `light` is an extraction depth, not a documentation adoption mode.
