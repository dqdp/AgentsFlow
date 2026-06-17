# ADR-0002: Contract-First Behavior Layer

Status: Accepted for v0.1 design seed

## Context

Agent-assisted development needs a higher-level behavioral layer above ordinary tests. Unit tests and integration tests do not fully constrain agent process behavior, scope boundaries, prompt behavior, memory policy, tool usage, or evidence quality.

## Decision

Task/feature contracts are the source of truth for non-trivial workflows.

BDD/Gherkin scenarios are used inside contracts to express observable behavior, forbidden behavior, and regression scenarios.

## Consequences

Positive:

- human-readable contracts;
- better review focus;
- more explicit forbidden behavior;
- easier mapping to tests, trace assertions, and review checklists.

Negative:

- risk of overusing Gherkin for trivial cases;
- requires style discipline;
- requires binding scenarios to actual checks where possible.
