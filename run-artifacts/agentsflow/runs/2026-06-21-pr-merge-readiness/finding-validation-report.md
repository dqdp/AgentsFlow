# Finding Relevance Validation Report

Contract: `run-artifacts/agentsflow/runs/2026-06-21-pr-merge-readiness/task.contract.md`
Artifact/Diff: `pr-merge-readiness` utility workflow development slice
Gate Report: `run-artifacts/agentsflow/runs/2026-06-21-pr-merge-readiness/verification-gate-report.md`
Review/Fusion Reports:
- `run-artifacts/agentsflow/runs/2026-06-21-pr-merge-readiness/reviewer-report.development-codex-generalist.json`
- `run-artifacts/agentsflow/runs/2026-06-21-pr-merge-readiness/reviewer-report.development-claude-generalist.json`
- `run-artifacts/agentsflow/runs/2026-06-21-pr-merge-readiness/reviewer-report.development-codex-adversarial-authority.json`
- `run-artifacts/agentsflow/runs/2026-06-21-pr-merge-readiness/fusion-report.md`
Validator: main/orchestrating agent
Generated: `2026-06-22T19:35:46Z`

## Rule

Reviewer findings are candidate findings. They become accepted issues only after relevance validation.

## Authority Boundary

This report is the main/orchestrating agent's relevance validation record. It is not an automatic gate verdict and does not replace human-mediated decisions.

## Validation Inputs Checked

- [x] task contract / reviewed artifact brief
- [x] diff or artifact under review
- [x] verification gate report
- [x] evidence bundle / logs
- [x] relevant ADRs / accepted decisions
- [x] workflow profile / effective strictness / topology
- [x] scope and non-goals
- [x] completed mixed-provider review invocation set

## Validation Table

| Finding ID | Source | Severity | Candidate blocker? | Candidate finding | Relevance status | Reason | Evidence checked | Decision impact |
|---|---|---:|---:|---|---|---|---|---|
| `DEV-GEN-V17-P3-001` | Codex generalist | P3 | no | Review packet says v17 in structured fields but v14 in a free-form critical note. | accepted-relevant | The stale wording exists, but structured packet fields, invocation hashes and reports bind the review to v17. | active packets/prompts, review reports, invocation set | Nonblocking follow-up; no rerun. |
| `AUTH-PKT-FRESHNESS-001` | Codex adversarial | P1 candidate | yes | Active v17 packet embeds stale v14/v16 authority and green-evidence cues. | downgraded-to-P2 | The evidence is real, but blocker severity is not supported: reviewers identified the stale cues, structured packet fields carry v17, deterministic verification reports show 65/217, and no implementation false-readiness path was found. Treating this as P1 would require rerun for a duplicate packet-summary issue after a successful gate, contrary to the no-P0/P1 exit rule. | active packets/prompts, verification-gate-report.md, evidence-report.md, review-invocation-set.json, all reviewer reports | Nonblocking follow-up; no rerun. |
| `AUTH-RAW-META-CLARITY-001` | Codex adversarial | NOTE | no | Raw-output hash remains when raw path is empty. | accepted-relevant-note | This is accurate as audit wording, but not a bypass: report-facing redacted artifact hash is persisted, raw path/source path are empty, and evaluator blocks raw source paths for redacted modes. | wrapper metadata, invocation metadata, tests | Optional documentation/schema wording follow-up. |
| `DEV-GEN-V17-001` | Claude generalist | P2 | no | Three v17 regression tests are not enumerated in `behavior.bindings.yaml`. | accepted-relevant | The tests exist and pass; the binding ledger under-represents them. Updating `behavior.bindings.yaml` would change reviewed artifacts and invalidate current review evidence, so it is recorded as a follow-up rather than applied in this cycle. | behavior.bindings.yaml, tests/test_pr_merge_readiness.py, verification-gate-report.md | Nonblocking follow-up; no rerun. |
| `DEV-GEN-V17-002` | Claude generalist | P2 | no | Packet `green_evidence` summary and `critical_validation_note` are stale relative to v17. | accepted-relevant | Same issue as `AUTH-PKT-FRESHNESS-001`; valid as packet hygiene, not blocker-grade after validation. | active packets/prompts, verification-gate-report.md, evidence-report.md | Nonblocking follow-up; no rerun. |
| `DEV-GEN-V17-003` | Claude generalist | NOTE | no | Missing raw hash emits mismatch label before missing-hash label. | accepted-relevant-note | Fail-closed behavior is intact; only blocker label precision is affected. | `scripts/repo_validation/pr_merge_readiness.py` | Optional cleanup. |

## Canonical Finding Groups Checked

| Group ID | Group type | Finding IDs | Max candidate severity | Validation status | Reason |
|---|---|---|---:|---|---|
| G-001 | related | `DEV-GEN-V17-P3-001`, `AUTH-PKT-FRESHNESS-001`, `DEV-GEN-V17-002` | P1 candidate | downgraded-to-P2 | Stale packet free-form cues are real but do not create a current false-readiness path or invalidate the completed gate after reviewers explicitly caught them. |
| G-002 | related | `AUTH-RAW-META-CLARITY-001`, `DEV-GEN-V17-003` | NOTE | accepted-relevant-note | Clarity-only findings; no behavior change required. |
| G-003 | standalone | `DEV-GEN-V17-001` | P2 | accepted-relevant | Binding ledger should be improved in a follow-up material artifact update. |

## Collision-Control Batches

No collision-control batch opened.

Rationale: the only P1 candidate was downgraded to P2 based on direct evidence and cross-review agreement that no implementation P0/P1 exists. This is a main-agent relevance/severity validation of a packet hygiene issue, not rejection of a supported blocker-level implementation defect.

## P0/P1 Handling

| Candidate P0/P1 | Disposition | Reason |
|---|---|---|
| `AUTH-PKT-FRESHNESS-001` | downgraded to P2 | Stale free-form packet cues are real, but structured v17 material binding, completed invocation hashes and green evidence remain valid; no false-readiness implementation path was found. |

## Post-Fix Materiality

No post-review fixes were applied in this cycle.

| Fix ID | Finding IDs | Changed artifacts | Material? | Reason | Required next action |
|---|---|---|---:|---|---|
| none | n/a | n/a | no | No reviewed artifacts changed after review. | No rerun. |

## Follow-Up Backlog

These are nonblocking follow-ups. They should be handled in a later material slice or before the next regenerated review packet:

- Add `test_redacted_live_external_output_rejects_invocation_normalization_raw_source` and `test_redacted_live_external_output_rejects_report_normalization_raw_source` to `PRM-BHV-005` in `behavior.bindings.yaml`.
- Add `test_accepted_human_decision_must_bind_material_change_and_report_hash` to `PRM-BHV-010` in `behavior.bindings.yaml`.
- Remove duplicated stale `green_evidence` count summaries from review packets or regenerate them from `verification-gate-report.md`.
- Replace version-specific packet wording such as `v14 packet` with version-neutral wording or current material-change id.
- Clarify in reviewer invocation docs/schema that `raw_output_hash` with an empty `raw_output_path` is non-replayable invocation metadata, while the report-facing redacted artifact hash is the persisted evidence.
- Optionally reorder raw hash validation to emit a more precise missing-hash blocker before mismatch.

## Review Cycle Decision

Default exit criterion:

```text
no_validated_blocking_findings
```

Decision: `exit-review-cycle`

Reason: after main-agent validation, there are no P0/P1 findings, no validated blockers and no mandatory evidence gaps. Nonblocking P2/P3/NOTE findings are recorded for follow-up and do not trigger a repeated review gate.

## Final Triage Decision

`pass-with-notes`

## Notes

- The completed review gate used three reviewers: Codex generalist, Claude generalist and Codex adversarial-authority.
- The Claude reviewer was invoked first by `run_review_set.py` with `external-first-async` scheduling, `opus`, `max`, 900-second timeout and progress heartbeats.
- The live Claude report is normalized JSON and includes provider metadata for `claude-opus-4-8`.
