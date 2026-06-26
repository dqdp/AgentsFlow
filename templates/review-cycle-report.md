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
default_exit_when: no_validated_blockers_or_mandatory_evidence_gaps
max_review_cycles: <n or omitted for no cycle-count cap>
max_review_cycles_source: <project-operating-decisions|workflow-binding|none>
max_review_cycles_absent_means: unlimited
blocking_default:
  severities: [P0, P1]
  missing_mandatory_evidence_blocks: true
collision_control:
  batching: per-review-cycle
  control_reviewer_count: 2
```

## Candidate Findings Summary

| Finding ID | Source | Severity | Candidate blocker? | Summary |
|---|---|---:|---:|---|
| F-001 | reviewer-architecture | P1 | yes | ... |

## Relevance Validation Matrix

| Finding ID | Violated requirement? | Concrete evidence? | Blocker path? | Acceptance consequence? | Validation status | Blocking? | Discovery class | Action |
|---|---:|---:|---:|---:|---|---:|---|---|
| F-001 | yes/no | yes/no | yes/no | yes/no | accepted-relevant / rejected-irrelevant / needs-more-evidence / duplicate / human-decision-required | yes/no | contract_gap / verification_gap / review_packet_gap / material_fix_regression / valid_late_discovery / false_positive / process_hygiene_nonblocking | fix / verify / rerun-review / follow-up / escalate / exit |

P0/P1 validates only when all four blocker columns are `yes`. Otherwise record
the calibration reason and classify as needs-more-evidence, downgraded severity,
contract gap or rejected finding.

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

## Post-Fix Materiality Classification

Use this section when any accepted finding is fixed before the cycle closes.

| Fix ID | Finding IDs | Changed artifacts | Material review input changed? | Verification refreshed? | Review rerun required? | Reason |
|---|---|---|---:|---:|---:|---|
| fix-001 | F-002 | `docs/...` | no | no | no | Editorial non-source-of-truth cleanup only. |

Material changes include contract/scope changes, workflow or review-cycle policy
changes, schema/validator changes, project overlay or binding changes, mandatory
evidence changes, verification-result changes, and examples used as current
evidence. A P2 finding can produce a material fix.

Closure-only review may confirm that old findings are fixed, but it cannot close
acceptance after a material change. If review rerun is required, use the full
current review packet and ask reviewers to check both prior finding closure and
new P0/P1 blockers across the changed scope.

## Rerun Decision

<exit-review-cycle|rerun-verification-gate|rerun-review-agents|revise-artifact|escalate-human>

Reason:

- ...

## Final Cycle State

<pass|pass-with-notes|needs-changes|needs-verification-evidence|human-decision-required|blocked>
