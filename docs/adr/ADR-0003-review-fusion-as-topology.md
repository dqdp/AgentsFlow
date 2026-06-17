# ADR-0003: Review Fusion as Review Topology

Status: Accepted for v0.1 design seed

## Context

Multi-model review and fusion are valuable but should not become a separate heavyweight mode that competes with workflows.

## Decision

Review/fusion is modeled as a review topology selected by workflow/profile metadata.

Examples:

- none;
- single reviewer;
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
