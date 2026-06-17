# Actor Model

## Purpose

AgentsFlow defines actor roles as workflow protocol roles. An actor is not a new
top-level building block like workflow, skill, script, pack, or profile. Actor
roles clarify who may read, write, run tools, produce evidence, review, synthesize,
or request human decisions inside a workflow.

## Current active roles

### Human

The human owns intent and accepted changes to intent. The human may approve scope
changes, accepted-decision changes, ADR changes, high-risk overrides, and final
decisions when the workflow returns `human-decision-required`.

### Main / Orchestrating Agent

The main/orchestrating agent coordinates the workflow. It reads `workflow.yaml`,
selects profiles/topology, invokes skills, requests or coordinates verification
gates, collects artifacts, launches reviewers according to the selected workflow,
validates reviewer findings for relevance, invokes fusion when required, and
prepares the final decision report.

It must not silently change accepted ADRs, project scope, or human-approved intent.
It must not forward unvalidated reviewer findings as mandatory implementation work.

### Verification Gate

A verification gate is a workflow-defined evidence-producing control point. It is
not limited to unit tests or simple scripts. A gate may run any verification
instruments explicitly allowed by the workflow/profile.

Examples of verification instruments:

- unit, integration, end-to-end, scenario, BDD, and regression tests;
- contract, boundary, impact-map, evidence, and schema checks;
- static analysis and linters;
- dynamic analysis, sanitizers, race detectors, profilers, and fuzzers;
- debuggers and trace analyzers;
- log and telemetry analysis;
- network traffic capture/analysis tools;
- security scanners;
- performance and latency benchmarks;
- domain-specific tools;
- manual evidence checks recorded in a gate report.

The gate produces evidence. It does not perform taste-based review.

### Review Agent

Review agents are read-only by default and run after the relevant evidence exists.
They evaluate contracts, diffs/artifacts, gate reports, logs, and evidence bundles.
They produce candidate findings, not authoritative truth.

A review agent may receive explicit tool permissions only if the workflow,
reviewer manifest, or reviewer prompt grants them. Such permissions must be
scoped, documented, and exceptional. Tool-enabled review still does not replace a
verification gate: observations produced by reviewer tools are candidate findings
until validated by the main/orchestrating agent.

### Fusion Agent

Fusion Agent is a read-only synthesis role. It consumes reviewer reports,
validated finding reports, workflow context, and gate evidence. It produces a
fusion report with consensus, disagreement, candidate/validated blockers, and
human-decision items.

By default, Fusion Agent does **not** launch reviewers, run gates, run tests, or
modify artifacts. It may recommend additional review or verification, but the
main/orchestrating agent remains responsible for orchestration.

### Script / Tool Runner

A script/tool runner executes deterministic commands or approved verification
instruments and returns structured outputs. It does not make architectural or
acceptance decisions.

### External Planning Provider

An external planning provider, such as haft/quint code, may perform advanced
planning or decision engineering. Its outputs must be normalized back into
AgentsFlow artifacts such as research briefs, decision contracts, plans, task
breakdowns, evidence summaries, and ADR drafts. It is not a second source of
truth.

## Reserved / future roles

### Planning Agent

Planning Agent is a reserved optional future role, similar to Implementation Agent.
Current AgentsFlow workflows treat planning primarily as a human-guided phase
coordinated by the main/orchestrating agent.

A future Planning Agent may assist with delegated planning, research, option
comparison, or integration with external planning providers, but it is not the
current default.

### Implementation Agent

Implementation Agent is also a reserved future role. It may eventually receive
permission to modify files, run tools, and iterate on implementation within an
approved contract/plan. Those permissions are explicitly not inherited by review
agents.

## Permission matrix

| Actor | Read repo/docs | Write spec/plan docs | Modify source | Run verification instruments | Produce candidate findings | Synthesize reports | Final authority |
|---|---:|---:|---:|---:|---:|---:|---:|
| Human | yes | yes | yes | optional | yes | yes | yes |
| Main/orchestrating agent | yes | yes | controlled | through gate/tool runner | validates | prepares | no, unless human delegated |
| Planning agent | yes | yes | no | no by default | no | no | no |
| Implementation agent | yes | yes | yes, future/explicit | future/explicit | no | no | no |
| Verification gate | yes | gate report only | no | yes | no | no | gate result only |
| Review agent | yes | reviewer report only | no | no by default | yes | no | no |
| Fusion agent | yes | fusion report only | no | no | no | yes | no |
| Script/tool runner | limited | machine output | no | yes | no | no | no |
| External planning provider | depends | external artifacts | no by default | no by default | maybe | maybe | no |

## Core invariants

```text
Planning is currently human-guided, not delegated-agent default.
Planning Agent and Implementation Agent are reserved roles.
Verification Gate owns evidence production.
Review agents are read-only by default.
Review-agent tool use is explicit, scoped, and exceptional.
Review-agent findings remain candidate findings until validated.
Fusion Agent synthesizes; it does not orchestrate by default.
Human remains final authority for scope, accepted-decision changes, and overrides.
```
