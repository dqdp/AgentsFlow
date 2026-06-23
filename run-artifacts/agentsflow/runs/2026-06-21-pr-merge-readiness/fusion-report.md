# Fusion Report

Contract: `run-artifacts/agentsflow/runs/2026-06-21-pr-merge-readiness/task.contract.md`
Review Topology: `homogeneous-plus-focused` with mixed-provider generalists plus focused Codex specialist
Verification Gate Report: `run-artifacts/agentsflow/runs/2026-06-21-pr-merge-readiness/verification-gate-report.md`
Review Invocation Set: `run-artifacts/agentsflow/runs/2026-06-21-pr-merge-readiness/review-invocation-set.json`
Generated: `2026-06-22T19:35:46Z`

## Recommended Verdict

`pass-with-notes`

This is a recommendation. It becomes a final workflow decision only after main-agent or human relevance validation when the workflow requires it.

## Authority Boundary

Fusion is decision support, not an automatic gate verdict and not a human-mediated decision. Reviewer reports are candidate evidence. The orchestrating agent validates relevance and severity before findings affect the workflow decision.

## Mechanical Intake

| Expected report | Present? | Schema valid? | Fresh? | Assignment/provider/topic match? | Notes |
|---|---:|---:|---:|---:|---|
| `reviewer-report.development-codex-generalist.json` | yes | yes | yes | yes | No P0/P1; one P3 packet wording issue. |
| `reviewer-report.development-claude-generalist.json` | yes | yes | yes | yes | No P0/P1; two P2 consistency gaps and one NOTE. |
| `reviewer-report.development-codex-adversarial-authority.json` | yes | yes | yes | yes | One candidate P1 about packet freshness cues; one NOTE. |
| `reviewer-invocation.development-claude-generalist.json` | yes | yes | yes | yes | Real Claude Code invocation, `opus`, `max`, provider-reported `claude-opus-4-8`, raw path intentionally empty. |
| `review-invocation-set.json` | yes | yes | yes | yes | Completed, `external-first-async`, provider families `internal-agent/codex` and `claude-code/opus`. |

## Canonical Finding Extraction

| Canonical ID | Source finding | Source report | Provider/model | Role | Severity | Evidence refs | Risk/FPM refs |
|---|---|---|---|---|---:|---|---|
| CF-001 | `DEV-GEN-V17-P3-001` | Codex generalist | `internal-agent/codex` | generalist | P3 | v17 packet has stale `v14` instruction text | audit persistence, stale evidence |
| CF-002 | `AUTH-PKT-FRESHNESS-001` | Codex adversarial | `internal-agent/codex` | adversarial | P1 candidate | packet has stale v14/v16 wording and counts | stale evidence, authority boundary |
| CF-003 | `AUTH-RAW-META-CLARITY-001` | Codex adversarial | `internal-agent/codex` | adversarial | NOTE | raw hash with empty raw path is non-replayable metadata | secret handling, audit clarity |
| CF-004 | `DEV-GEN-V17-001` | Claude generalist | `claude-code/claude-opus-4-8` | generalist | P2 | v17 tests not enumerated in behavior bindings | verification traceability |
| CF-005 | `DEV-GEN-V17-002` | Claude generalist | `claude-code/claude-opus-4-8` | generalist | P2 | packet green evidence has stale 62/214 and v14 note | stale evidence |
| CF-006 | `DEV-GEN-V17-003` | Claude generalist | `claude-code/claude-opus-4-8` | generalist | NOTE | raw-persistence missing-hash branch label ordering | triage clarity |

## Duplicate / Related / Conflict Groups

| Group ID | Group type | Finding IDs | Max candidate severity | Shared claim or conflict | Fusion handling |
|---|---|---|---:|---|---|
| G-001 | related | CF-001, CF-002, CF-005 | P1 candidate | Active packet contains stale free-form freshness cues despite structured v17 fields and green evidence artifacts. | Preserve for relevance validation; likely downgrade if no false-readiness path is supported. |
| G-002 | related | CF-003, CF-006 | NOTE | Metadata/label clarity issues that do not change blocking behavior. | Nonblocking notes. |
| G-003 | standalone | CF-004 | P2 | Behavior binding ledger does not enumerate three v17 tests already present and passing. | Nonblocking traceability follow-up unless the workflow requires binding ledger perfection before exit. |

## Consensus

- All reviewers found no P0/P1 implementation defect in the `pr-merge-readiness` evaluator, schema, wrapper integration or raw-output policy.
- All reviewers agreed that v17 closes the two previous P1 implementation issues: raw-output bypass through `normalization.source_path` and replayable human merge approval.
- Codex and Claude both identified stale packet wording/counts as the main remaining issue.
- Claude and Codex adversarial both treated raw-output metadata clarity as nonblocking.

## Candidate Blocking Issues

| Finding ID | Source reviewer(s) | Severity | Candidate issue | Why it may block | Required validation |
|---|---|---:|---|---|---|
| CF-002 | Codex adversarial | P1 candidate | Stale v14/v16 packet cues in active v17 review packet. | If packet free-form fields were authoritative over structured hashes/evidence, this could invalidate review freshness. | Validate whether structured v17 fields, hash-bound artifacts and reviewers' explicit detection avoid false readiness; decide if downgrade is appropriate. |

## Candidate Non-blocking Issues

- CF-001/CF-005: stale duplicate packet text and counts should be cleaned in a follow-up or next packet regeneration.
- CF-004: add the three v17 regression tests to `behavior.bindings.yaml` in a follow-up material artifact update.
- CF-003: clarify that `raw_output_hash` without `raw_output_path` is non-replayable invocation metadata, not persisted raw evidence.
- CF-006: optionally reorder missing-hash validation for clearer blocker labels.

## Proposed Required Changes

No required changes before exiting this review cycle, provided finding validation downgrades CF-002 and records the remaining items as nonblocking follow-ups.

## Human Decision Required

No new human design decision is required by the review findings. Human final acceptance may still be required by the workflow's normal final decision phase.

## Confidence

`high`

## Relevance Validation Handoff

| Finding | Source reviewer(s) | Fusion classification | Relevance status | Reason | Decision impact |
|---|---|---|---|---|---|
| CF-002 | Codex adversarial | candidate blocker | requires validation | Single P1 candidate; related lower-severity findings from other reviewers. | Must be validated before exit. |
| CF-001, CF-005 | Codex generalist, Claude generalist | concern | requires validation | Same stale packet issue, lower severity. | Follow-up if CF-002 downgraded. |
| CF-004 | Claude generalist | concern | requires validation | Binding ledger traceability gap. | Follow-up unless classified mandatory evidence gap. |
| CF-003, CF-006 | Codex adversarial, Claude generalist | note | requires validation | Clarity only. | No rerun by default. |

## Review Cycle Exit Check

Default exit condition:

```text
no_validated_blocking_findings
```

Fusion recommends exiting the review cycle after relevance validation if CF-002 is downgraded or rejected as blocker-grade, because no reviewer reported a P0/P1 implementation defect and no mandatory evidence gap was found in deterministic validation.
