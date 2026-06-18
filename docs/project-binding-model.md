# Project Binding / Overlay Model

## Status

Accepted in v0.1.8.

## Problem

AgentsFlow upstream defines reusable workflows and gate contracts. A concrete
software project has project-specific realities: language, test commands, CI,
repository layout, ADR paths, domain tools, performance checks, network analysis
commands, evidence locations, and local conventions.

Those details must not be hard-coded into upstream workflow definitions.

## Three levels

```text
Level 1: AgentsFlow upstream
  Universal methodology, workflow definitions, gate contracts, schemas,
  templates, generic validators and runner interfaces.

Level 2: Project binding / overlay
  Project-specific mapping from upstream workflow/gate requirements to concrete
  repository paths, commands, tools, runners, evidence sources and review policy.

Level 3: Workflow run / task instance
  Task-specific contract, plan, behavior bindings, gate reports, evidence bundle,
  reviewer reports, finding validation and fusion reports.
```

## Workflow definition vs binding vs run

```text
Workflow Definition = reusable upstream process shape.
Workflow Binding    = project-specific configuration for that workflow.
Workflow Run        = concrete task instance with artifacts and evidence.
```

## Core rule

```text
AgentsFlow workflows define process shape.
Project bindings define execution details.
Workflow runs contain task-specific artifacts and evidence.
```

## Example project overlay

```text
my-project/
  AGENTS.md
  .agentsflow/
    project.yaml
    agentsflow.lock.yaml
    workflows/
      big-feature-contract-first.binding.yaml
    gates/
      verification_gate.yaml
      plan_gate.yaml
    scripts/
      run_verification_gate.sh
      run_unit_tests.sh
      run_static_analysis.sh
    profiles/
      default.yaml
  Docs/agentsflow/runs/<run-id>/
    task.contract.md
    behavior.bindings.yaml
    plan.md
    verification-gate-report.md
    evidence/
    reviewer-report.*.md
    finding-validation-report.md
    fusion-report.md
```

## Canonical v0.2 overlay shape

Use one project manifest shape in v0.2. `.agentsflow/project.yaml` is a flat
project-level manifest:

```yaml
name: my-project
agentsflow_version: 0.2

paths:
  docs_root: Docs/
  adr_root: Docs/adr/
  agentsflow_root: .agentsflow/
  runs_root: Docs/agentsflow/runs/

project_rules:
  default_workflow: big-feature-contract-first

verification_defaults:
  evidence_root: Docs/agentsflow/evidence/
  ci_source: local-or-ci
```

Do not use a nested shape such as:

```yaml
project:
  name: my-project
application:
  upstream_mode: git-submodule
```

Pinning and upstream source information belongs in `.agentsflow/agentsflow.lock.yaml`,
not in `project.yaml`.

## Canonical workflow binding shape

Workflow bindings live under `.agentsflow/workflows/*.binding.yaml`.

`extends` points to a workflow inside the pinned AgentsFlow upstream root. Gate
`extends` paths also point to upstream gate contracts. Gate `manifest` and
`runner` paths point to project-local overlay files.

```yaml
workflow: big-feature-contract-first
extends: workflows/big-feature-contract-first/workflow.yaml
agentsflow_version: 0.2

binding:
  project: my-project
  docs_root: Docs/
  runs_root: Docs/agentsflow/runs/

gates:
  verification_gate:
    extends: gates/verification_gate.yaml
    manifest: .agentsflow/gates/verification_gate.yaml
    runner: .agentsflow/scripts/run_verification_gate.sh

behavior_bindings:
  default_pattern: "Docs/agentsflow/runs/*/*.bindings.yaml"

review:
  topology: homogeneous-dual
  composition: homogeneous
  reviewers:
    - generalist-a
    - generalist-b
  prompt_policy:
    same_prompt: true
    same_packet: true
    same_rubric: true
    same_output_schema: true
  context_policy:
    start_mode: fresh_context
    fork_conversation_context: false
    allowed_context_sources:
      - review_packet
      - referenced_artifacts
```

This shape is validated by `scripts/validate_project_binding.py`.

## Gate contract vs project-bound executable gate

Upstream gate manifests are **gate contracts/templates**. They define what must be
proved and what interface the project must provide.

Project bindings create **project-bound executable gates** by mapping those
contracts to deterministic project-level runners.

```text
A gate is not executable for a real workflow run until it is bound to a deterministic project-level runner.
```

## Non-goal

Do not edit upstream workflow definitions for each project. Create a project
binding/overlay instead.


## First-stage pinning modes

Accepted in v0.1.9: initial project application supports only:

```text
- Git submodule
- CMake FetchContent / FetchPackage-style dependency
```

CLI/package distribution is deferred.

Projects should record the pinned upstream in `.agentsflow/agentsflow.lock.yaml`.
