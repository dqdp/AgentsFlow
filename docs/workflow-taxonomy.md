# Workflow Taxonomy

AgentsFlow classifies workflows into application, core, agent-specific and auxiliary groups.

## Application / onboarding workflow

`project-initialization` is the mandatory application workflow for applying AgentsFlow to a concrete project. It creates or drafts the project overlay, gathers intake/inventory, handles legacy adoption, and prepares project-bound gates.

## Core workflows

Core workflows define the primary development lifecycle patterns.

- `new-project-spec-first` — turn a vague project idea into specifications, initial contracts, ADR candidates, and roadmap before implementation.
- `big-feature-contract-first` — define a behavioral contract, plan, impact map, gates, and evidence before implementing a large feature.
- `bugfix-regression-capture` — reproduce a bug, capture a regression scenario, implement a minimal fix, and verify the regression does not return.
- `safe-refactor` — perform behavior-preserving refactors with explicit boundaries, impact map, verification, and rollback notes. It is non-MVP/reference for v0.2.

## Agent-specific workflows

Agent-specific workflows specialize AgentsFlow for agentic systems, prompt behavior, tools, memory, policy, context management, evals, and traces.

- `agentic-system-hardening` — non-MVP/reference for v0.2.
- `prompt-behavior-eval` — non-MVP/reference for v0.2.

## Auxiliary / utility workflows

Auxiliary workflows support research, ADR preparation, standalone review, and fusion-based decision support. They are not full implementation workflows.

- `research-to-ADR` — non-MVP/reference for v0.2.
- `review-only-fusion` — MVP review utility workflow.

`review-only-fusion` consumes existing artifacts/evidence and produces reviewer reports plus a fusion report. It must not implement or run tests.
