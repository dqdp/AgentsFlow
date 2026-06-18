# ADR-0014: Project Initialization and Research Assignment

## Status

Accepted in v0.1.9, refined in v0.1.10, and refined for v0.2 with a
human operating-decisions interview.

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
human operating decisions
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

## v0.2 refinement: operating decisions are collected by dialogue

Project initialization must not rely only on model-filled inventory and expert
recommendations. Before drafting the project overlay, the main/orchestrating
agent conducts an agent-led dialogue with the human project owner to decide how
AgentsFlow should operate in the concrete project.

This step must not be implemented as "here is a YAML/JSON file, fill it in." The
agent asks focused questions, offers evidence-grounded defaults where appropriate,
summarizes decisions back to the human, and then records the normalized result as
`project-operating-decisions.yaml`.

The dialogue covers at least:

```text
- verification gate blockers and advisory checks;
- canonical commands and required evidence;
- reviewer count, reviewer roles and model/harness diversity;
- whether external reviewers are allowed and what context they may receive;
- maximum review cycles and escalation conditions;
- authority for scope, gate, topology, migration and residual-risk decisions;
- evidence storage, raw log and redaction policy.
```

Unresolved operating decisions remain explicit. They must not silently become
project defaults during overlay drafting.
