# AGENTS.md

These instructions apply to AI coding agents working in this repository.

## Language

Repository artifacts should be primarily in English for portability across coding agents and future users. Russian handoff prompts are allowed when the user asks for them, but repository docs should default to English.

## Prime directive

Do not expand scope. Implement accepted decisions. Make AgentsFlow usable for v0.2 MVP.

Do not treat workflows as monolithic prompts. Preserve the modular philosophy:

```text
skills + scripts + templates + packs + profiles → workflows
```

A workflow composes capabilities. It should not duplicate all instructions from the skills it invokes.

## Source of truth

Before changing workflow design, read:

1. latest checkpoint in `docs/checkpoints/`;
2. relevant ADRs in `docs/adr/`;
3. `docs/philosophy.md`;
4. `docs/workflow-model.md`;
5. `docs/mvp-ready-workflow-standard.md`;
6. this `AGENTS.md`.

Preserve accepted decisions unless the user explicitly approves changing them.

## v0.2 MVP scope

Application workflow:

```text
project-initialization
```

MVP user workflows:

```text
big-feature-contract-first
bugfix-regression-capture
review-only-fusion
new-project-spec-first
```

Non-MVP workflows remain reference/experimental and schema-valid only:

```text
agentic-system-hardening
prompt-behavior-eval
safe-refactor
research-to-ADR
```

Primary e2e example:

```text
examples/e2e/minimal-python-project/
```

CMake FetchContent / FetchPackage support is a documented pattern/skeleton only in v0.2.

## Required behavior

Before adding or changing a workflow:

1. Define intent and MVP status.
2. List invoked skills/scripts/templates/packs.
3. Specify supported strictness profiles and review topology.
4. Reference gate manifests rather than prose-only gate names.
5. Keep project-specific commands out of upstream workflow definitions.

Before adding a skill:

1. Create `skills/<name>/SKILL.md`.
2. Create `skills/<name>/skill.yaml`.
3. Define inputs, outputs, dependencies and compatible workflows.

Before adding a script:

1. Put deterministic logic in `scripts/<name>.py` or a scoped subdirectory.
2. Put its manifest in `scripts/contracts/<name>.yaml`.
3. Prefer JSON/text outputs that can be used as evidence.
4. Do not hide non-deterministic model judgment inside deterministic scripts.

## Gate and binding rules

- Do not treat BDD/Gherkin scenarios as executable gates by themselves.
- Required acceptance scenarios need `*.bindings.yaml` behavior bindings.
- Do not hard-code project-specific commands into upstream workflow definitions.
- A real workflow-run gate is executable only after it is bound to a deterministic project-level runner.
- Upstream gate manifests are gate contracts/templates plus generic validation helpers.

## Project application / initialization rules

When applying AgentsFlow to a concrete project:

- Treat `.agentsflow/upstream` as a pinned upstream dependency and do not edit it during normal workflows.
- First-stage dependency modes are Git submodule or CMake FetchContent / FetchPackage-style dependency.
- Create project-specific bindings and executable gates in the project overlay, not in upstream.
- Start project initialization with an explicit project intake / research assignment. Unknown-project discovery uses the standard exploratory assignment, not an empty prompt.
- Analyze code, docs, ADRs, agent instructions, process artifacts and Markdown implementation history when present.
- Separate raw observed facts from model-produced inventory and expert assessments.
- Mark inferred fields with provenance, confidence and human-confirmation needs.
- Explicitly identify project domain(s), separate domain assumptions from observed evidence, and ask whether the user has domain expertise that should constrain initialization decisions.
- Use `knowledge-extraction` as the default legacy adoption mode for existing projects unless evidence supports another mode.
- Do not rewrite `AGENTS.md` or activate a migration without human approval.

## Review and fusion rules

- Verification gates produce authoritative verification evidence.
- Review agents are read-only and run after verification gates by default.
- Review-agent findings are candidate findings, not authoritative truth.
- The main/orchestrating agent must validate finding relevance before findings affect workflow decisions.
- Fusion is read-only synthesis, not majority voting.

## External reviewer provider rules

- Claude Code external reviewer provider is in v0.2 MVP scope.
- External model reviewers must be invoked only through explicit project-bound wrappers.
- For Claude Code CLI external review, v0.2 permits subscription-local usage only.
- API-key based Claude usage is forbidden. Wrappers must fail if `ANTHROPIC_API_KEY` is present.
- External reviewer outputs are candidate findings, not authoritative truth.
- External reviewers do not replace verification gates and do not modify files or run tests by default.
- Store review packets, raw provider output, normalized reviewer report and invocation metadata as run evidence.

## Evidence discipline

When completing a task, provide an acceptance proof:

- changed files;
- relevant contract(s);
- tests/scripts run;
- scenario coverage;
- boundary check result;
- known limitations;
- unresolved design questions.

## Non-goals for v0.2

Do not introduce:

- full CLI/package distribution;
- generic multi-provider reviewer runtime;
- API-key Claude usage;
- implementation agents as first-class actors;
- full haft/quint-code integration;
- formal TLA+/Quint baseline;
- UI, database, cloud service or agent runtime.
