# ADR-0006: Specification / Plan Mode and External Planning Providers

Status: Accepted

## Context

Modern AI coding harnesses increasingly separate planning/specification from implementation. Examples include read-only plan modes, spec-first pipelines, architecture/planning agents, persistent plan artifacts, and decision-engineering tools.

AgentsFlow needs to support specification and planning without becoming a heavyweight execution platform or duplicating specialized tools.

## Decision

AgentsFlow treats Specification / Plan Mode as a reusable phase pattern and artifact protocol.

It is not a new top-level abstraction and not a single global workflow.

Workflows may include planning/specification phases at different depth depending
on workflow type, workflow default strictness, effective project/run strictness,
risk, and domain pack.

AgentsFlow core provides lightweight native planning skills/templates/gates. Advanced decision-engineering systems such as haft/quint code may be used as optional external planning providers.

## Accepted native ideas

AgentsFlow adopts the following ideas into its methodology:

- frame / explore / compare / decide / verify;
- decision contracts;
- term maps;
- target system / enabling system split;
- evidence freshness / staleness markers.

## External provider boundary

AgentsFlow does not reimplement haft/quint code and does not depend on it in core.

Optional providers must map their outputs into AgentsFlow artifacts, such as:

- research brief;
- decision contract;
- plan;
- task breakdown;
- evidence summary;
- ADR draft.

## Consequences

- AgentsFlow stays lightweight.
- High-risk workflows can still delegate deep planning to specialized external tools.
- Specification / Plan Mode can be reused across workflows without becoming a monolithic workflow.
- A future integration pack may support haft/quint code explicitly.
