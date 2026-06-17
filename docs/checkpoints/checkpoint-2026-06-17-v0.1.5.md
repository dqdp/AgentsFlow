# AgentsFlow Checkpoint — v0.1.5

Date: 2026-06-17
Status: design checkpoint after review-agent interaction protocol formalization

## Accepted decisions

### 1. Project identity

Project name: **AgentsFlow**.

AgentsFlow is a **workflow kit and reference methodology** for controlled agent-assisted development. It is not an agent runtime, execution platform, or replacement for coding harnesses such as Codex, Claude Code, Cursor, OpenCode, Cline, or Roo.

### 2. Core model

Workflow is the primary user-facing abstraction.

A workflow is a compositional recipe that orchestrates reusable skills, scripts, templates, schemas, packs, profiles, and artifacts.

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

Skills encode agent-facing procedures and reasoning patterns. Scripts encode deterministic checks and automation. Contracts, evidence reports, gate reports, reviewer reports, fusion reports, ADR drafts, BDD scenarios, research briefs, plans, task breakdowns, decision contracts, finding-validation reports, and review-cycle reports are artifacts created and consumed by workflows.

### 3. Workflow taxonomy

Core workflows:

- `new-project-spec-first`
- `big-feature-contract-first`
- `bugfix-regression-capture`
- `safe-refactor`

Agent-specific workflows:

- `agentic-system-hardening`
- `prompt-behavior-eval`

Auxiliary / utility workflows:

- `research-to-ADR`
- `review-only-fusion`

`review-only-fusion` is a review utility workflow: it reviews an existing artifact/evidence bundle and produces independent reviewer reports plus a fusion report. It does not implement and does not run tests.

### 4. Review control model

Review gates and review agents are composable control primitives, not a fixed methodology baked into the core.

Core defines common interfaces for gate, reviewer, review topology, fusion, blocking issue, severity, and evidence. Each workflow decides how many reviewers it needs, which reviewer roles to use, which gates are mandatory or optional, whether fusion is required, and which exit policy applies.

Accepted baseline: **Core defines contracts. Workflow defines composition.**

### 5. Review-agent rule 1: post-verification and read-only

Review agents run only after a verification gate. The verification gate is responsible for running tests, scripts, deterministic checks, impact-map checks, boundary checks, and evidence validation.

Review agents consume the gate report and evidence bundle. They must not run tests, run verification scripts, modify files, generate patches, or update evidence. They may request additional verification only as a candidate finding.

### 6. Review-agent rule 2: findings require relevance validation

Review-agent findings are candidate findings, not authoritative truth.

A finding becomes an accepted issue only after the main/orchestrating agent validates its relevance against the task contract, artifact/diff, verification gate report, evidence bundle, accepted ADRs, workflow profile, scope, and non-goals.

P0/P1 candidate findings must not be silently discarded. If the main/orchestrating agent rejects, downgrades, or marks such a finding as irrelevant, it must record an evidence-based reason.

### 7. Review-agent interaction protocol

AgentsFlow now defines a concrete review-agent interaction protocol.

The protocol distinguishes:

- candidate blocking findings;
- validated blocking findings;
- missing mandatory evidence;
- non-blocking follow-ups;
- human-decision-required findings.

Default blocking semantics:

- P0 and P1 findings are candidate blockers by default;
- missing mandatory evidence is blocking by default;
- majority/fusion cannot erase a candidate blocker;
- candidate blockers must be validated by the main/orchestrating agent.

Default review-loop exit criterion:

```text
Exit when there are no validated blocking findings and no mandatory evidence gaps.
```

Repeated review agents are not rerun when only non-blocking P2/P3/NOTE findings remain, duplicate findings are consolidated, or irrelevant findings are rejected with evidence-based reasons.

### 8. BDD / contract model

BDD/Gherkin is accepted as a human-readable behavior-spec layer over tests, evals, trace assertions, gates, and review. Task contracts are artifact types, not top-level modules.

### 9. Specification / Plan Mode

Specification / Plan Mode is accepted as a reusable phase pattern, not a new top-level abstraction and not one global workflow. It is composed from existing primitives: skills, scripts, templates, artifacts, gates, profiles, and workflow phases.

Planning agents are read-only. Implementation requires an approved plan gate when the selected workflow/profile requires it.

### 10. Quint Code / haft

AgentsFlow will not reimplement haft/quint code in the core. It will borrow selected ideas conceptually:

- frame / explore / compare / decide / verify;
- decision contracts;
- term maps;
- target system / enabling system split;
- evidence freshness / staleness markers.

haft/quint code may be supported as an optional external advanced planning / decision-engineering provider through an integration boundary.

## New in v0.1.5

- `docs/review-agent-interaction-protocol.md`
- `docs/adr/ADR-0008-review-agent-interaction-protocol.md`
- `schemas/review-cycle.schema.json`
- `templates/review-cycle-report.md`
- expanded `templates/finding-validation-report.md`
- workflow-level `review_cycle` policies
- updated `AGENTS.md` review-agent protocol guidance

## Open questions

1. Define `docs/actor-model.md` for human, orchestrator, planning agent, implementation agent, verification gate, review agent, and fusion agent.
2. Formalize workflow `phase` schema without introducing a new top-level abstraction.
3. Decide MVP cut for v0.2: likely `new-project-spec-first`, `big-feature-contract-first`, and `prompt-behavior-eval`.
4. Add stronger repository validation around workflow phases, review-cycle policies, and template references.
5. Define BDD scenario binding: how each scenario maps to tests, evals, trace assertions, or reviewer checks.
6. Define model-diversity policy for optional multi-model fusion.
7. Specify the haft integration boundary and artifact mapping in more detail.
8. Decide whether to add `plan-review-before-implementation` as an auxiliary workflow later.

## Next review focus

Recommended next design-review topic: **Actor model and workflow phase schema**.
