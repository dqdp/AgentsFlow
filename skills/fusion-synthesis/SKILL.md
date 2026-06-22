# Skill: fusion-synthesis

## Purpose

Synthesize independent reviewer reports into consensus, disagreements, candidate blockers, and recommended verdict. Fusion is decision support; it does not turn reviewer findings into authoritative truth.

## Inputs

- `contract`
- `review_reports`
- `evidence_report`
- `risk_surface_profile`
- `failure_path_matrix`
- `evidence_freshness`


## Outputs

- `fusion_report`
- `recommended_verdict`
- `human_decision_items`


## Procedure

1. Run mechanical intake: confirm expected reviewer reports exist, are
   schema-valid, fresh for the latest material change and match the declared
   reviewer assignment, provider, role and topic where applicable.
2. Extract canonical finding metadata while preserving source findings: source
   report, provider, model, topic, role, severity, evidence references, risk
   surface and Failure Path Matrix row when available.
3. Group findings as duplicate, related, or conflict. True duplicate groups keep
   the highest candidate severity until relevance validation.
4. Compare reviewer findings, including topic-pair comparison when a topology
   mirrors providers or roles over the same topic.
5. Identify consensus.
6. Identify disagreements.
7. Surface any P0/P1 candidate blocker.
8. Surface missing or stale risk-surface/FPM evidence as candidate mandatory
   evidence gaps when reviewers report it.
9. Preserve relevance questions and disagreements.
10. Assign recommended verdict and proposed required changes.
11. Hand off candidate findings for main-agent relevance validation.


## Quality bar

- No plausible candidate blocker is hidden by majority vote.
- Disagreements are preserved.
- Findings remain candidate findings until the main/orchestrating agent validates relevance.
- FPM coverage and freshness gaps are preserved as evidence issues, not
  averaged away.


## Anti-patterns

- Averaging away blocking issues.
- Reclassifying missing selected risk-path evidence as nonblocking without
  main-agent relevance validation.


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

## Authority boundary

Fusion is not an automatic acceptance gate and does not own human-mediated
decisions. Deterministic automation may validate reviewer-report structure,
schema, freshness and evidence references. Fusion provides decision support.
The main/orchestrating agent validates candidate findings. Human-mediated gates
remain human-owned and require normalized human decisions before acceptance is
claimed.
