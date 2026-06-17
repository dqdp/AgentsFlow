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

- The failure is captured as a recorded failing run (red), not merely described.
- Scenario prevents the same class of bug.

This reproduce-before-fix step is the bugfix instance of the test-framed
implementation discipline (ADR-0017): capture the failing run as evidence before
fixing, so the regression gate confirms the same test goes red-before / green-after.
The same red-capture step generalizes to any implementation phase, not only bugfix.


## Anti-patterns

- Fixing without reproducing.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.
