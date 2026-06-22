# AgentsFlow

Version: v0.2 MVP readiness snapshot

> Workflow kit and reference methodology for controlled agent-assisted development.

AgentsFlow is a text-first, tool-light workflow kit. It makes agent-assisted development explicit, reviewable and reproducible through workflows, skills, scripts, templates, schemas, project overlays, gates, evidence reports, reviewer reports and fusion reports.

AgentsFlow is **not** an agent runtime, execution platform, UI, database, or replacement for coding harnesses such as Codex, Claude Code, Cursor, OpenCode, Cline or Roo.

## Core model

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

Primary abstraction: `Workflow`.

Reusable building blocks:

- `skills/` — agent-facing procedures;
- `scripts/` — deterministic checks and automation;
- `templates/` — artifact shapes;
- `schemas/` — machine-readable validation;
- `packs/` — domain/project rules;
- `profiles/` — strictness and review topology knobs.

Artifacts include task contracts, plans, behavior bindings, gate reports, evidence reports, reviewer reports, finding-validation reports and fusion reports.

## v0.2 MVP boundary

Application workflow:

```text
project-initialization
```

MVP supported target workflow:

```text
big-feature-contract-first
```

v0.2 utility workflows:

```text
review-only-fusion
pr-merge-readiness
```

Non-MVP workflows remain reference/experimental and schema-valid only:

```text
agentic-system-hardening
bugfix-regression-capture
new-project-spec-first
prompt-behavior-eval
safe-refactor
research-to-ADR
```

The supported v0.2 application path is:

```text
project-initialization.prepare-workflow -> big-feature-contract-first
```

Primary end-to-end example target:

```text
examples/e2e/minimal-python-project/
```

## Project application model

AgentsFlow is applied to a concrete project through three layers:

```text
AgentsFlow upstream      — pinned workflow kit / methodology
Project overlay/binding  — project-specific paths, gates, tools, policies
Workflow run             — task-specific contracts, plans, evidence and reports
```

Project initialization includes an agent-led human operating-decisions interview.
The agent asks about gate policy, reviewer count/model strategy, review-cycle
limits, authority boundaries and evidence storage, then records the normalized
`project-operating-decisions.yaml` artifact. The human is not asked to manually
fill a YAML/JSON file.

The v0.2 project overlay uses one canonical shape: flat `.agentsflow/project.yaml`,
structured `.agentsflow/workflows/*.binding.yaml`, and upstream pinning in
`.agentsflow/agentsflow.lock.yaml`.

Human interaction is workflow-scoped and main-agent mediated. The main agent may
pause at declared decision phases, record questions in `human-questions.yaml`,
record answers in `human-decisions.yaml`, and then resume. Review agents do not
ask humans questions directly.

First-stage dependency modes:

- Git submodule;
- CMake FetchContent / FetchPackage-style dependency.

CLI/package distribution is future work.

## Gate and behavior rules

- Upstream gates are gate contracts/templates, not project-executable gates.
- A real gate is executable only after project binding maps it to deterministic project-level runners, commands, tools and evidence sources.
- BDD/Gherkin scenarios are behavior specifications, not executable gates.
- Required acceptance scenarios must be bound to executable checks through `*.bindings.yaml`.
- A workflow phase of `kind: implementation` must be framed by a pre-implementation red-capture phase (contract scenarios turned into executable tests, run against the not-yet-implemented state, failing run captured) and a post-implementation green-verify phase (same tests re-run, passing run captured). `validate_repo.py` enforces the phase topology; run-artifact validation of the actual failing/passing evidence pair remains future work. See `docs/adr/ADR-0017-test-framed-implementation-phase.md`.

## Review rules

- Verification gates produce authoritative verification evidence.
- Review agents are read-only by default and run after the verification gate.
- Review-agent findings are candidate findings until the main/orchestrating agent validates relevance.
- Fusion is read-only synthesis, not majority voting.

## External reviewer provider

v0.2 includes a minimal Claude Code external reviewer provider:

- Claude Code CLI only;
- subscription-local only;
- API-key/proxy usage forbidden;
- wrapper must fail if the configured forbidden Claude API/proxy environment variables are present;
- Codex-launched Claude reviewer runs require escalated sandbox access for local
  subscription auth. Stdin packet transport disables Claude Code tools with
  `--tools ""`; file prompt transport may use only `--tools Read` for the
  generated prompt file in an isolated temporary directory;
- review packet in, normalized reviewer-report out;
- normalized report and invocation metadata stored as evidence, with raw output
  stored only when explicitly non-sensitive;
- findings remain candidate/unvalidated.

See:

- `docs/external-reviewer-provider-model.md`
- `docs/pr-merge-readiness.md`
- `docs/adr/ADR-0016-external-reviewer-provider-interface.md`
- `examples/external-reviewers/claude-code/`

## Quick validation

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python3 scripts/validate_repo.py --root .
python3 -m pytest -q
```

Example checks:

```bash
python3 scripts/contract_lint.py --contract examples/memory-policy/Docs/contracts/memory-policy.contract.md
python3 scripts/gherkin_lint.py --contract examples/memory-policy/Docs/contracts/memory-policy.contract.md
python3 scripts/bdd_binding_check.py --bindings examples/memory-policy/Docs/contracts/memory-policy.bindings.yaml
python3 scripts/evidence_validate.py --evidence examples/memory-policy/evidence-report.md
```

External reviewer wrapper smoke test without calling Claude:

```bash
python3 scripts/reviewers/run_external_reviewer.py \
  --provider claude-code \
  --config examples/external-reviewers/claude-code/claude-code.yaml \
  --input examples/external-reviewers/claude-code/review-packet.architecture.json \
  --mock-response examples/external-reviewers/claude-code/mock-raw-output.json \
  --output /tmp/reviewer-report.claude-architecture.json
```

## Suggested review path

Start here:

1. `docs/checkpoints/checkpoint-2026-06-20-documentation-legacy-adoption-confirmation.md`
2. `docs/checkpoints/checkpoint-2026-06-19-v0.2-supported-path.md`
3. `docs/checkpoints/checkpoint-2026-06-19-v0.2-expert-assessment-output-contract.md`
4. `docs/checkpoints/checkpoint-2026-06-18-v0.2.0-slice2.md`
5. `docs/retrospectives/documentation-consistency-review-2026-06-17-v0.1.13.md`
6. `docs/philosophy.md`
7. `docs/workflow-model.md`
8. `docs/mvp-ready-workflow-standard.md`
9. `docs/project-application-model.md`
10. `docs/project-initialization-model.md`
11. `docs/enforcement-boundary.md`
12. `docs/human-interaction-protocol.md`
13. `docs/gate-executability-model.md`
14. `docs/behavior-binding-model.md`
15. `docs/review-control-model.md`
16. `docs/review-prompt-contract.md`
17. `docs/external-reviewer-provider-model.md`

## Development rule for coding agents

Do not expand scope. Implement accepted decisions. Make AgentsFlow usable for the v0.2 MVP path.
