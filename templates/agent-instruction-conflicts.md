# Agent Instruction Conflicts

## Purpose

Record conflicts between existing agent/process artifacts and AgentsFlow rules.

## Conflicts

| ID | Source A | Source B | Conflict | Severity | Proposed handling |
|---|---|---|---|---|---|
| LEGACY-CONFLICT-001 | AGENTS.md | AgentsFlow review-agent rules | Example: old docs allow reviewers to run tests directly | P1 | Migrate old rule into verification gate or mark legacy non-authoritative |

## Open questions

- Which legacy artifacts should remain active?
- Which useful domain/process rules should be imported into project packs?
