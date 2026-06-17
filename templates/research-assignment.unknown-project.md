# Standard Research Assignment: Unknown Project Discovery

## Purpose

You are analyzing a software project for AgentsFlow project initialization.

This is **not an empty prompt**. The user has not provided a specific project direction yet, so use the standard exploratory mode. Your job is to understand the project from repository evidence and produce structured, reviewable initialization artifacts.

Before starting, give the user an opportunity to add context. If the user provides no additional context, continue with this standard assignment.

## Preflight questions for the user

Ask the user briefly:

1. What do you want to understand or improve in this project?
2. Is this your project or an external/unknown project?
3. Is there a known direction of development, migration, refactor, or process improvement?
4. Are there known constraints, accepted decisions, risks, or non-goals?
5. Are there domain-specific concerns that may not be fully documented in the repository?

If the user does not answer or says there is no additional context, continue with unknown-project discovery.

## Primary objective

Build a structured understanding of the project:

- what the project appears to be;
- what problem it appears to solve;
- what domain or domains it appears to belong to;
- how it is organized;
- how it is built, tested, configured, and operated;
- what documentation and implementation history exist;
- what development process is implied by the repository;
- what is missing, unclear, risky, stale, contradictory, or requires human confirmation.

## Mandatory analysis scope

Analyze more than source code. Inspect and summarize evidence from:

- source code and project structure;
- build and package files;
- test directories and test configuration;
- CI/CD configuration;
- README and project documentation;
- ADRs, design documents, architecture notes;
- AGENTS.md, CLAUDE.md, Cursor/Codex/OpenCode/Roo instructions, if present;
- Markdown implementation history: previous plans, task reports, migration notes, changelogs, postmortems, runbooks;
- scripts, Makefiles, Docker/devcontainer files, deployment notes;
- domain-specific docs, protocols, API notes, operational rules, if present.

## Domain identification

Identify the apparent project domain or domains.

Examples:

- fintech / trading / HFT;
- healthcare;
- robotics;
- developer tooling;
- AI agent framework;
- infrastructure / DevOps;
- embedded systems;
- data platform;
- scientific computing;
- enterprise backend;
- consumer app;
- unknown / unclear.

For every domain classification, separate:

1. **Observed evidence** — file names, docs, APIs, protocols, terminology, dependencies, comments, configs.
2. **Model inference** — your interpretation based on the evidence.
3. **Confidence** — high / medium / low.
4. **Required human confirmation** — whether the domain identification needs user confirmation.

Do not overclaim domain understanding. If the domain is unclear, say so explicitly.

## Domain expertise questions for the user

Before finalizing project assessment, ask or record these questions:

1. What domain is this project in?
2. Are you a domain expert for this project?
3. Should your domain knowledge be treated as authoritative for initialization decisions?
4. Are there domain-specific constraints, regulations, safety concerns, latency requirements, financial risks, privacy requirements, operational rules, or compliance obligations that the repository may not fully document?
5. Are there domain terms, abbreviations, protocols, exchanges, APIs, devices, business rules, or workflows that the agent must not reinterpret without confirmation?
6. Should AgentsFlow use an existing domain pack for this project or create a project-specific domain pack?
7. Are there accepted domain decisions that should be treated as fixed constraints?

## Output separation rules

Separate the following categories strictly:

1. **User-provided context**
   Facts, goals, constraints, domain statements, or directions explicitly provided by the user.

2. **Machine-observed facts**
   Facts directly visible in files, paths, configs, or repository structure.

3. **Model-inferred conclusions**
   Reasoned interpretations based on evidence. Every inference must include evidence, confidence, and whether human confirmation is required.

4. **Domain assumptions**
   Assumptions about the problem domain, business rules, operational constraints, protocols, risk model, or terminology. Domain assumptions must include evidence and confirmation status.

5. **Unknowns**
   Important questions that cannot be answered from available evidence.

6. **Recommendations**
   Candidate recommendations only. Do not treat them as authoritative truth.

## Required outputs

Produce or help produce:

- project-raw-scan.json;
- project-inventory.json;
- project-assessment.json or project-assessment.md;
- workflow-recommendations.yaml;
- gate-recommendations.yaml;
- open-questions.md;
- initialization-report.md.

## Safety and scope rules

Do not modify source files.
Do not create project-bound gates as final truth without human approval.
Do not assume project intent when evidence is weak.
Do not ignore documentation or Markdown implementation history.
Clearly mark stale, conflicting, or incomplete documentation.
Treat researcher/expert outputs as candidate assessments, not authoritative truth.

## Final summary

End with:

- what is well understood;
- what remains uncertain;
- what domain assumptions require confirmation;
- what the user should confirm;
- recommended next initialization step.
