# ADR-0005: Review Agents Run After Verification Gates

## Status

Accepted for v0.1.1 draft.

## Context

The project uses verification gates, review agents, and fusion as composable control
primitives. If review agents are allowed to run tests or mutate artifacts, their role
becomes ambiguous: they stop being independent evaluators and start acting as
implementation or verification executors.

The project may later introduce implementation agents with broader permissions, but
those rules must not leak into the review-agent protocol.

## Decision

Review agents are read-only and run only after a verification gate has produced the
required evidence.

The verification gate is responsible for executing tests, deterministic scripts,
contract checks, boundary checks, impact-map checks, and evidence validation.

Review agents consume the gate report and evidence bundle. They may identify missing
or insufficient verification and request additional checks as findings, but they must
not run those checks themselves.

Fusion also remains read-only and synthesizes reviewer reports without executing
checks or modifying artifacts.

## Consequences

- Review reports are grounded in explicit verification evidence.
- Review agents remain independent and easier to compare/fuse.
- Workflows can vary the number of reviewers and gates while preserving a common
  actor model.
- Missing verification becomes a review finding, not an implicit action performed by
  the reviewer.
- Future implementation-agent rules can be added separately without weakening the
  review-agent safety boundary.
