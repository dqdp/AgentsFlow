# ADR-0015: Legacy Adoption Modes

## Status

Accepted in v0.1.11.

## Context

Existing projects may already contain agent instructions, skills, prompts, workflow documents, process notes, and implementation history. If AgentsFlow is added without classifying or migrating those artifacts, agents may receive conflicting instructions and the project can end up with multiple ambiguous authority layers.

## Decision

When applying AgentsFlow to an existing project, initialization must choose an explicit legacy adoption mode:

```text
full-archive-rebuild
knowledge-extraction
minimal-patch-adapt
shadow-pilot
```

The selected mode determines how existing `AGENTS.md` files, skills, prompts, workflow docs, implementation history and process artifacts are backed up, migrated, extracted, patched, kept active, or archived.

The final project state must have one active agent-instruction authority layer and no ambiguous legacy instructions.

This ADR governs legacy agent-system/process adoption. It does not by itself
choose how the project's ordinary documentation corpus should be treated.

Project documentation legacy adoption is a separate
`project-initialization`/documentation-disposition decision. That decision must
be explicitly confirmed by the human; the agent may recommend but must not select
the documentation adoption mode without human confirmation. Supported
documentation modes are:

```text
preserve-as-is
knowledge-extraction
rewrite-migration
archive-delete
```

When `knowledge-extraction` is selected, extraction depth is recorded separately
as `light`, `standard` or `deep`. `light` is intentionally narrower than this
ADR's `knowledge-extraction` legacy agent-system mode: it extracts only the
knowledge needed by the current run or target workflow into a run-level artifact
such as `project-knowledge-extraction.md`, without rewriting or de-authorizing
the source documentation.

## Consequences

- Existing agent/process artifacts must be discovered and classified during project initialization.
- Legacy artifacts must not remain silently authoritative.
- Backup/quarantine is required before destructive replacement.
- Useful legacy knowledge may be extracted into AgentsFlow artifacts rather than discarded.
- Shadow/pilot adoption is allowed, but it must be temporary and explicitly marked.
- `active-instruction-map.yaml` becomes the project-level evidence of active vs legacy authority.
- Ordinary project documentation adoption must be recorded separately from
  legacy agent-system adoption.
- Agents must not silently choose a documentation adoption mode, even when they
  can recommend a conservative default.
