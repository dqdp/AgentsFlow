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
max_review_cycles: <n>
max_review_cycles_source: <project-operating-decisions|workflow-binding>
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
rejected or downgraded P0/P1 findings, and exactly two fresh-context control
reviewers inspect the batch.

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

## Rerun Decision

<exit-review-cycle|rerun-verification-gate|rerun-review-agents|revise-artifact|escalate-human>

Reason:

- ...

## Final Cycle State

<pass|pass-with-notes|needs-changes|needs-verification-evidence|human-decision-required|blocked>
