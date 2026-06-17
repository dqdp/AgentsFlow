# BDD Scenario Style Guide

## Purpose

BDD scenarios are used as a human-readable behavioral layer above tests and evals.

They should describe what must be true about system or agent behavior. They are not a replacement for unit tests.

## Good scenarios

Good scenarios are:

- concrete;
- observable;
- checkable;
- focused on one behavior;
- explicit about forbidden behavior;
- linked to verification binding where possible.

## Weak words to avoid

Avoid vague assertions:

- correctly;
- properly;
- reasonably;
- as expected;
- good;
- appropriate;
- robustly;
- efficiently.

Replace them with evidence:

- specific output property;
- tool call or absence of tool call;
- trace field;
- file boundary;
- test command;
- reviewer-verifiable claim.

## Scenario types

### Product behavior

What the product should do.

### Agent behavior

How the coding/implementation agent should behave.

### Process behavior

What evidence, gates, and review steps are required.

### Safety/policy behavior

What is forbidden without approval.

### Regression behavior

What must never happen again after a known failure.

## Anti-patterns

### Exact output snapshots for non-deterministic agents

Prefer property-based assertions over exact long text matches.

### UI-level detail too early

Do not lock implementation details before architecture is stable.

### Scenario explosion

Do not write Gherkin for every unit test. Use scenarios for behavior with product, architecture, policy, or agentic risk.
