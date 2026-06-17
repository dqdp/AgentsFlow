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
| Finding may be valid but required evidence is missing | needs-more-evidence | yes if mandatory evidence or P0/P1 | Run verification gate/checks; rerun review only if evidence materially changes. |
| Finding concerns an explicit non-goal or out-of-scope preference | rejected-irrelevant | no | Record reason; no rerun. |
| Finding is factually contradicted by contract/diff/evidence | rejected-irrelevant | no | Record contradiction; no rerun. |
| Finding duplicates an already validated issue | duplicate | inherits original | Link to original; no rerun. |
| Finding conflicts with accepted ADR or requires changing an accepted decision | human-decision-required | yes until resolved | Escalate to human / ADR workflow. |
| Reviewers disagree on a P0/P1 issue and evidence is insufficient | needs-more-evidence / human-decision-required | yes | Produce/refresh evidence or escalate. |
| Fusion surfaces a candidate blocker from one reviewer only | validate via matrix | depends | Majority cannot erase it; validate explicitly. |

## P0/P1 Handling

For every P0/P1 candidate finding, record one of:

- accepted as blocker;
- rejected as irrelevant with evidence-based reason;
- downgraded with reason;
- needs more evidence;
- escalated to human decision.

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
