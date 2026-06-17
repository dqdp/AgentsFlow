# Workflow Model

## Definition

A workflow is a named, reusable process for a class of agent-assisted development work.

A workflow answers:

- What is the goal of this work?
- What artifacts are expected?
- Which skills are invoked?
- Which scripts are mandatory or optional?
- Which templates should be used?
- Which domain packs can parameterize it?
- Which strictness profiles are supported?
- Which review topologies make sense?

## Workflow is the primary abstraction

Strictness is not the primary abstraction. Strictness only changes how deep the gates go.

Example:

```yaml
workflow: prompt-behavior-eval
domain_pack: coding-agent
strictness: L4
review_topology: adversarial-fusion
```

The workflow defines the type of work. The strictness profile controls depth.

## Workflow manifest shape

See `schemas/workflow.schema.json` and `templates/workflow.yaml`.

Minimal fields:

```yaml
name: big-feature-contract-first
version: 0.1
intent: "Design and implement a large feature through a contract-first process."
entry_criteria: []
outputs: []
uses:
  skills: []
  scripts: []
  templates: []
supported_profiles:
  strictness: []
  review_topologies: []
```

## Current workflows

| Workflow | Purpose |
|---|---|
| `new-project-spec-first` | Start a new project with problem framing, specs, ADR seeds, and initial contracts. |
| `big-feature-contract-first` | Implement a large feature through contract, BDD scenarios, impact map, verification, evidence. |
| `agentic-system-hardening` | Harden agent systems: prompts, tools, memory, context, policy, model router, traces. |
| `prompt-behavior-eval` | Evaluate changes to prompts/skills/instructions using behavioral scenarios. |
| `safe-refactor` | Perform scoped refactoring with boundary and regression protection. |
| `bugfix-regression-capture` | Reproduce a bug, fix it, and convert it into a regression scenario. |
| `research-to-ADR` | Turn research into decision memos and ADRs. |
| `review-only-fusion` | Run independent review and fusion on an existing artifact or diff. |

## Workflow selection guidance

Use `new-project-spec-first` when the main risk is ambiguous initial direction.

Use `big-feature-contract-first` when the main risk is scope creep or architecture drift during implementation.

Use `agentic-system-hardening` when the main risk is runtime behavior of agents, tools, memory, or policy.

Use `prompt-behavior-eval` when the main artifact is a prompt, instruction set, or skill behavior.

Use `safe-refactor` when behavior should remain stable and scope boundaries matter.

Use `bugfix-regression-capture` when a known failure must become a permanent scenario.

Use `research-to-ADR` when implementation should not start until alternatives and decisions are explicit.

Use `review-only-fusion` when the work is already done and the need is independent review.

## Workflow definition, project binding and workflow run

AgentsFlow separates three levels:

```text
Workflow Definition
  Universal upstream process shape under `workflows/`.

Project Binding / Overlay
  Project-specific mapping from workflow requirements to repo paths, commands,
  gates, instruments, evidence sources and local rules.

Workflow Run
  Concrete task instance with task contract, plan, behavior bindings, gate reports,
  evidence bundle, reviewer reports, finding validation and fusion report.
```

Upstream workflow definitions must not be edited for each project. Projects
should create `.agentsflow/` overlays and workflow binding files.
