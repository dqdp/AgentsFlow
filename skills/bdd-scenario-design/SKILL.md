# Skill: bdd-scenario-design

## Purpose

Design concrete BDD/Gherkin scenarios for product, agent, process, policy,
failure-path and regression behavior.

## Inputs

- `contract`
- `domain_pack`
- `strictness`
- `known_failures`
- `risk_surface_profile`
- `failure_path_matrix`


## Outputs

- `behavioral_scenarios`
- `forbidden_behavior`
- `path_class_scenarios`
- `failure_path_coverage_notes`
- `ambiguity_notes`


## Procedure

1. Identify behavior with real risk.
2. Read selected risk surfaces and required path classes from the contract.
3. For each required Failure Path Matrix row, write or identify a scenario that
   exercises the row's trigger and observable outcome.
4. Cover happy paths and hard paths: denied, malformed, bypass, timeout,
   rejected, downstream-failure and persistence/audit paths when selected.
5. Write Given/When/Then scenarios.
6. Prefer observable properties over exact long outputs.
7. Include forbidden behavior and `must_not_happen` expectations from FPM rows.
8. Map scenarios to verification where possible and include `risk_surfaces`,
   `path_class` and `failure_path_matrix_refs` metadata for behavior bindings.


## Quality bar

- Scenarios are concrete and checkable.
- Vague terms are replaced with evidence fields.
- Required path classes are covered by scenarios or explicitly marked as
  deferred/residual risk.


## Anti-patterns

- Using Gherkin for every unit test.
- Writing “Then it should work correctly”.
- Writing only happy-path scenarios when selected surfaces require failure paths.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.
