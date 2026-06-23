# Skill: evidence-reporting

## Purpose

Produce an acceptance proof for a task, implementation, review, or spec workflow,
including scenario coverage, Failure Path Matrix coverage, structured command
evidence and freshness after material changes.

## Inputs

- `contract`
- `verification_results`
- `changed_files`
- `review_reports`
- `risk_surface_profile`
- `failure_path_matrix`
- `behavior_bindings`
- `material_change_log`


## Outputs

- `evidence_report`
- `failure_path_matrix_coverage`
- `evidence_freshness_summary`
- `known_limitations`
- `follow_up_items`


## Procedure

1. Summarize changes.
2. Map scenarios to evidence (including the red→green run pair for test-bound scenarios, ADR-0017).
3. Map each required FPM row to evidence status: pass, fail, skip or
   human-approved deferral.
4. Record structured command evidence for each command: command, cwd, start/end
   time when available, exit code, result, output summary, artifact paths and raw
   log path when stored.
5. Record the latest material change id and confirm green verification evidence
   was produced after that change.
6. Mark or exclude stale evidence. Do not use pre-material-change evidence as
   acceptance proof for the changed scope.
7. State whether review packets were generated after the latest green evidence
   when review is applicable.
8. State boundary check result.
9. State limitations and follow-ups.


## Quality bar

- Evidence is auditable.
- Claims are tied to commands, files, or reviews.
- Freshness is explicit: latest material change, latest green gate and stale
  evidence handling are visible.
- FPM coverage is visible when risk surfaces were selected.


## Anti-patterns

- Saying “all tests pass” without commands/results.
- Reporting only a passing (green) run for a test-bound scenario with no captured failing (red) run before implementation (ADR-0017).
- Using stale evidence produced before a material change without marking it.
- Omitting denied/timeout/rejected/audit failure paths from evidence when they
  were selected in the contract.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.
