# ADR-0008: Review Agent Interaction Protocol

Status: Accepted

Date: 2026-06-17

## Context

AgentsFlow already defines two general review-agent rules:

1. Review agents run after verification gates and remain read-only.
2. Review-agent findings are candidate findings until the main/orchestrating
   agent validates their relevance.

The next required step is to formalize the interaction loop between review agents,
fusion, and the main/orchestrating agent. Without a clear protocol, workflows may
fall into repeated review cycles, treat reviewer findings as truth, or rerun
review agents unnecessarily.

## Decision

AgentsFlow introduces a Review Agent Interaction Protocol.

The protocol defines:

- candidate vs validated findings;
- candidate blocking vs validated blocking findings;
- default blocking severity semantics;
- default review-cycle exit criterion;
- rerun triggers and non-triggers;
- main-agent relevance-validation procedure;
- decision matrix for finding validation;
- final review-cycle decision states.

The default exit criterion is:

```text
Exit the review cycle when there are no validated blocking findings and no
mandatory evidence gaps.
```

By default, P0/P1 findings are blocking only after relevance validation, while
candidate P0/P1 findings must be preserved and explicitly validated.

Missing mandatory evidence is blocking by default.

## Rationale

Review agents are useful because they provide independent perspectives. They are
also fallible: they can produce false positives, irrelevant objections, duplicate
findings, or findings based on incomplete evidence.

The main/orchestrating agent therefore needs a structured triage process rather
than blindly accepting or ignoring reviewer output.

A decision matrix makes the process repeatable without requiring it to be fully
deterministic or purely mechanical.

## Consequences

- Workflows can configure their review cycles, but must declare exit and rerun
  policy explicitly when they deviate from defaults.
- P0/P1 candidate findings cannot be erased by majority vote or silently ignored.
- Non-blocking findings do not trigger repeated review cycles by default.
- Implementation agents, when introduced later, must receive validated accepted
  issues rather than raw reviewer findings as mandatory work.

## References

- `docs/review-control-model.md`
- `docs/review-agent-interaction-protocol.md`
- `templates/finding-validation-report.md`
- `templates/review-cycle-report.md`
