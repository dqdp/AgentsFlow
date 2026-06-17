# Skill: bdd-scenario-design

## Purpose

Design concrete BDD/Gherkin scenarios for product, agent, process, policy, and regression behavior.

## Inputs

- `contract`
- `domain_pack`
- `strictness`
- `known_failures`


## Outputs

- `behavioral_scenarios`
- `forbidden_behavior`
- `ambiguity_notes`


## Procedure

1. Identify behavior with real risk.
2. Write Given/When/Then scenarios.
3. Prefer observable properties over exact long outputs.
4. Include forbidden behavior.
5. Map scenarios to verification where possible.


## Quality bar

- Scenarios are concrete and checkable.
- Vague terms are replaced with evidence fields.


## Anti-patterns

- Using Gherkin for every unit test.
- Writing “Then it should work correctly”.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.
