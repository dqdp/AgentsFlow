# Finding Relevance Validation Report

Contract: `<path>`
Artifact/Diff: `<path or description>`
Gate Report: `<path>`
Review/Fusion Reports: `<paths>`
Validator: `<main/orchestrating agent or human>`

## Rule

Reviewer findings are candidate findings. They become accepted issues only after relevance validation.

## Validation Inputs Checked

- [ ] task contract / reviewed artifact brief
- [ ] diff or artifact under review
- [ ] verification gate report
- [ ] evidence bundle / logs
- [ ] relevant ADRs / accepted decisions
- [ ] workflow profile / strictness / topology
- [ ] scope and non-goals

## Validation Table

| Finding ID | Source | Severity | Candidate blocker? | Candidate finding | Relevance status | Reason | Evidence checked | Decision impact |
|---|---|---:|---:|---|---|---|---|---|
| F-001 | reviewer-architecture | P1 | yes | ... | accepted-relevant / rejected-irrelevant / needs-more-evidence / duplicate / human-decision-required | ... | contract, diff, gate report, ADR | ... |

## Decision Matrix

| Condition | Validation status | Blocking? | Default action |
|---|---|---:|---|
| Finding is supported by contract/evidence and severity is P0/P1 | accepted-relevant | yes | Fix/revise, then rerun verification gate and relevant review cycle. |
| Finding is supported by contract/evidence but severity is P2/P3/NOTE | accepted-relevant | no | Record follow-up; no review rerun by default. |
| Finding may be valid but required evidence is missing | needs-more-evidence | yes if mandatory evidence or P0/P1 | Produce evidence through the verification gate or a narrow evidence-probe objective; rerun review only if evidence materially changes. |
| Finding concerns an explicit non-goal or out-of-scope preference | rejected-irrelevant | no | Record reason; no rerun. |
| Finding is factually contradicted by contract/diff/evidence | rejected-irrelevant | no | Record contradiction; no rerun. |
| Finding duplicates an already validated issue | duplicate | inherits original | Link to original; no rerun. |
| Finding conflicts with accepted ADR or requires changing an accepted decision | human-decision-required | yes until resolved | Escalate to human / ADR workflow. |
| Reviewers disagree on a P0/P1 issue and evidence is insufficient | needs-more-evidence / human-decision-required | yes | Produce/refresh evidence, run a narrow evidence probe when appropriate, or escalate. |
| Fusion surfaces a candidate blocker from one reviewer only | needs-more-evidence / accepted-relevant / rejected-irrelevant / duplicate / human-decision-required | depends | Majority cannot erase it; validate explicitly. |

## Evidence Probe Batches

Use this section only when `needs-more-evidence` requires a targeted probe.
Probe reports are evidence only; they do not accept, reject, downgrade, or close
findings.

| Probe ID | Objective | Finding IDs | Report | Result summary | Remaining gaps |
|---|---|---|---|---|---|
| probe-001 | ... | F-001, F-002 | `evidence-probe-report.probe-001.json` | ... | ... |

## Collision-Control Batches

Use this section when the main/orchestrating agent rejects or downgrades one or
more P0/P1 candidate findings. Collision-control is batched per review cycle, not
per finding.

| Collision Batch ID | Finding IDs | Orchestrator collision reason | Control reviewer count | Control reports | Final triage |
|---|---|---|---:|---|---|
| collision-001 | F-001, F-003 | ... | 2 | `reviewer-report.control-a.md`, `reviewer-report.control-b.md` | ... |

## P0/P1 Handling

For every P0/P1 candidate finding, record one of:

- accepted as blocker;
- rejected as irrelevant with evidence-based reason;
- downgraded with reason;
- needs more evidence;
- escalated to human decision.

## Post-Fix Materiality

Classify every fix made after review before deciding whether to rerun reviewers.

| Fix ID | Finding IDs | Changed artifacts | Material? | Reason | Required next action |
|---|---|---|---:|---|---|
| fix-001 | F-001 | `schemas/...`, `docs/...` | yes/no | ... | rerun-verification / rerun-review / no-rerun |

A fix is material when it changes contracts, schemas, validators, workflow or
gate policy, project bindings, mandatory evidence, verification output, reviewed
behavior, or examples used as evidence. Editorial/report-only cleanup is
non-material by default.

## Review Cycle Decision

Default exit criterion:

```text
no_validated_blocking_findings
```

Repeated review agents are not rerun when all P0/P1 candidate findings have been
validated and no validated blockers or mandatory evidence gaps remain.

## Final Triage Decision

<pass|pass-with-notes|needs-changes|needs-verification-evidence|human-decision-required|blocked>

## Notes

- ...
