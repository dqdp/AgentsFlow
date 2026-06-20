# Legacy Agent-System Adoption Model

## Status

Accepted in v0.1.11.

## Purpose

When AgentsFlow is applied to an existing project, the project may already contain an agent/process layer: `AGENTS.md`, `CLAUDE.md`, Cursor/Codex/OpenCode/Roo instructions, skills, prompts, workflow documents, implementation history, review conventions, and process artifacts.

AgentsFlow must not be layered on top of those artifacts ambiguously. Existing agent/process artifacts must be discovered, classified, migrated, adapted, archived, or explicitly kept active.

## Core rule

```text
No ambiguous coexistence.
```

A project must have one active agent-instruction authority layer. Legacy artifacts may remain as historical evidence or imported knowledge, but they must not remain silently authoritative.

This model is about the legacy agent/process layer. It is separate from the
documentation legacy adoption decision recorded by
`project-documentation-disposition.yaml`.

Documentation legacy adoption covers README files, ADRs, architecture notes,
runbooks, implementation history and domain documentation. It must be selected
by the human, not by the agent. The agent may recommend one of:

```text
preserve-as-is
knowledge-extraction
rewrite-migration
archive-delete
```

When `knowledge-extraction` is selected, extraction depth is recorded separately
as `light`, `standard` or `deep`. `light` means extracting only the knowledge
needed by the current run or target workflow into a run-level artifact such as
`project-knowledge-extraction.md`, while leaving source documentation unchanged
and without changing its long-lived authority.

## Legacy adoption modes

### 1. full-archive-rebuild

Use when the existing documentation/process layer is stale, contradictory, harmful, or not trustworthy enough to adapt.

Actions:

```text
- create a backup/quarantine archive;
- mark archived artifacts as non-authoritative;
- create a new active AGENTS.md / project overlay;
- rebuild workflow bindings, gates, packs, and authority order from current evidence;
- import only explicitly reviewed knowledge.
```

This mode should be selected when old instructions are more likely to mislead agents than help them.

### 2. knowledge-extraction

Use when legacy docs contain useful knowledge but do not match the AgentsFlow model.

Actions:

```text
- backup legacy docs/process artifacts;
- extract useful knowledge into AgentsFlow artifacts:
  - project pack;
  - term map;
  - decision contracts;
  - ADR candidates;
  - workflow bindings;
  - gate recommendations;
  - domain constraints;
- mark original legacy docs as non-authoritative reference unless explicitly imported;
- create an active instruction map.
```

This is expected to be the common mode for mature but non-AgentsFlow projects.

### 3. minimal-patch-adapt

Use when the existing docs and agent instructions are mostly current, coherent, and compatible with AgentsFlow.

Actions:

```text
- backup existing artifacts;
- add/patch AgentsFlow entrypoint sections;
- add authority order;
- create `.agentsflow/` overlay and workflow bindings;
- classify existing docs/skills as active/imported/adapted;
- minimally fix conflicts.
```

### 4. shadow-pilot

Use when the project is risky or the team wants to pilot AgentsFlow before changing the active process layer.

Actions:

```text
- attach AgentsFlow and draft project overlay;
- run one or two workflow runs in a controlled scope;
- keep legacy authority mostly unchanged;
- record that shadow-pilot is temporary;
- decide later whether to patch, extract, or rebuild.
```

Shadow mode must not become permanent ambiguity.

## Required classification states

Every legacy agent/process artifact must be classified as one of:

```text
active
imported
archived
deprecated
non-authoritative
needs-human-decision
```

## Artifact types to discover

Initialization must search for and classify:

```text
AGENTS.md
CLAUDE.md
.cursor/rules
.codex/
.opencode/
.roo/
skills/
prompts/
old workflow docs
implementation history in Markdown
migration notes
runbooks
postmortems
task reports
CI/process docs
review conventions
```

## Active instruction map

The final state must include an active instruction map that makes authority explicit:

```yaml
active_instruction_sources:
  - AGENTS.md
  - .agentsflow/project.yaml
  - .agentsflow/workflows/big-feature-contract-first.binding.yaml

legacy_non_authoritative:
  - Docs/agentsflow/legacy/2026-06-17-pre-agentsflow/AGENTS.md

explicitly_imported_legacy_knowledge:
  - source: Docs/agentsflow/legacy/2026-06-17-pre-agentsflow/domain-notes.md
    imported_as: .agentsflow/packs/project-pack.md
```

## Backup policy

Never delete or overwrite existing agent/process instructions during initialization without backup and human approval.

A typical archive path:

```text
Docs/agentsflow/legacy/<date>-pre-agentsflow-adoption/
```

If legacy files remain in place, they must either remain explicitly active or receive a non-authoritative/deprecated status. If they are copied to an archive, the archive should include a `legacy-backup-manifest.yaml`.

## Authority order

A project using AgentsFlow should define an authority order, usually:

```text
1. Latest explicit human instruction
2. Accepted ADRs / accepted project decisions
3. Active workflow run artifacts: contract, plan, behavior bindings, evidence
4. Project AGENTS.md
5. .agentsflow/project.yaml and workflow bindings
6. AgentsFlow upstream workflow definitions
7. Project packs / active skills
8. Legacy docs only if explicitly referenced
```

## Integration with project initialization

Project initialization must include legacy adoption phases for existing projects:

```text
legacy agent-system discovery
legacy documentation/process classification
human-confirmed documentation legacy adoption decision
adoption mode decision
legacy backup/quarantine
knowledge extraction / patch / rebuild / shadow pilot
active instruction map creation
validation that no ambiguous authority remains
human approval
```

## Output artifacts

```text
legacy-agent-system-inventory.json
legacy-adoption-decision.yaml
agent-instruction-conflicts.md
agent-instruction-migration-plan.md
legacy-backup-manifest.yaml
active-instruction-map.yaml
```
