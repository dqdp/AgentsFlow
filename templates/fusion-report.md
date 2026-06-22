# Fusion Report

Contract: `<path>`
Review Topology: `<topology>`
Verification Gate Report: `<path>`

## Recommended Verdict

<pass|pass-with-notes|needs-changes|blocked|human-decision-required>

This is a recommendation. It becomes a final workflow decision only after main-agent/human relevance validation when the workflow requires it.

## Authority Boundary

Fusion is decision support, not an automatic gate verdict and not a
human-mediated decision. Deterministic automation may validate structure,
schema, freshness and evidence references; the main/orchestrating agent validates
candidate findings; human-mediated gates remain human-owned.

## Mechanical Intake

| Expected report | Present? | Schema valid? | Fresh? | Assignment/provider/topic match? | Notes |
|---|---:|---:|---:|---:|---|
| ... | yes/no | yes/no | yes/no | yes/no | ... |

## Canonical Finding Extraction

| Canonical ID | Source finding | Source report | Provider/model | Topic/role | Severity | Evidence refs | Risk/FPM refs |
|---|---|---|---|---|---:|---|---|
| CF-001 | ... | ... | ... | ... | P1 | ... | ... |

## Duplicate / Related / Conflict Groups

| Group ID | Group type | Finding IDs | Max candidate severity | Shared claim or conflict | Fusion handling |
|---|---|---|---:|---|---|
| G-001 | duplicate / related / conflict | CF-001, CF-002 | P1 | ... | ... |

## Topic-Pair Comparison

Use this section when the review topology mirrors providers or roles over the
same topic.

| Topic pair | Reviewer reports | Agreement | Disagreement | Fusion handling |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

## Consensus

Points all reviewers agree on.

## Disagreements

| Topic | Reviewer A | Reviewer B | Reviewer C | Fusion handling |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

## Candidate Blocking Issues

Fusion must surface any plausible P0/P1 candidate issue, even if only one reviewer found it. Fusion must not treat the candidate issue as proven truth; it must preserve it for relevance validation.

Reviewer severity is candidate severity. Risk-surface or Failure Path Matrix
membership alone is not enough to make a finding blocking; the handoff should
include the asserted blocker path or explicitly state that it is missing.

| Finding ID | Source reviewer(s) | Candidate severity | Candidate issue | Proposed blocker path | Risk/FPM refs | Required validation |
|---|---|---:|---|---|---|---|
| F-001 | reviewer-adversarial | P1 | ... | contract/gate/evidence -> acceptance consequence | ... | ... |

## Candidate Non-blocking Issues

- ...

## Proposed Required Changes

These are proposed changes until the main/orchestrating agent validates the underlying findings.

- ...

## Human Decision Required

- ...

## Confidence

<low|medium|high>

## Notes

- ...

## Relevance Validation Handoff

For each candidate finding that could affect acceptance, the main/orchestrating agent should record:

| Finding | Source reviewer(s) | Fusion classification | Proposed blocker path | Relevance status | Validated severity | Reason | Decision impact |
|---|---|---|---|---|---:|---|---|
| ... | ... | candidate blocker / concern | ... | accepted-relevant / rejected-irrelevant / needs-more-evidence / duplicate / human-decision-required | P1/P2/P3/NOTE | ... | ... |

## Review Cycle Exit Check

Default exit condition:

```text
no_validated_blocking_findings
```

Fusion should recommend exiting the review cycle only when there are no unresolved
candidate blockers, no validated blockers, and no mandatory evidence gaps after
main-agent relevance validation.
