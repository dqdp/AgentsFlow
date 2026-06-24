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

Updated for review-gate hardening on 2026-06-24: `homogeneous-plus-focused`
is a first-class elevated-risk topology. Its homogeneous baseline pair may use
different providers, such as Codex and Claude, but the two baseline generalists
must receive the same substantive prompt, same review packet, same rubric and
same output schema. Provider transport metadata may differ.

Focused reviewers receive the same full review packet and diff plus an explicit
focus zone. A focus zone is not an ownership boundary: a focused reviewer may
and should report any plausible P0/P1 blocker noticed outside the focus.

Run artifacts should record equality evidence for the homogeneous baseline
pair, such as shared prompt-content, packet-content, rubric and output-schema
hashes. Full rendered prompts may differ only for technical identity, provider
or transport fields.

## Context

Multi-model review and fusion are valuable but should not become a separate heavyweight mode that competes with workflows.

## Decision

Review/fusion is modeled as a review topology selected by workflow/profile metadata.

The canonical v0.2 primary topologies are:

- `homogeneous-dual`;
- `homogeneous-plus-focused`;
- `heterogeneous-variable`.

`collision-control` is a focused control topology for rejected or downgraded
plausible blocker-path findings. It is not a normal primary gate topology.

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
