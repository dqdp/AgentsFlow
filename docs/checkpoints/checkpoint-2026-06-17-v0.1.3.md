# AgentsFlow Checkpoint — v0.1.3

Date: 2026-06-17
Status: design checkpoint after the first review pass

## Accepted decisions

### 1. Project identity

Project name: **AgentsFlow**.

AgentsFlow is a **workflow kit and reference methodology** for controlled agent-assisted development.
It is not an agent runtime, not an execution platform, and not a replacement for coding harnesses such as Codex, Claude Code, Cursor, OpenCode, Cline, or Roo.

### 2. Core model

Workflow is the primary user-facing abstraction.

A workflow is a compositional recipe that orchestrates reusable skills, scripts, templates, schemas, packs, profiles, and artifacts.

Core formula:

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

Skills and scripts are the primary reusable building blocks:

- skills encode agent-facing procedures and reasoning patterns;
- scripts encode deterministic checks and automation.

Contracts, evidence reports, gate reports, reviewer reports, fusion reports, ADR drafts, BDD scenarios, research briefs, plans, task breakdowns, and decision contracts are artifacts created and consumed by workflows.

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

Core defines common interfaces for:

- gate;
- reviewer;
- review topology;
- fusion;
- blocking issue;
- severity;
- evidence.

Each workflow decides:

- how many reviewers it needs;
- which reviewer roles to use;
- which gates are mandatory or optional;
- whether fusion is required;
- what counts as pass/fail/needs-human-decision.

Accepted principle:

```text
Core defines contracts.
Workflow defines composition.
```

### 5. Verification gate before review agents

Review agents are read-only evaluators and must run only after a verification gate when implementation artifacts are being reviewed.

The verification gate is responsible for executing tests, scripts, deterministic checks, impact-map checks, boundary checks, evidence validation, and other verification commands.

Review agents consume the gate report and evidence bundle. They must not run tests, call scripts, modify files, or generate patches. They may request additional verification only as a finding.

Future implementation agents may have different rules, but they are a separate actor class.

### 6. BDD / contract layer

BDD/Gherkin is a human-readable behavior-specification layer over tests, checks, evals, trace assertions, and review gates.

BDD does not replace unit/integration/architecture tests. It provides a higher-level behavioral contract, especially for:

- forbidden behavior;
- agent process constraints;
- memory/tool/policy/context behavior;
- regression scenarios;
- acceptance criteria.

Task contracts are artifacts, not top-level modules.

### 7. Specification / Plan Mode

Specification / Plan Mode is accepted as a reusable workflow phase pattern, not as a new top-level abstraction and not as one global workflow.

It is composed from existing primitives:

- skills;
- scripts;
- templates;
- artifacts;
- gates;
- profiles;
- workflow phases.

Planning agents are read-only. Implementation begins only after a required plan gate passes when the workflow/strictness profile requires it.

Baseline thesis:

```text
Plan mode is a reusable phase pattern implemented through skills/scripts/templates,
not one global workflow.
```

A future utility workflow `plan-review-before-implementation` remains a possible later addition, but it is not part of the core v0.2 direction.

### 8. Quint Code / haft influence

AgentsFlow should not reimplement haft/quint code.

AgentsFlow should:

1. borrow selected conceptual patterns from haft;
2. keep its own core lightweight;
3. support haft/quint code as an optional external advanced planning / decision-engineering provider;
4. define an adapter boundary rather than merging the models.

Ideas to borrow into AgentsFlow methodology:

- frame / explore / compare / decide / verify;
- decision contracts;
- term maps;
- target system / enabling system split;
- evidence freshness / staleness markers.

Do not import into AgentsFlow core v0.2:

- MCP runtime dependency;
- `.haft` graph as native storage;
- full decision-governance engine;
- evidence decay metrics;
- stale/drift enforcement as baseline;
- WorkCommission runtime model.

haft/quint code may be supported as an optional external provider for advanced planning and decision engineering.

## Open questions

### A. MVP cut for v0.2

Candidate v0.2 focus:

- `new-project-spec-first`
- `big-feature-contract-first`
- `prompt-behavior-eval`

Open decision: do we also bring `bugfix-regression-capture` into v0.2 because it is small and practically useful?

### B. Actor model

We need an explicit actor model document covering:

- human;
- workflow orchestrator;
- planning agent;
- implementation agent;
- verification gate;
- review agent;
- fusion agent.

Especially important: planning agents and review agents are both read-only but have different roles and timing.

### C. Workflow phase schema

We need to decide how formal `phases:` should become in `workflow.yaml`.

Current direction: phase is a structural element inside workflow, not a top-level abstraction.

### D. Native Spec/Plan templates and skills

Need to decide exact minimal template/skill set for v0.2.

Likely native templates:

- `problem-frame.md`
- `repository-grounding-report.md`
- `plan.md`
- `task-breakdown.md`
- `decision-contract.md`
- `plan-gate-report.md`
- `term-map.md`
- `target-system-spec.md`
- `enabling-system-spec.md`

Likely native skills:

- `problem-framing`
- `repository-grounding`
- `technical-planning`
- `plan-validation`
- `decision-contracting`

### E. haft integration boundary

Need to decide whether the integration lives under:

- `integrations/haft/`; or
- `packs/haft-advanced-planning/`.

Current v0.1.3 uses `integrations/haft/` as the clearer boundary.

### F. Validation and repository integrity

Need to grow `scripts/validate_repo.py` into a serious repository validator that checks:

- all YAML/JSON files parse;
- workflow references exist;
- skills/scripts/templates/packs/profiles exist;
- review topology names are valid;
- schema validation passes where schemas exist;
- examples are runnable.

### G. Formal specifications

Quint/TLA+-style formal specifications remain optional and should be represented as a future `formal-specification` pack, not as baseline AgentsFlow behavior.

## Next design-review order

1. MVP cut for v0.2.
2. Actor model.
3. Workflow phase schema.
4. Native Spec/Plan minimal set.
5. haft integration boundary.
6. Repo validation hardening.
7. BDD scenario binding to tests/evals/checks.
8. Multi-model fusion policy details.
