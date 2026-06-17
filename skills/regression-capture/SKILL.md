# Skill: regression-capture

## Purpose

Turn known failures into durable regression scenarios and verification bindings.

## Inputs

- `failure_description`
- `logs_or_trace`
- `domain_pack`


## Outputs

- `regression_scenario`
- `reproduction_notes`
- `hidden_regression_candidate`


## Procedure

1. Describe failure concretely.
2. Identify trigger and expected behavior.
3. Write a regression scenario.
4. Bind it to a test or future hidden case.
5. Record lessons learned.


## Quality bar

- Failure can be reproduced or simulated.
- Scenario prevents the same class of bug.


## Anti-patterns

- Fixing without reproducing.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.
