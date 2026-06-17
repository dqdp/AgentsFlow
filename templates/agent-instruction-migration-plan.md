# Agent Instruction Migration Plan

## Selected adoption mode

`knowledge-extraction`

## Migration goals

- Establish one active instruction authority layer.
- Preserve useful legacy knowledge.
- Remove ambiguous legacy authority.

## Actions

| Step | Action | Source | Target | Status |
|---|---|---|---|---|
| 1 | Backup legacy artifacts | AGENTS.md, old-skills/ | Docs/agentsflow/legacy/<date>/ | pending |
| 2 | Extract domain rules | old docs | .agentsflow/packs/project-pack.md | pending |
| 3 | Patch root AGENTS.md | AGENTS.md | AGENTS.md | pending |
| 4 | Create active instruction map | classified artifacts | .agentsflow/active-instruction-map.yaml | pending |

## Human decisions required

- Confirm adoption mode.
- Confirm which legacy artifacts remain active.
