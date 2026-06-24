# Review Cycle Report

Workflow: `<workflow>`
Review Topology: `<topology>`
Cycle: `<n>`
Contract / Artifact: `<path>`
Verification Gate Report: `<path>`
Fusion Report: `<path or none>`
Validator: `<main/orchestrating agent or human>`

## Review Cycle Policy

```yaml
default_exit_when: no_validated_blocking_findings
max_review_cycles: <n or omitted for no cycle-count cap>
max_review_cycles_source: <project-operating-decisions|workflow-binding|none>
max_review_cycles_absent_means: unlimited
blocking_default:
  severities: [P0, P1]
  missing_mandatory_evidence_blocks: true
review_observability:
  review_metrics: <path or pending until implemented>
  provider_preflight_blockers_count_as_review_cycles: false
collision_control:
  batching: per-review-cycle
  control_reviewer_count: 2
```

## Review Metrics Summary

Use structured `review-metrics.json` when the run profile requires it. Until the
metrics artifact is implemented for a project, record the same facts here.

| Metric | Value | Source |
|---|---|---|
| Review phase started | ... | invocation metadata / review metrics |
| Review phase finished | ... | invocation metadata / review metrics |
| Review phase elapsed ms | ... | review metrics |
| Substantive review cycles | ... | review-cycle ledger |
| Provider preflight blockers | ... | preflight artifact |
| Summed reviewer elapsed ms | ... | reviewer invocation metadata |
| Summed provider runtime ms | ... | provider-reported when available |
| Token/cost usage available | yes/no | provider-reported, not estimated |

## Candidate Findings Summary

| Finding ID | Source | Severity | Candidate blocker? | Summary |
|---|---|---:|---:|---|
| F-001 | reviewer-architecture | P1 | yes | ... |

## Relevance Validation Matrix

| Finding ID | Grounded? | In scope? | Factually supported? | Acceptance impact? | Validation status | Blocking? | Action |
|---|---:|---:|---:|---:|---|---:|---|
| F-001 | yes/no | yes/no | yes/no/uncertain | yes/no/uncertain | accepted-relevant / rejected-irrelevant / needs-more-evidence / duplicate / human-decision-required | yes/no | fix / verify / rerun-review / follow-up / escalate / exit |

## Validated Blocking Findings

List accepted relevant blockers, mandatory evidence gaps, or human-decision items.

- ...

## Evidence Probe Batches

Probe reports collect missing evidence only. They do not make finding or
acceptance decisions.

| Probe ID | Objective | Trigger | Finding IDs | Report | Remaining gaps |
|---|---|---|---|---|---|
| probe-001 | ... | needs-more-evidence | F-001 | `evidence-probe-report.probe-001.json` | ... |

## Collision-Control Batches

Collision-control is batched per review cycle. One batch may contain multiple
rejected or downgraded plausible blocker-path findings, and exactly two
fresh-context control reviewers inspect the batch.

| Collision Batch ID | Finding IDs | Control reviewers | Control reports | Outcome |
|---|---|---|---|---|
| collision-001 | F-001, F-003 | 2 | `reviewer-report.control-a.md`, `reviewer-report.control-b.md` | ... |

## Non-blocking Findings / Follow-ups

- ...

## Important P2/P3 Handling During Blocker Loop

Use this section only when important P2/P3 findings are fixed while a validated
P0/P1 blocker loop or mandatory-evidence-gap loop is already open.

| Finding ID | Severity | Reason to fix now | Changed artifacts | Material review input changed? | Review rerun required? | Rationale |
|---|---|---|---|---:|---:|---|
| F-010 | P2 | ... | `docs/...` | no | no | Non-material clarification in same touched area. |

P2/P3-only fixes do not trigger a review rerun unless they materially change
contract, scope, selected risk surfaces, Failure Path Matrix, schema, validator
behavior, mandatory evidence, verification result, project overlay, workflow
policy, review packet content or current evidence examples.

## Post-Fix Materiality Classification

Use this section when any accepted finding is fixed before the cycle closes.

| Fix ID | Finding IDs | Changed artifacts | Material review input changed? | Verification refreshed? | Review rerun required? | Reason |
|---|---|---|---:|---:|---:|---|
| fix-001 | F-002 | `docs/...` | no | no | no | Editorial non-source-of-truth cleanup only. |

Material changes include contract/scope changes, workflow or review-cycle policy
changes, schema/validator changes, project overlay or binding changes, mandatory
evidence changes, verification-result changes, and examples used as current
evidence. A P2 finding can produce a material fix.

## Post-Fix Rerun Scope

If a fix closes a validated P0/P1 blocker or mandatory evidence gap, the
acceptance rerun must be a full-scope blocker/evidence sweep. The reviewer packet
must include the latest review packet, complete current diff, latest green
verification evidence and previous validated findings/fixes. Reviewer
instructions must ask reviewers to verify closure and search for new or remaining
P0/P1 blockers and mandatory evidence gaps across the full slice.

Closure-only material-fix review is allowed only as supplemental evidence. It
does not count as the acceptance review gate.

## Rerun Decision

<exit-review-cycle|rerun-verification-gate|rerun-full-scope-review|revise-artifact|escalate-human>

Reason:

- ...

## Review-Loop Health Checkpoint

Complete this section when an ADR-0022 trigger fires.

Use `templates/review-loop-health-checkpoint.yaml` as the structured checkpoint
shape. The checkpoint is required only when `trigger_policy: any` fires from
main_agent_validated_findings_and_mandatory_evidence_gaps_only.

Do not copy this section as a checkpoint. Copy and fill the full canonical
template instead. The canonical template includes `required: null`,
`required_when_any_trigger_fires: true`, `trigger_policy: any`,
`counted_inputs_source`, `trigger_evidence`, `risk_surface_policy`,
`root_cause`, `diagnostic_reviewers`, `human_decision`, `closure` and
`next_review_packet`.

The checkpoint is not a review gate, cycle cap or automatic reviewer launch.

## Final Cycle State

<pass|pass-with-notes|needs-changes|needs-verification-evidence|human-decision-required|blocked>
