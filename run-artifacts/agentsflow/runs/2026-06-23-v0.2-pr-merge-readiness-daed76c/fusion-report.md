# Fusion Report: v0.2 PR Merge Readiness

Contract: `review-prompt-contract.yaml`
Review topology: `heterogeneous-variable`
Verification gate report: `verification-gate-report.md`
Material change: `daed76c`

## Recommended Verdict

`human-decision-required`

The review cycle has no validated P0/P1 blocker after finding relevance
validation, but this workflow cannot produce `accepted_merge_ready` without a
recorded human merge decision.

## Authority Boundary

Fusion is decision support. Reviewer reports contain candidate findings only.
The main/orchestrating agent validates relevance in `finding-validation-report.md`.
The human-owned merge decision is recorded separately in `human-decisions.yaml`.

## Mechanical Intake

| Expected report | Present? | Schema valid? | Fresh? | Assignment/provider/topic match? | Notes |
|---|---:|---:|---:|---:|---|
| `reviewer-report.verification-codex.json` | yes | yes | yes | yes | Internal Codex verification topic. |
| `reviewer-report.verification-claude.json` | yes | yes | yes | yes | Real Claude invocation, raw output not persisted. |
| `reviewer-report.architecture-codex.json` | yes | yes | yes | yes | Internal Codex architecture topic. |
| `reviewer-report.architecture-claude.json` | yes | yes | yes | yes | Real Claude invocation, raw output not persisted. |
| `reviewer-report.adversarial-codex.json` | yes | yes | yes | yes | Internal Codex adversarial topic. |
| `reviewer-report.adversarial-claude.json` | yes | yes | yes | yes | Real Claude invocation, raw output not persisted. |

`review-invocation-set.json` has `status: completed` and records the required
provider/model diversity: `internal-agent/codex` and `claude-code/opus`.

## Canonical Finding Extraction

| Canonical ID | Source finding | Source report | Provider/model | Topic/role | Candidate severity | Fusion handling |
|---|---|---|---|---|---:|---|
| CF-001 | `VERIFY-RAW-OUTPUT-001` | verification-codex | internal-agent/codex | verification | P1 | Accepted as real evidence-storage gap in the first live invocation; resolved by disabling raw persistence and rerunning external invocations. |
| CF-002 | `VERIFY-RED-CAPTURE-001` | verification-claude | claude-code/opus | verification | P1 | Conditional blocker path does not apply to this utility acceptance workflow; validate against ADR-0017 and workflow phase model. |
| CF-003 | `ADV-EXT-REVIEWER-EVIDENCE-001` | adversarial-claude | claude-code/opus | adversarial | P1 | Accepted as packet-time evidence gap; resolved by completed live invocation set and deterministic failure-path test evidence. |
| CF-004 | `VERIFY-EXT-REVIEWER-MOCK-001` | verification-claude | claude-code/opus | verification | P2 | Packet could surface targeted negative tests more clearly; not blocking after evidence check. |
| CF-005 | `VERIFY-INVOCATION-SET-001` | verification-codex | internal-agent/codex | verification | P2 | Stale after runner completion; invocation set is now completed. |
| CF-006 | `ARCH-DUP-REVIEW-CONTROL-001` | architecture-codex | internal-agent/codex | architecture | P2 | Accepted backlog: review-control policy reuse can improve after PR acceptance. |
| CF-007 | `ADV-REVIEW-SCOPE-COVERAGE-001` | adversarial-claude | claude-code/opus | adversarial | P2 | Accepted residual risk: source/generated split should be clearer in future packets. |
| CF-008 | `ARCH-SELF-APPLICATION-001`, `ADV-SELF-APPLICATION-CIRCULARITY-001` | architecture-claude, adversarial-claude | claude-code/opus | architecture/adversarial | P2 | Accepted residual risk; mitigated by explicit self-application disclaimer and human merge gate. |

## Topic-Pair Comparison

| Topic pair | Reviewer reports | Agreement | Disagreement | Fusion handling |
|---|---|---|---|---|
| verification-evidence | verification-codex, verification-claude | Both examined evidence completeness and live external review surfaces. | Codex found raw evidence persistence; Claude focused on red-capture and mock-vs-live evidence. | Preserve all candidate blockers; validate with current artifacts after evidence refresh. |
| architecture-process | architecture-codex, architecture-claude | Both treated self-application as a real process risk, not an automatic blocker. | Codex focused on duplicated review-control policy; Claude focused on self-application proof boundary. | Keep as non-blocking backlog/residual risk. |
| adversarial-authority | adversarial-codex, adversarial-claude | Both preserved human authority boundary. | Claude raised scope coverage and live-evidence concerns; Codex did not report blockers. | Validate against completed invocation set and final human gate requirements. |

## Candidate Blocking Issues

| Finding ID | Source reviewer(s) | Candidate severity | Proposed blocker path | Required validation |
|---|---|---:|---|---|
| CF-001 | verification-codex | P1 | Raw external output policy -> artifact storage -> final readiness evidence. | Check current invocation metadata and normalized reports after rerun. |
| CF-002 | verification-claude | P1 | Red-capture requirement if this acceptance workflow has an implementation phase. | Check ADR-0017 and `workflows/pr-merge-readiness/workflow.yaml`. |
| CF-003 | adversarial-claude | P1 | Live external reviewer evidence and provider-failure evidence. | Check completed live invocation set and targeted failure-path tests. |

## Candidate Non-blocking Issues

- Review-control policy reuse remains a P2 backlog item.
- Review packets should better distinguish source changes from generated run
  artifacts for large PRs.
- Self-application remains a residual limitation; the bootstrap run does not
  prove the workflow by itself.
- External reviewer failure-path tests exist but should be surfaced more
  explicitly in future evidence packets.

## Human Decision Required

- Decide whether to accept, defer or reject merge readiness for material change
  `daed76c`.

## Confidence

`medium-high`

Confidence is high for mechanical evidence and current artifact validity. It is
medium for PR-level acceptance because self-application and generated-artifact
volume require human judgment at the declared gate.

## Review Cycle Exit Check

Default exit condition:

```text
no_validated_blocking_findings
```

Fusion recommends exiting the primary review cycle after finding validation and
moving to the human merge decision phase.
