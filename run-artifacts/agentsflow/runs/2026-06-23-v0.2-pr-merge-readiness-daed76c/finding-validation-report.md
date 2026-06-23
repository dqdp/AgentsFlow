# Finding Relevance Validation Report: v0.2 PR Merge Readiness

Contract: `review-prompt-contract.yaml`
Artifact/diff: `main..daed76c`
Gate report: `verification-gate-report.md`
Review/fusion reports: `reviewer-report.*.json`, `fusion-report.md`
Validator: main/orchestrating agent

## Rule

Reviewer findings are candidate findings. They become accepted issues only after
relevance validation against the workflow contract, current artifacts, evidence,
accepted decisions and authority boundaries.

## Validation Inputs Checked

- `workflows/pr-merge-readiness/workflow.yaml`
- `docs/pr-merge-readiness.md`
- `docs/external-reviewer-provider-model.md`
- `docs/adr/ADR-0017-test-framed-implementation-phase.md`
- `evidence-report.md`
- `verification-gate-report.md`
- `evidence/command-evidence.json`
- `review-invocation-set.json`
- `reviewer-invocation.*-claude.json`
- `reviewer-report.*.json`
- `tests/test_scripts_smoke.py`

## Boundary Trace

| Finding/invariant | Trigger | Affected boundaries | Existing evidence/contract | Consumer decision | Regression/evidence |
|---|---|---|---|---|---|
| `VERIFY-RAW-OUTPUT-001` | accepted P1 evidence-storage gap | `artifact-storage`, `external-normalization`, `contract-evidence` | External provider model permits raw capture only for non-sensitive evidence; final readiness cannot point at uncommitted raw dumps. | Disable raw persistence for this run and use committed summary artifacts. | External Claude invocations rerun with `preserve_raw_output: false`; reports have empty `normalization.source_path`; validator passed. |
| `ADV-EXT-REVIEWER-EVIDENCE-001` | mandatory live external evidence concern | `contract-evidence`, `external-normalization`, `evaluator` | `review-invocation-set.json` now records three real Claude invocations; wrapper failure path is covered by targeted pytest. | Treat packet-time gap as resolved by current evidence; no blocker remains. | `validate_repo` passed after live invocation set refresh. |
| `VERIFY-RED-CAPTURE-001` | candidate P1 with conditional blocker path | `docs-rule`, `contract-evidence` | ADR-0017 requires red-capture framing for implementation phases; `pr-merge-readiness` is a utility acceptance workflow with no implementation phase. | Reject P1 blocker path as not applicable to this workflow phase. | No source change required; no rerun required. |

## Validation Table

| Finding ID | Source | Candidate severity | Candidate blocker? | Relevance status | Validated severity | Blocking? | Reason | Evidence checked | Decision impact | Rerun required? |
|---|---|---:|---:|---|---:|---:|---|---|---|---:|
| `VERIFY-RAW-OUTPUT-001` | verification-codex | P1 | yes | accepted-relevant, resolved by evidence fix | NOTE | no | The finding was correct for the first live invocation state. It was fixed by disabling raw persistence and rerunning external invocations; current reports no longer reference raw paths. | `.agentsflow/external-reviewers/claude-code.yaml`, `reviewer-invocation.*-claude.json`, `reviewer-report.*-claude.json`, `validate_repo` | No remaining acceptance blocker. | completed |
| `VERIFY-RED-CAPTURE-001` | verification-claude | P1 | conditional | rejected-irrelevant for this workflow phase | NOTE | no | The blocker path depends on red-capture being required for this run. `pr-merge-readiness` is an acceptance/reporting utility, not an implementation phase; ADR-0017 does not require a new red-capture for this acceptance run. | `workflows/pr-merge-readiness/workflow.yaml`, `docs/adr/ADR-0017-test-framed-implementation-phase.md`, `AGENTS.md` | No blocker; future packets can state this boundary more explicitly. | no |
| `ADV-EXT-REVIEWER-EVIDENCE-001` | adversarial-claude | P1 | yes | accepted-relevant, resolved by evidence refresh | P2 | no | The packet accurately said mock smoke is not live evidence. The current run now has real Claude invocations for all three external reviewers, and provider failure evidence is covered by targeted tests. The residual issue is evidence-packet clarity, not merge blocking. | `review-invocation-set.json`, `reviewer-invocation.*-claude.json`, `tests/test_scripts_smoke.py`, `validate_repo` | No blocker; improve future packet summaries. | completed |
| `VERIFY-EXT-REVIEWER-MOCK-001` | verification-claude | P2 | no | accepted-relevant | P2 | no | The mock smoke alone is insufficient, but it is not the final evidence set. Failure-path tests and real Claude invocation evidence exist. | `tests/test_scripts_smoke.py`, `review-invocation-set.json` | Backlog/evidence presentation improvement. | no |
| `VERIFY-INVOCATION-SET-001` | verification-codex | P2 | no | rejected-stale | NOTE | no | The finding was true before runner completion. Current `review-invocation-set.json` is completed and references all reports. | `review-invocation-set.json`, `validate_repo` | None. | no |
| `ARCH-DUP-REVIEW-CONTROL-001` | architecture-codex | P2 | no | accepted-relevant | P2 | no | Review-control policy is somewhat duplicated across workflow definitions. This does not invalidate the PR acceptance slice, but it is a good follow-up for modularity hardening. | `workflows/*/workflow.yaml`, `docs/review-control-model.md` | Backlog. | no |
| `ADV-REVIEW-SCOPE-COVERAGE-001` | adversarial-claude | P2 | no | accepted-relevant | P2 | no | The PR includes large generated evidence volume. Current packet reviewed the intended acceptance surfaces, but future packets should quantify source vs generated changes more clearly. | `readiness-intake.md`, `review-prompt-contract.yaml`, git diff stats | Residual risk/backlog. | no |
| `ARCH-SELF-APPLICATION-001` | architecture-claude | P2 | no | accepted-relevant | P2 | no | Self-application is a real limitation. It is mitigated by the bootstrap disclaimer, deterministic validation, provider-mirrored review and human merge gate; it does not prove the workflow by itself. | `run.yaml`, `docs/pr-merge-readiness.md`, `fusion-report.md` | Residual limitation. | no |
| `ADV-SELF-APPLICATION-CIRCULARITY-001` | adversarial-claude | P2 | no | duplicate of self-application residual risk | P2 | no | Same underlying risk as `ARCH-SELF-APPLICATION-001`. | same as above | Residual limitation. | no |

## Canonical Finding Groups Checked

| Group ID | Group type | Finding IDs | Max candidate severity | Validation status | Reason |
|---|---|---|---:|---|---|
| `G-RAW-EVIDENCE` | resolved evidence gap | `VERIFY-RAW-OUTPUT-001` | P1 | resolved | Current external invocation evidence no longer persists raw paths; summary artifacts provide committed evidence surface. |
| `G-LIVE-CLAUDE-EVIDENCE` | resolved evidence gap | `ADV-EXT-REVIEWER-EVIDENCE-001`, `VERIFY-EXT-REVIEWER-MOCK-001` | P1 | resolved/non-blocking | Mock smoke remains limited, but live Claude invocations and targeted failure-path tests are present. |
| `G-RED-CAPTURE` | contract applicability check | `VERIFY-RED-CAPTURE-001` | P1 | no blocker path | Red-capture is not mandatory for this utility acceptance workflow. |
| `G-SELF-APPLICATION` | residual risk | `ARCH-SELF-APPLICATION-001`, `ADV-SELF-APPLICATION-CIRCULARITY-001` | P2 | accepted non-blocking | Human merge decision remains required; bootstrap run does not prove itself. |

## Post-Fix Materiality

| Fix ID | Finding IDs | Changed artifacts | Material? | Reason | Required next action |
|---|---|---|---:|---|---|
| `fix-raw-output-retention` | `VERIFY-RAW-OUTPUT-001` | `.agentsflow/external-reviewers/claude-code.yaml`, `reviewer-report.*-claude.json`, `reviewer-invocation.*-claude.json`, `review-invocation-set.json`, `evidence/raw/*-claude.summary.md` | yes | External evidence storage behavior changed for the run. | Rerun affected external reviewer invocations and validator; completed. |

## Collision-Control Batches

No collision-control batch was launched.

Rationale:

- `VERIFY-RAW-OUTPUT-001` and `ADV-EXT-REVIEWER-EVIDENCE-001` were not silently
  rejected; they were accepted as evidence gaps and resolved by refreshing the
  relevant evidence.
- `VERIFY-RED-CAPTURE-001` is conditional on a red-capture requirement that does
  not apply to this utility acceptance workflow, so no grounded blocker path
  remains after contract validation.

## Review Cycle Decision

`exit-review-cycle`

Default exit criterion:

```text
no_validated_blocking_findings
```

There are no validated P0/P1 blockers and no mandatory evidence gaps after the
raw-output evidence fix, live Claude rerun and repository validation.

## Final Triage Decision

`human-decision-required`

The next workflow phase is `human_merge_decision`. A final
`pr-merge-readiness-report.json` must not be authoritative until the human
decision is recorded.
