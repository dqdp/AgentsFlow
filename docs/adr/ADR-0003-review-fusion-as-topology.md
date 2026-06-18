# ADR-0003: Review Fusion as Review Topology

Status: Accepted for v0.1 design seed

Updated for v0.2: primary review gates require two or more reviewers. A single
reviewer is allowed only as a control-review exception after a rejected blocker
collision.

v0.2 also replaces the early narrative topology labels below with the canonical
profile names `homogeneous-dual`, `homogeneous-plus-focused`,
`heterogeneous-variable`, and `collision-control`.

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
- strictness controls depth;
- fusion can be reused across workflows;
- blocking issues can be surfaced consistently.

Negative:

- requires clear reviewer report templates;
- requires fusion rules;
- generic multi-model automation remains future work; a minimal Claude Code external reviewer provider is accepted for the v0.2 MVP under ADR-0016.
