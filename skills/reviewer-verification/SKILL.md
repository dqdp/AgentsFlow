# Skill: reviewer-verification

## Purpose

Independently review test adequacy, impact map, evidence quality, and regression coverage.

## Inputs

- `contract`
- `impact_map`
- `test_results`
- `evidence_report`


## Outputs

- `verification_review_report`


## Procedure

1. Check scenario coverage.
2. Check required tests.
3. Detect weakened/missing tests, and confirm the red→green evidence pair exists for test-bound acceptance scenarios (a captured failing run before implementation, passing run after — ADR-0017); a test only ever green, or never run against broken code, is a finding.
4. Check evidence gaps.
5. Classify issues.


## Quality bar

- Missing tests are concrete.
- Evidence gaps are actionable.


## Anti-patterns

- Accepting vague evidence.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.


## Review-agent execution rule

This skill is a read-only review-agent skill.

It runs only after a verification gate has produced a gate report and evidence
bundle. It must not run tests, execute scripts, modify files, generate patches, or
update evidence. If additional verification is needed, report it as a finding for
workflow/human decision.


## Candidate finding rule

Reviewer findings are candidate findings, not authoritative truth. The reviewer must ground each finding in contract/evidence context and provide a relevance claim, but the main/orchestrating agent validates relevance before the finding becomes an accepted issue or required change.

## Interaction protocol

This reviewer produces candidate findings only. It must assign stable finding ids
where possible, mark P0/P1 items as candidate blockers, and provide evidence and
relevance claims.

The main/orchestrating agent validates findings using the decision matrix in
`docs/review-agent-interaction-protocol.md`. Review findings do not become required
changes until that validation occurs.

Default loop rule: repeated review agents are not rerun when there are no validated
blocking findings and no mandatory evidence gaps.

## Tool permission rule

This reviewer is read-only by default. Tool use is exceptional and must be explicitly granted by the workflow, reviewer manifest, or prompt. Any tool observation remains a candidate finding and does not replace verification-gate evidence.
