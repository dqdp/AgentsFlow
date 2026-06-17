# ADR-0014: Project Initialization and Research Assignment

## Status

Accepted in v0.1.9 and refined in v0.1.10.

## Context

AgentsFlow needs a repeatable way to onboard existing projects. A project may be unknown, or the human may already know goals and intended direction. Agents must not analyze a project without context, nor infer metadata without evidence.

The phrase "unknown project" must not mean an empty prompt. It means a standard exploratory research assignment with explicit scope and output rules.

## Decision

AgentsFlow introduces a project initialization/onboarding process.

Initialization starts with an explicit research assignment / project intake brief. The brief may be standard exploratory for unknown-project discovery, or directed by known human goals for existing projects.

Even in unknown-project discovery, the workflow must give the user a chance to provide goals, constraints, known direction, domain context, or concerns before the scan proceeds. If the user provides no additional context, the workflow uses `templates/research-assignment.unknown-project.md`.

Initialization must analyze:

```text
- code;
- tests;
- build/config files;
- project documentation;
- ADRs;
- agent instructions;
- implementation history recorded in Markdown;
- CI/process artifacts;
- domain documentation and operational rules.
```

Initialization separates:

```text
machine-observed raw facts
model-produced structured inventory
model-inferred domain assumptions
expert assessments
human-confirmed decisions
```

Model-produced fields must include provenance, confidence and human-confirmation markers when appropriate.

Domain identification is mandatory. Researcher agents must identify apparent domain(s), separate observed evidence from inferred domain assumptions, and ask whether the user has domain expertise that should constrain initialization decisions.

## Consequences

- The same repository can be analyzed differently depending on the assignment.
- Unknown-project discovery is no longer underspecified or empty.
- AgentsFlow avoids pretending that generic scripts can fully understand arbitrary projects.
- Domain assumptions become explicit and reviewable.
- Researcher/expert agents produce candidate findings and recommendations, not authoritative truth.
- Project overlay creation remains subject to human approval.
