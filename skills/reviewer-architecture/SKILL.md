# Skill: reviewer-architecture

## Purpose

Independently review artifacts for architecture consistency, modularity, scope, and ADR drift.

## Inputs

- `contract`
- `diff_or_artifact`
- `adrs`
- `evidence_report`


## Outputs

- `architecture_review_report`


## Procedure

1. Read contract and fixed decisions.
2. Check boundary preservation.
3. Check module design.
4. Flag architecture drift.
5. Classify issues by severity.


## Quality bar

- Review is grounded in contract and ADRs.
- Blocking issues are explicit.


## Anti-patterns

- Reviewing by taste without contract reference.


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
