# Checkpoint: AgentsFlow v0.1.11

## Focus

v0.1.11 adds the accepted Legacy Adoption Modes model for existing projects that already contain agent/process documentation, skills, prompts, workflow docs and implementation history.

## Accepted decisions recorded

- Existing projects must not have ambiguous coexistence between legacy agent/process docs and AgentsFlow.
- Every legacy artifact must be classified as active, imported, archived, deprecated, non-authoritative, or needs-human-decision.
- Supported legacy adoption modes:
  - full-archive-rebuild
  - knowledge-extraction
  - minimal-patch-adapt
  - shadow-pilot
- Default direction for messy existing projects is knowledge extraction or archive/rebuild, not silent layering.
- Backup/quarantine is required before destructive replacement.
- The final project state must have one active agent-instruction authority layer.

## New files

```text
docs/legacy-agent-system-adoption-model.md
docs/adr/ADR-0015-legacy-adoption-modes.md
templates/legacy-adoption-decision.yaml
templates/legacy-agent-system-inventory.json
templates/agent-instruction-conflicts.md
templates/agent-instruction-migration-plan.md
templates/legacy-backup-manifest.yaml
templates/active-instruction-map.yaml
schemas/legacy-adoption-decision.schema.json
schemas/legacy-agent-system-inventory.schema.json
schemas/active-instruction-map.schema.json
skills/legacy-agent-system-discovery/
skills/agent-instruction-migration/
examples/legacy-adoption/
```

## Updated workflow

`project-initialization` now includes legacy discovery, adoption-mode decision and migration/quarantine planning phases.
