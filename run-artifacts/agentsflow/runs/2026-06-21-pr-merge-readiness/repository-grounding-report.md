# Repository Grounding Report

## Scope

Inspected existing AgentsFlow workflow, project-binding, external-review,
review-topology, phase-transition and validation artifacts before planning
`pr-merge-readiness`.

## Evidence Sources

| Source | Relevant facts | Confidence |
|---|---|---:|
| `AGENTS.md` | v0.2 primary path remains narrow; avoid scope expansion and keep workflows modular. | high |
| `docs/project-binding-model.md` | Separates workflow definitions, project bindings and run artifacts. | high |
| `profiles/review_topologies/heterogeneous-variable.yaml` | Supports three to eight explicit reviewer roles and focus zones. | high |
| `profiles/reviewer_roles/{verification,architecture,adversarial}.yaml` | Existing role contracts map to the selected review topics. | high |
| `docs/external-reviewer-provider-model.md` | External review evidence shape includes packet, raw output, normalized report and invocation metadata. | high |
| `workflows/big-feature-contract-first/workflow.yaml` | BFCF requires human `contract_acceptance` after plan gate and before red-capture. | high |
| `docs/plans/v0.2-next-slices.md` | Records accepted name/status/first-slice shape and self-application storage policy. | high |

## Existing Contracts / ADRs

- ADR-0010 gate executability rule.
- ADR-0011 behavior binding rule.
- ADR-0013 project application model.
- ADR-0016 external reviewer provider interface.
- ADR-0017 test-framed implementation phase.
- ADR-0018 phase transition control.

## Current Behavior / Architecture Notes

Observed:

- Repository validation already checks workflow definitions, schemas, examples,
  selected run artifacts and external-reviewer provider fixtures.
- `heterogeneous-variable` already exists and allows explicit focus zones.
- Existing reviewer roles cover verification, architecture and adversarial
  concerns without adding new roles.
- Existing Claude provider support distinguishes subscription-local invocation
  from mock smoke evidence.
- `run-artifacts/agentsflow/runs/**` is outside the lowercase `docs/`
  methodology-source tree and avoids the self-application `Docs`/`docs`
  collision.

Inference:

- The first `pr-merge-readiness` slice should add a structured report and
  validator checks, not a PR platform integration or release runtime.
- Provider-mirrored topic pairs can be represented as review assignment policy
  inside the workflow/binding layer without adding a new review topology.

## Gaps And Assumptions

| Gap or assumption | Blocking? | Required action |
|---|---:|---|
| Exact readiness report field names are not implemented yet. | no | Define minimal schema before red-capture tests. |
| Validator discovery for `run-artifacts/agentsflow/runs/**/run.yaml` is not currently part of `validate_repo`. | no | Add focused validation or keep explicit run validation evidence for bootstrap artifacts. |
| Live Claude may be unavailable in CI. | no | Preserve mock smoke as CI-safe baseline and require explicit live/unavailable evidence in local readiness. |
| Six-reviewer gate is heavier than the baseline. | no | Use it only for PR/merge readiness, where multiple risk themes justify provider mirroring. |

## Plan-Gate Evidence Summary

The plan is grounded enough to enter plan gate after the impact and technical
plan artifacts are created. Red-capture remains blocked until the later human
`contract_acceptance` phase.
