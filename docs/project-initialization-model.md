# Project Initialization / Onboarding Model

## Status

Accepted in v0.1.9 and refined in v0.1.10.

## Purpose

Project initialization creates the project overlay needed to use AgentsFlow in a concrete repository. It must not assume that the agent already understands the project.

Initialization separates:

```text
machine-observed facts
model-produced structured inventory
expert assessments
human-confirmed decisions
```

## Core rules

```text
No project analysis without an explicit research assignment.
Unknown project does not mean empty assignment.
No inferred metadata without provenance and confidence.
No domain assumption without evidence and confirmation status.
No project overlay without human approval.
No code-only scan when documentation/history exist.
```

## Input artifact: project intake / research assignment

Initialization starts with an explicit assignment, stored as `project-intake.yaml` or `project-intake.md`.

The assignment may be:

```text
standard exploratory
  Used for unknown-project discovery. This is not empty: it uses the standard research assignment template and gives the user a chance to provide context before scanning.

directed
  Used when the human knows project goals, intended direction, fixed decisions, or preferred AgentsFlow workflows.

problem-driven / migration-driven / risk-driven
  Used when initialization has a narrower purpose.
```

The canonical standard exploratory template is:

```text
templates/research-assignment.unknown-project.md
```

The assignment is passed to researcher agents and expert assessment agents. It gives them context, known goals, constraints, domain assumptions, and analysis focus.

## Preflight user opportunity

Even in unknown-project discovery, the user must have a chance to provide context. The initialization workflow should ask, or record that it asked, questions such as:

```text
- What do you want to understand or improve in this project?
- Is this your project or an external/unknown project?
- Is there a known direction of development, migration, refactor, or process improvement?
- Are there known constraints, accepted decisions, risks, or non-goals?
- Are there domain-specific concerns that may not be fully documented in the repository?
```

If the user provides no additional context, the workflow proceeds with the standard exploratory assignment.

## Required analysis scope

Initialization must analyze more than code when those artifacts exist:

```text
- source code and tests;
- build/package/config files;
- README and project documentation;
- ADRs and architecture notes;
- AGENTS.md / CLAUDE.md / Cursor rules / Codex instructions;
- implementation history recorded in Markdown files;
- migration notes, runbooks, changelogs, postmortems, task reports;
- CI, scripts and existing process artifacts;
- domain-specific docs, protocols, APIs and operational rules.
```

Implementation history in Markdown is especially important because agentic projects often store real decisions, constraints, unfinished migrations and known problems in planning or task-report documents.

## Domain identification and domain expertise

Project initialization must explicitly identify the apparent project domain or domains.

For every domain classification, the inventory must separate:

```text
observed evidence
model inference
confidence
requires_human_confirmation
```

Domain identification is model-inferred unless directly stated by the user or by project documentation. It must not be treated as authoritative until confirmed when it affects workflow bindings, gates, domain packs, review roles, or accepted decisions.

Initialization must ask or record domain-expertise questions for the user:

```text
- What domain is this project in?
- Are you a domain expert for this project?
- Should your domain knowledge be treated as authoritative for initialization decisions?
- Are there domain-specific constraints, regulations, safety concerns, latency requirements, financial risks, privacy requirements, operational rules, or compliance obligations that the repository may not fully document?
- Are there domain terms, abbreviations, protocols, exchanges, APIs, devices, business rules, or workflows that the agent must not reinterpret without confirmation?
- Should AgentsFlow use an existing domain pack for this project or create a project-specific domain pack?
- Are there accepted domain decisions that should be treated as fixed constraints?
```

## Two initialization modes

### Unknown project discovery

Used when no reliable prior context is known.

This is not an empty assignment. It uses the standard exploratory research assignment and emphasizes observed facts, inferred judgments, domain assumptions, unknowns, and questions for humans.

### Directed onboarding

Used when the project owner provides known goals and intended direction.

The analysis must take those inputs into account; for example, assessing readiness for specific AgentsFlow workflows or gate policies.

## Data layers

### Layer 1: raw scan

A generic scanner collects observable repository facts where possible:

```text
file tree, config files, candidate build systems, CI files, docs roots, source/test roots, scripts, AGENTS.md-like files, git status.
```

Output: `project-raw-scan.json`.

### Layer 2: structured inventory

The main/orchestrating agent uses raw scan evidence plus selected project documents to fill `project-inventory.json` according to schema.

The format is deterministic. The truth of some fields may still be model-inferred.

Every non-trivial field should include:

```text
source_type
provenance/evidence
confidence
requires_human_confirmation
```

Domain-related fields must additionally separate observed evidence from domain assumptions.

### Layer 3: expert assessment

Read-only expert agents produce candidate assessments:

```text
architecture readiness
verification strategy
workflow recommendations
gate recommendations
domain risks
open questions
```

Their findings are candidate findings and follow the review-finding validation model.

### Layer 4: human confirmation

The human approves or corrects the project overlay, disputed inventory fields, domain assumptions, workflow selection and gate strategy.

## Initialization workflow

```text
1. Read project intake / research assignment.
2. Ask or record preflight user context/domain-expertise questions.
3. Attach or verify pinned AgentsFlow upstream.
4. Run raw project scan.
5. Discover documentation and implementation history.
6. Produce structured project inventory, including domain identification.
7. Run expert assessments.
8. Collect human questionnaire / clarifications.
9. Draft project overlay.
10. Draft project-bound gates.
11. Optionally use haft/quint-code for advanced decision engineering.
12. Validate project overlay.
13. Produce initialization report.
14. Human approval.
```

## Modes of operation

```text
scan-only
  Produce raw scan, inventory, assessment and questions. Do not create overlay files.

draft-overlay
  Create draft `.agentsflow/` overlay files for human review.

apply-approved
  Apply approved overlay after human confirmation.
```

Default mode should be `scan-only + draft-overlay`.


## Legacy agent-system adoption

Existing projects may already contain agent instructions, skills, prompts, workflow docs and process artifacts. Initialization must not simply add AgentsFlow on top of them.

Before drafting the final project overlay, initialization must run a legacy adoption step:

```text
legacy agent-system discovery
legacy documentation/process classification
adoption mode decision
backup/quarantine if required
knowledge extraction / patch / rebuild / shadow pilot
active instruction map creation
validation that no ambiguous authority remains
human approval
```

Supported adoption modes:

```text
full-archive-rebuild
knowledge-extraction
minimal-patch-adapt
shadow-pilot
```

The final state must have one active agent-instruction authority layer. Every legacy artifact must be classified as active, imported, archived, deprecated, non-authoritative, or needs-human-decision.

See:

```text
docs/legacy-agent-system-adoption-model.md
docs/adr/ADR-0015-legacy-adoption-modes.md
```

## Optional haft / Quint Code integration

Project initialization is one of the best places to use haft/quint-code as an optional advanced decision-engineering provider.

Use it when:

```text
- project direction is unclear;
- workflow strategy is contested;
- gate strategy has long-term consequences;
- architecture/process decisions need frame/explore/compare/decide/verify;
- target system vs enabling system split is important;
- domain constraints need explicit decision contracts.
```

Expected outputs must be normalized into AgentsFlow artifacts:

```text
term-map.md
target-system-spec.md
enabling-system-spec.md
decision-contract.md
project-assessment.md
initialization-report.md
```

## Non-goals

Initialization does not implement features, rewrite source code, or silently apply process changes without approval.
