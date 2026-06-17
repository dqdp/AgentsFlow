# ADR-0004: Specification Development Is First-Class

Status: Proposed

## Context

The v0.1 design has stronger coverage for contracts, BDD scenarios, review, and evidence than for the upstream process of specification development.

Modern coding-agent harnesses increasingly expose planning modes, goal modes, plan-review flows, and read-only repository grounding. These need separate investigation before this project encodes a strong opinion.

## Proposed decision

Specification development should become a first-class capability area with its own workflows, skills, scripts, and templates.

Candidate additions:

- `plan-review-before-implementation` workflow;
- `plan-grounding` skill;
- `specification-discovery` skill;
- `architecture-option-mapping` skill;
- `spec_lint.py` and `plan_lint.py` scripts.

## Consequences

Positive:

- avoids premature implementation;
- makes plan mode more rigorous;
- improves new-project and big-feature workflows;
- creates a bridge from research to ADRs and contracts.

Open questions:

- Should plan mode be a workflow or a reusable phase pattern?
- How much plan structure should be mandatory?
- How should plan changes be tracked after user corrections?
