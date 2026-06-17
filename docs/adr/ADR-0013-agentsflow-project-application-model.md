# ADR-0013: AgentsFlow Project Application Model

## Status

Accepted in v0.1.9.

## Context

AgentsFlow must be applied to concrete repositories without mixing upstream methodology, project-specific bindings and task-specific run artifacts. Without a clear structure, projects can easily turn AgentsFlow usage into a confusing collection of prompts, scripts and reports.

## Decision

AgentsFlow is applied to a project as a pinned upstream dependency plus a project-specific overlay.

For the first stage, supported installation/pinning modes are limited to:

```text
- Git submodule
- CMake FetchContent / FetchPackage-style dependency
```

CLI/package distribution is deferred.

The project overlay binds upstream workflows and gate contracts to concrete repository paths, commands, runners, tools, evidence sources and review policies.

Concrete workflow runs store task-specific contracts, plans, behavior bindings, gate reports, evidence, reviewer reports, finding validation, fusion reports and final decisions.

## Consequences

- Upstream AgentsFlow remains reusable and project-independent.
- Project-specific execution details live in `.agentsflow/` overlay files.
- Task-specific history lives in `Docs/agentsflow/runs/`.
- Upstream upgrades become explicit process changes, not accidental drift.
