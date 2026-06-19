# Gate Report

Gate authority mode:

- `deterministic_gate`
- `review_gate`
- `human_mediated_gate`

Use the mode that matches who has decision authority for this report. A
deterministic gate report must not silently include human approval or reviewer
acceptance unless those are declared inputs/evidence for the gate.

## Gate

- Name:
- Workflow:
- Profile:
- Started at:
- Finished at:
- Result: pass | pass_with_notes | fail | needs_human_decision | blocked

## Inputs

- Contract:
- Diff/artifact:
- Impact map:
- Selected profile:

## Checks Executed

| Check | Required | Result | Evidence |
|---|---:|---|---|
| contract_lint | yes |  |  |
| gherkin_lint | yes |  |  |
| boundary_check | yes |  |  |
| impact_map_check | yes |  |  |
| evidence_validate | yes |  |  |
| workflow_required_tests | yes |  |  |

## Skipped Checks

| Check | Reason | Blocking? |
|---|---|---|

## Evidence Bundle

- Command logs:
- Test results:
- Script outputs:
- Coverage/trace artifacts:
- Changed files:

## Gate Decision

Explain why the gate result is valid. Missing required checks or missing required evidence must not be silently converted into pass.

## Handoff to Review Agents

Review agents consume this report and the evidence bundle. They are read-only and must not run tests/scripts themselves.
