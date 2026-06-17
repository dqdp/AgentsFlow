# Skill: contract-authoring

## Purpose

Create a task/feature contract with intent, fixed decisions, boundaries, scenarios, verification binding, and evidence requirements.

## Inputs

- `intent`
- `specification_brief`
- `domain_pack`
- `strictness`


## Outputs

- `task_contract`
- `boundaries`
- `fixed_decisions`
- `verification_binding`


## Procedure

1. Write intent and non-goals.
2. List fixed decisions and relevant ADRs.
3. Define allowed and forbidden paths/behavior.
4. Add or link BDD scenarios.
5. Bind scenarios to tests/scripts/reviews where possible.


## Quality bar

- Contract is actionable.
- Boundaries are explicit.
- Evidence requirements are checkable.


## Anti-patterns

- Writing broad prose without enforceable constraints.
- Changing accepted decisions silently.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.
