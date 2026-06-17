# Skill: fusion-synthesis

## Purpose

Synthesize independent reviewer reports into consensus, disagreements, candidate blockers, and recommended verdict. Fusion is decision support; it does not turn reviewer findings into authoritative truth.

## Inputs

- `contract`
- `review_reports`
- `evidence_report`


## Outputs

- `fusion_report`
- `recommended_verdict`
- `human_decision_items`


## Procedure

1. Compare reviewer findings.
2. Identify consensus.
3. Identify disagreements.
4. Surface any P0/P1 candidate blocker.
5. Preserve relevance questions and disagreements.
6. Assign recommended verdict and proposed required changes.
7. Hand off candidate findings for main-agent relevance validation.


## Quality bar

- No plausible candidate blocker is hidden by majority vote.
- Disagreements are preserved.
- Findings remain candidate findings until the main/orchestrating agent validates relevance.


## Anti-patterns

- Averaging away blocking issues.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.


## Fusion execution rule

Fusion is read-only and runs after verification and reviewer reports exist. It must
not run tests, execute scripts, modify artifacts, erase candidate blocking issues by
majority vote, or claim that reviewer findings are accepted truth before relevance
validation.

## Review cycle handoff

Fusion must explicitly hand off candidate blockers to the main/orchestrating agent
for relevance validation. Fusion may recommend a review-cycle decision, but the
default exit condition is satisfied only after validation shows no validated
blocking findings and no mandatory evidence gaps.

Fusion must not trigger repeated review cycles for non-blocking findings alone.

## Orchestration boundary

Fusion is not the workflow orchestrator. It does not launch reviewers, run verification gates, run tests, call tools, or modify artifacts by default. It may recommend additional review or verification, but the main/orchestrating agent owns the decision to run another cycle.
