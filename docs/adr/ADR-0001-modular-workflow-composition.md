# ADR-0001: Modular Workflow Composition

Status: Accepted for v0.1 design seed

## Context

The project could be organized as a set of large workflow prompts. That would be simple at first but would quickly cause duplication and inconsistency.

## Decision

Workflows are orchestration recipes composed from reusable skills, scripts, templates, packs, and profiles.

Skills and scripts are first-class building blocks.

## Consequences

Positive:

- workflows stay small;
- skills are reusable;
- deterministic checks can be shared;
- domain-specific behavior can be injected through packs;
- review/fusion can be a topology rather than a separate methodology.

Negative:

- more files and manifests;
- requires discipline to avoid duplicating skill internals in workflows;
- needs schema/lint support over time.
