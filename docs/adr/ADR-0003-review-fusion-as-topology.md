# ADR-0003: Review Fusion as Review Topology

Status: Accepted for v0.1 design seed

Updated for v0.2: primary review gates require two or more reviewers.
Collision-control is also a two-reviewer exception: rejected or downgraded
plausible blocker-path candidate findings from the same review cycle are
recorded as one collision batch and sent to two fresh-context control reviewers.

v0.2 also replaces the early narrative topology labels below with the canonical
profile names `homogeneous-dual`, `homogeneous-plus-focused`,
`heterogeneous-variable`, and `collision-control`.

Updated for default strictness: review topology remains separate from strictness.
Workflows own their normal depth through `default_strictness`; project or run
overrides are explicit deviations, not routine setup choices.

Proposed follow-up: ADR-0021 should make provider and invocation evidence
observable for mixed-provider review gates. `homogeneous-plus-focused` keeps the
homogeneous baseline property: the baseline generalists receive the same
substantive packet, prompt, rubric and output schema, while provider transport
metadata may differ. Focused reviewers receive the full review packet plus an
explicit focus zone; the focus zone does not prevent them from reporting
plausible P0/P1 blockers outside that focus.

## Context

Multi-model review and fusion are valuable but should not become a separate heavyweight mode that competes with workflows.

## Decision

Review/fusion is modeled as a review topology selected by workflow/profile metadata.

Historical seed examples:

- none;
- dual independent;
- triad fusion;
- adversarial fusion;
- multi-model fusion.

## Consequences

Positive:

- workflows decide when review is needed;
- workflow default/effective strictness controls depth;
- fusion can be reused across workflows;
- blocking issues can be surfaced consistently.

Negative:

- requires clear reviewer report templates;
- requires fusion rules;
- generic multi-model automation remains future work; a minimal Claude Code external reviewer provider is accepted for the v0.2 MVP under ADR-0016.
