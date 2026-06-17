# Skill: impact-map-builder

## Purpose

Map affected modules/paths to required tests, scripts, contracts, and ADRs.

## Inputs

- `contract`
- `changed_paths_or_planned_paths`
- `domain_pack`


## Outputs

- `impact_map`
- `required_tests`
- `required_scripts`
- `related_adrs`


## Procedure

1. Identify affected modules.
2. Map paths to test suites.
3. Include architecture checks.
4. Include related ADRs/contracts.
5. Mark verification gaps.


## Quality bar

- Required tests are specific enough for an implementer.
- Gaps are visible.


## Anti-patterns

- Saying “run tests” without specifying which tests.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.
