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
