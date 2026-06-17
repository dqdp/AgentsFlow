# Checkpoint: AgentsFlow v0.1.10

## Status

Design checkpoint after project-initialization refinement and bird-eye retrospective.

## Newly accepted decisions

### 1. Unknown-project discovery is not an empty prompt

Unknown-project discovery must use a standard exploratory research assignment.

Canonical template:

```text
templates/research-assignment.unknown-project.md
```

The user must still be given a chance to provide goals, known direction, constraints, non-goals, project ownership context, and domain concerns before analysis proceeds.

### 2. Research assignment must include domain identification

Researcher agents must explicitly identify apparent project domain(s), for example trading/HFT, developer tooling, infrastructure, AI agents, healthcare, robotics, etc.

For every domain classification, researcher agents must separate:

```text
observed evidence
model inference
confidence
requires_human_confirmation
```

### 3. User domain expertise must be queried

Project initialization must ask whether the user has domain expertise and whether the user's domain knowledge should constrain:

```text
workflow bindings
gate strategy
reviewer selection
domain packs
accepted decisions
initialization recommendations
```

### 4. Domain assumptions are not facts

Domain assumptions must be separately recorded and treated as model-inferred until confirmed by user-provided context or project documentation.

## Files added or updated

```text
templates/research-assignment.unknown-project.md
templates/project-intake.yaml
templates/project-inventory.json
templates/project-assessment.json
schemas/project-intake.schema.json
schemas/project-inventory.schema.json
workflows/project-initialization/workflow.yaml
skills/project-intake-analysis/SKILL.md
skills/project-inventory-structuring/SKILL.md
docs/project-initialization-model.md
docs/adr/ADR-0014-project-initialization-and-research-assignment.md
docs/retrospectives/bird-eye-pass-2026-06-17-v0.1.10.md
```

## Current major accepted architecture

```text
AgentsFlow = workflow kit + reference methodology.
Workflow is the primary abstraction.
Skills/scripts/templates/schemas/packs/profiles are reusable building blocks.
Contracts/evidence/gate/reviewer/fusion reports are artifacts.
Spec/Plan Mode is a reusable phase pattern, not a top-level abstraction.
Quint Code / haft is an optional external advanced planning provider.
Project binding separates upstream from concrete project execution.
Concrete gates become executable only after project-level binding.
Review agents are read-only by default and produce candidate findings.
Main/orchestrating agent validates finding relevance.
Fusion is synthesis, not majority voting or orchestration.
```

## Remaining open questions

```text
1. Final v0.2 MVP-ready implementation plan.
2. How much of project initialization should be automated vs human-guided.
3. First real project to onboard with AgentsFlow.
4. How to represent domain packs for project-specific domains.
5. When to introduce a CLI/package distribution model.
6. Whether to add a dedicated AgentsFlow upgrade workflow.
```
