# Skill: evidence-reporting

## Purpose

Produce an acceptance proof for a task, implementation, review, or spec workflow.

## Inputs

- `contract`
- `verification_results`
- `changed_files`
- `review_reports`


## Outputs

- `evidence_report`
- `known_limitations`
- `follow_up_items`


## Procedure

1. Summarize changes.
2. Map scenarios to evidence (including the red→green run pair for test-bound scenarios, ADR-0017).
3. List commands and results.
4. State boundary check result.
5. State limitations and follow-ups.


## Quality bar

- Evidence is auditable.
- Claims are tied to commands, files, or reviews.


## Anti-patterns

- Saying “all tests pass” without commands/results.
- Reporting only a passing (green) run for a test-bound scenario with no captured failing (red) run before implementation (ADR-0017).


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.
