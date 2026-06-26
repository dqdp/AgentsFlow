# Finding Relevance Validation Report

Contract: `<path>`
Artifact/Diff: `<path or description>`
Gate Report: `<path>`
Review/Fusion Reports: `<paths>`
Validator: `<main/orchestrating agent or human>`

## Rule

Reviewer findings are candidate findings. They become accepted issues only after relevance validation.

## Severity Calibration Rule

Reviewer severity is a candidate label. A P0/P1 candidate validates as a blocker
only when this report records all four blocker fields:

- violated requirement: the contract, accepted decision, ADR, gate policy,
  safety rule, authority boundary or mandatory evidence requirement at risk;
- concrete evidence: reviewed artifact, diff, report, log or recorded evidence
  reference;
- blocker path: how acceptance can fail if the artifact is unchanged;
- acceptance consequence: why the workflow cannot accept before fix, explicit
  deferral or human decision.

Risk-surface or Failure Path Matrix membership alone is not enough to validate
P0/P1 severity. It may justify focused review or additional evidence, but the
validated severity must come from acceptance impact.

If an accepted P0/P1 appears after an earlier review cycle, classify why it was
late:

- `contract_gap`
- `verification_gap`
- `review_packet_gap`
- `material_fix_regression`
- `valid_late_discovery`
- `false_positive`
- `process_hygiene_nonblocking`

If the discovery class is `contract_gap`, update the task contract, Failure Path
Matrix or verification binding before treating the fix loop as complete. Do not
use another review cycle as a substitute for recording the missing requirement.

## Boundary Trace

Boundary Trace is required only when triggered. It is a small validation block
inside finding validation, not a separate gate.

Trigger conditions:

- accepted P0/P1 finding;
- mandatory evidence gap;
- new or changed review, finding, gate or acceptance invariant;
- schema, prompt rendering, reviewer output, external normalization, evaluator,
  provider, artifact storage, contract evidence or generated evidence behavior
  changes;
- reviewer-reported plausible boundary-loss path.

Boundary impact is not severity. A boundary label can explain where an issue may
be lost or misread, but validated severity still requires the grounded blocker
path above.

The main/orchestrating agent owns Boundary Trace validation. Reviewers may
suggest affected boundaries or suspected boundary impact, but those suggestions
remain candidate-unvalidated until this report validates them.

Boundary labels:

- `docs-rule`
- `reviewer-output`
- `schema`
- `prompt-rendering`
- `external-normalization`
- `artifact-storage`
- `evaluator`
- `contract-evidence`
- `generated-artifacts`
- `human-decision`

Do not add Boundary Trace for every P2/P3/NOTE finding or editorial cleanup by
default. Use it only when one of the trigger conditions above applies.

| Finding/invariant | Trigger | Affected boundaries | Existing evidence/contract | Consumer decision | Regression/evidence |
|---|---|---|---|---|---|
| F-001 | accepted P0/P1 / mandatory evidence gap / invariant change | `schema`, `evaluator` | ... | ... | ... |

## Authority Boundary

This report is the main/orchestrating agent's relevance validation record. It is
not an automatic gate verdict and does not replace human-mediated decisions.
Deterministic checks may validate report structure and evidence references, but
accepted human decisions must still be recorded in the declared human decision
artifact when the workflow requires them.

## Validation Inputs Checked

- [ ] task contract / reviewed artifact brief
- [ ] diff or artifact under review
- [ ] verification gate report
- [ ] evidence bundle / logs
- [ ] relevant ADRs / accepted decisions
- [ ] workflow profile / effective strictness / topology
- [ ] scope and non-goals
- [ ] packet relevance inputs: focus zone, selected risk surfaces, Failure Path
      Matrix, changed files, verification gate report, evidence freshness and
      known blockers

## Validation Table

| Finding ID | Source | Candidate severity | Candidate blocker? | Candidate finding | Violated requirement | Concrete evidence | Blocker path | Acceptance consequence | Relevance input refs | Relevance status | Validated severity | Blocking? | Discovery class | Reason | Rerun required? |
|---|---|---:|---:|---|---|---|---|---|---|---|---:|---:|---|---|---:|
| F-001 | reviewer-architecture | P1 | yes | ... | contract/gate/evidence | diff/report/log | failure path | acceptance consequence | focus_zone / FPM row / changed file / evidence ref / known blocker | accepted-relevant / rejected-irrelevant / needs-more-evidence / duplicate / human-decision-required | P1/P2/P3/NOTE | yes/no | contract_gap / verification_gap / review_packet_gap / material_fix_regression / valid_late_discovery / false_positive / process_hygiene_nonblocking | ... | yes/no |

## Canonical Finding Groups Checked

Use this section when fusion grouped findings before validation.

| Group ID | Group type | Finding IDs | Max candidate severity | Validation status | Reason |
|---|---|---|---:|---|---|
| G-001 | duplicate / related / conflict | F-001, F-002 | P1 | ... | ... |

## Decision Matrix

| Condition | Validation status | Blocking? | Default action |
|---|---|---:|---|
| Finding has violated requirement, concrete evidence, blocker path and acceptance consequence | accepted-relevant | yes | Fix/revise, then rerun verification gate and an acceptance-capable review cycle. |
| Finding is tagged P0/P1 but lacks any blocker field | needs-more-evidence / rejected-irrelevant / accepted-relevant with downgraded severity | no by default | Record calibration reason; produce evidence only if needed; no primary review rerun by default. |
| Finding is supported by contract/evidence but severity is P2/P3/NOTE | accepted-relevant | no | Record follow-up; no review rerun by default. |
| Finding may be valid but required evidence is missing | needs-more-evidence | yes if mandatory evidence or grounded P0/P1 blocker path | Produce evidence through the verification gate or a narrow evidence-probe objective; rerun review only if evidence materially changes. |
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
more plausible P0/P1 blocker-path candidate findings. Collision-control is
batched per review cycle, not per finding. If the only blocker signal is an
ungrounded severity label, record the no-collision reason in the final triage
instead of launching control reviewers.

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

Also record the blocker path or the reason no grounded blocker path exists.

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
no_validated_blockers_or_mandatory_evidence_gaps
```

Repeated review agents are not rerun when all P0/P1 candidate findings have been
validated and no validated blockers or mandatory evidence gaps remain.

Closure-only review can confirm previous finding closure, but it is not an
acceptance-capable review after a material change. A material fix requires a
full current review packet and a prompt that asks reviewers to look for new
P0/P1 blockers across the changed scope.

## Final Triage Decision

<pass|pass-with-notes|needs-changes|needs-verification-evidence|human-decision-required|blocked>

## Notes

- ...
