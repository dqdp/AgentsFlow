# Bird-eye Pass / Retrospective: AgentsFlow v0.1.10

## Purpose

This retrospective reviews AgentsFlow from above: what the project has become, where the architecture is strong, where complexity is accumulating, and what should happen before v0.2.

## Current identity

AgentsFlow is a **workflow kit and reference methodology** for controlled agent-assisted development.

It is not:

```text
- an agent runtime;
- a replacement for Codex / Claude Code / Cursor / OpenCode / Cline / Roo;
- a full execution platform;
- a clone of haft / Quint Code;
- a generic QA framework.
```

Its core value is making agentic development workflows explicit, reviewable, reproducible and evidence-driven.

## Core architecture

```text
AgentsFlow upstream
  Universal workflow definitions, skills, scripts, templates, schemas, gate contracts and methodology docs.

Project overlay / binding
  Project-specific paths, commands, gate runners, tools, evidence sources, review policies and domain rules.

Workflow run
  Task-specific contract, plan, behavior bindings, gate reports, evidence, reviewer reports, finding validation, fusion and final decision.
```

This three-layer model is the main protection against turning the project into a mess.

## Accepted control principles

```text
Workflows compose.
Skills guide.
Scripts verify.
Templates structure.
Schemas validate.
Packs specialize.
Profiles tune.
Artifacts carry evidence.
```

Additional accepted invariants:

```text
Planning is not implementation.
Verification is not review.
Review findings are not truth.
Fusion is not majority voting.
Workflow defines composition.
Core defines contracts.
Project overlay defines execution.
```

## Strong decisions

### 1. Workflow as primary abstraction

This keeps the user-facing model clear. People do not ask for a skill; they ask to start a project, implement a big feature, fix a bug, review a design, or harden an agentic system.

### 2. Project binding model

This prevents upstream methodology from being polluted by project-specific commands and prevents project overlays from silently redefining methodology.

### 3. Gate executability rule

A gate is only real when it has a deterministic runner entrypoint at project-binding level. BDD/prose/contracts define what should be checked; bound runners execute checks and produce evidence.

### 4. Behavior binding rule

Required BDD/Gherkin scenarios must map to executable checks. This prevents behavior specs from becoming decorative documentation.

### 5. Review-agent protocol

Review agents are read-only by default, run after verification, produce candidate findings, and require main-agent relevance validation.

### 6. Lightweight Spec/Plan model with optional haft

AgentsFlow borrows ideas from Quint Code / haft without absorbing its full runtime. Advanced decision engineering remains optional.

### 7. Project initialization starts with research assignment

Unknown project discovery is standard exploratory analysis, not an empty prompt. Domain identification and user domain expertise are explicit.

## Complexity risks

### Risk 1: Too many concepts too early

AgentsFlow now includes workflows, skills, scripts, templates, schemas, packs, profiles, artifacts, gates, bindings, overlays, runs, actors and external providers.

Mitigation:

```text
Do not add new top-level abstractions lightly.
Prefer phase patterns, artifact types and templates over new model entities.
Keep v0.2 focused on four MVP workflows.
```

### Risk 2: Markdown sprawl

The project can become a forest of documents with weak execution.

Mitigation:

```text
Every MVP-ready workflow needs validation coverage.
Every concrete gate needs project-bound runner.
Required behavior scenarios need bindings.
Repo validation should keep growing.
```

### Risk 3: AgentsFlow vs project overlay confusion

If upstream, overlay and workflow-run artifacts are mixed, the system becomes unmaintainable.

Mitigation:

```text
Upstream is pinned and read-only during normal workflows.
Project-specific execution lives in .agentsflow/ overlay.
Task artifacts live in Docs/agentsflow/runs/<run-id>/.
```

### Risk 4: Review agents treated as authority

Review findings can be wrong, irrelevant, duplicated or out of scope.

Mitigation:

```text
Main/orchestrating agent validates relevance using the decision matrix.
Only validated blocking findings drive the review loop.
```

### Risk 5: Domain misunderstanding during initialization

Agents may parse the repository correctly but misunderstand the domain.

Mitigation:

```text
Domain identification is explicit.
Domain assumptions are separated from observed evidence.
User domain expertise is queried.
Domain packs are selected or created only after confirmation.
```

## MVP focus for v0.2

MVP workflows:

```text
big-feature-contract-first
bugfix-regression-capture
review-only-fusion
new-project-spec-first
```

Support workflow:

```text
project-initialization
```

Non-MVP/reference for now:

```text
agentic-system-hardening
prompt-behavior-eval
safe-refactor
research-to-ADR
```

## Recommended next step

Move from design expansion to consolidation:

```text
1. Turn v0.2 MVP-ready standard into a concrete checklist.
2. Harden project-initialization example.
3. Add a first real-project onboarding run.
4. Keep adding validators only where they enforce accepted decisions.
5. Avoid introducing new top-level abstractions before v0.2.
```

## Bird-eye verdict

AgentsFlow is now coherent: it has a stable philosophy, a layered application model, a review/verification protocol, a spec/plan strategy, and a project onboarding path.

The main remaining danger is over-expansion. v0.2 should focus on making the accepted model usable on a real project rather than adding more methodology surface area.
