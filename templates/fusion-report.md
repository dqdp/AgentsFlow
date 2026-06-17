# Fusion Report

Contract: `<path>`
Review Topology: `<topology>`
Verification Gate Report: `<path>`

## Recommended Verdict

<pass|pass-with-notes|needs-changes|blocked|human-decision-required>

This is a recommendation. It becomes a final workflow decision only after main-agent/human relevance validation when the workflow requires it.

## Consensus

Points all reviewers agree on.

## Disagreements

| Topic | Reviewer A | Reviewer B | Reviewer C | Fusion handling |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

## Candidate Blocking Issues

Fusion must surface any plausible P0/P1 candidate issue, even if only one reviewer found it. Fusion must not treat the candidate issue as proven truth; it must preserve it for relevance validation.

| Finding ID | Source reviewer(s) | Severity | Candidate issue | Why it may block | Required validation |
|---|---|---:|---|---|---|
| F-001 | reviewer-adversarial | P1 | ... | ... | ... |

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

| Finding | Source reviewer(s) | Fusion classification | Relevance status | Reason | Decision impact |
|---|---|---|---|---|---|
| ... | ... | candidate blocker / concern | accepted-relevant / rejected-irrelevant / needs-more-evidence / duplicate / human-decision-required | ... | ... |

## Review Cycle Exit Check

Default exit condition:

```text
no_validated_blocking_findings
```

Fusion should recommend exiting the review cycle only when there are no unresolved
candidate blockers, no validated blockers, and no mandatory evidence gaps after
main-agent relevance validation.
