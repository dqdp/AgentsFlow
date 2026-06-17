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
blocking_default:
  severities: [P0, P1]
  missing_mandatory_evidence_blocks: true
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

## Non-blocking Findings / Follow-ups

- ...

## Rerun Decision

<exit-review-cycle|rerun-verification-gate|rerun-review-agents|revise-artifact|escalate-human>

Reason:

- ...

## Final Cycle State

<pass|pass-with-notes|needs-changes|needs-verification-evidence|human-decision-required|blocked>
