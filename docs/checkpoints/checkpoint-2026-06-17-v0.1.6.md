# Checkpoint: AgentsFlow v0.1.6

## Accepted in this checkpoint

### Planning Agent is reserved, not default

Current workflows treat planning as a human-guided phase coordinated by the
main/orchestrating agent. `Planning Agent` remains a reserved optional future
actor, like `Implementation Agent`.

### Verification Gate is instrument-agnostic

Verification Gate is an evidence-producing control point. It may run any
workflow-declared verification instruments, including tests, deterministic scripts,
static analysis, dynamic analysis, debuggers, trace/log/network analysis, profilers,
fuzzers, benchmarks, security scanners, and domain-specific tools.

### Review agents are read-only by default, but explicit tool exceptions are possible

Reviewer tool use must be explicitly declared by workflow, reviewer manifest, or
prompt. Tool observations remain candidate findings and do not replace gate
evidence.

### Fusion Agent is synthesis, not orchestration

Fusion Agent does not launch reviewers/gates by default. It consumes reports and
evidence, synthesizes consensus/disagreement/blockers, and may recommend additional
review or verification. The main/orchestrating agent owns orchestration.

## Added files

- `docs/actor-model.md`
- `docs/workflow-phase-schema.md`
- `docs/adr/ADR-0009-actor-model-and-fusion-semantics.md`
- `schemas/actor.schema.json`
- `schemas/workflow-phase.schema.json`

## Updated files

- `README.md`
- `AGENTS.md`
- `docs/review-control-model.md`
- `docs/review-agent-interaction-protocol.md`
- `docs/review-fusion-model.md`
- `docs/specification-and-plan-mode.md`
- `schemas/workflow.schema.json`
- `schemas/reviewer.schema.json`
- `templates/workflow.yaml`
- `workflows/*/workflow.yaml`
- `skills/reviewer-*/skill.yaml`
- `skills/reviewer-*/SKILL.md`
- `skills/fusion-synthesis/*`

## Remaining open questions

- Whether v0.2 should include stricter semantic validation of workflow phases.
- Which workflows should be production-quality first.
- Whether to define a future Planning Agent protocol.
- Whether to define a future Implementation Agent protocol.
- How to represent advanced tool-enabled review safely in examples.
