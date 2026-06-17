# Skill: Reviewer Product Spec

## Purpose

Read-only reviewer for specification-first workflows. It checks whether the project
or feature specification is understandable, scoped, testable, and ready to become
contracts/ADR candidates.

## Read-only rule

This is a review-agent skill. It runs only after the workflow's relevant gate has
produced evidence. It must not run tests, execute scripts, modify files, update
contracts, or generate patches. Missing verification or missing specification evidence
must be returned as a finding.

## Focus

- problem clarity;
- user/value framing;
- non-goals and boundaries;
- ambiguity and unstated assumptions;
- readiness for ADR candidates;
- readiness for initial BDD/task contracts.

## Output

Use `templates/reviewer-report.md`. Classify issues as P0/P1/P2/P3/NOTE.


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
