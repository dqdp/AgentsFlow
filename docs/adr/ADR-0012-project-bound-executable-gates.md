# ADR-0012: Project-Bound Executable Gates

## Status

Accepted.

## Context

The Gate Executability Rule says every concrete gate included in a workflow must
have a deterministic runner entrypoint. However, AgentsFlow upstream cannot know
project-specific commands, languages, CI systems, tooling, test suites or domain
verification instruments.

## Decision

AgentsFlow upstream defines gate contracts, templates, schemas, generic validators
and runner interfaces.

Project bindings/overlays define concrete executable gates by mapping upstream
gate contracts to project-specific deterministic runners, commands, tools and
evidence sources.

A gate is not considered executable for a real workflow run until it is bound to
a deterministic project-level runner.

## Consequences

- Upstream workflows stay portable and project-agnostic.
- Real projects remain responsible for executable verification details.
- `validate_repo.py` validates upstream consistency.
- `validate_project_binding.py` validates project overlays.
- Review and fusion consume gate reports but do not replace project-bound gates.
