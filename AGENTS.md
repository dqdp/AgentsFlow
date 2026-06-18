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

For a broader orientation path, use README.md's "Suggested review path" plus the
primary e2e example at `examples/e2e/minimal-python-project/`.

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
6. If the workflow has an implementation phase, frame it with a preceding red-capture (failing-test) phase and a following green-verify phase (ADR-0017).

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
- An implementation phase must be framed by a red-capture phase (tests run against the not-yet-implemented state, failing run captured) and a green-verify phase (same tests re-run, passing run captured). `validate_repo.py` rejects workflow definitions whose implementation phase is missing this structural framing. Full run-artifact proof of the actual red and green executions is still workflow evidence, not a schema-only fact. See `docs/adr/ADR-0017-test-framed-implementation-phase.md`.
- Refactor-only implementation may use a pre-change `baseline_capture` before `change_type: refactor`; this is not a substitute for red-capture when new behavior is implemented.

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
- Before drafting the project overlay, conduct an agent-led human operating-decisions interview for gate policy, review topology, reviewer/model strategy, maximum review cycles, authority boundaries and evidence storage. Do not ask the human to manually fill a YAML/JSON file; the agent records the normalized `project-operating-decisions.yaml` artifact after the dialogue.
- Human interaction is main-agent mediated. Review agents must not ask the human questions directly; they produce candidate findings, recommendations and questions for the main agent to synthesize. A workflow may pause for humans only at declared human-interaction phases or true blocking clarifications.
- Use `knowledge-extraction` as the default legacy adoption mode for existing projects unless evidence supports another mode.
- Do not rewrite `AGENTS.md` or activate a migration without human approval.

## Review and fusion rules

- Verification gates produce authoritative verification evidence.
- Review agents are read-only and run after verification gates by default.
- Default review is `homogeneous-dual`: two independent generalist reviewers
  receive the same prompt, same review packet, same rubric and same output schema.
- Primary review gates require at least two reviewers. Collision-control also uses
  two fresh-context control reviewers: rejected or downgraded blocker-level
  candidate findings from the same review cycle are recorded as one collision
  batch and sent to those two control reviewers.
- Heterogeneous review is explicit, not inferred. Reviewer role ids such as
  `adversarial`, `architecture` or `verification` must resolve to role definitions
  in `profiles/reviewer_roles/`; focus zones may overlap and do not prevent any
  reviewer from reporting a plausible P0/P1 blocker outside its focus.
- Review agents start from zero conversation context and must not be launched by
  forking the main/orchestrating agent context. They receive only the review
  packet and referenced artifacts declared by the workflow or project binding.
- Review-agent findings are candidate findings, not authoritative truth.
- The main/orchestrating agent must validate finding relevance before findings affect workflow decisions.
- Fusion is read-only synthesis, not majority voting.

## External reviewer provider rules

- Claude Code external reviewer provider is in v0.2 MVP scope.
- External model reviewers must be invoked only through explicit project-bound wrappers.
- For Claude Code CLI external review, v0.2 permits subscription-local usage only.
- API-key based Claude usage is forbidden. Wrappers must fail if any configured
  forbidden Claude API/proxy environment variable is present.
- Claude API/proxy environment routes are also forbidden by the provider baseline:
  `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `CLAUDE_CODE_USE_BEDROCK` and
  `CLAUDE_CODE_USE_VERTEX`.
- External reviewer outputs are candidate findings, not authoritative truth.
- External reviewers do not replace verification gates and do not modify files or run tests by default.
- Store review packets, raw provider output, normalized reviewer report and invocation metadata as run evidence.

## Validation

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python3 scripts/validate_repo.py --root .
python3 -m pytest -q

# external reviewer wrapper smoke test (no live Claude call):
python3 scripts/reviewers/run_external_reviewer.py \
  --provider claude-code \
  --config examples/external-reviewers/claude-code/claude-code.yaml \
  --input examples/external-reviewers/claude-code/review-packet.architecture.json \
  --mock-response examples/external-reviewers/claude-code/mock-raw-output.json \
  --output /tmp/reviewer-report.claude-architecture.json
```

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
