# AgentsFlow

Version: v0.1.13 checkpoint

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

First-stage dependency modes:

- Git submodule;
- CMake FetchContent / FetchPackage-style dependency.

CLI/package distribution is future work.

## Gate and behavior rules

- Upstream gates are gate contracts/templates, not project-executable gates.
- A real gate is executable only after project binding maps it to deterministic project-level runners, commands, tools and evidence sources.
- BDD/Gherkin scenarios are behavior specifications, not executable gates.
- Required acceptance scenarios must be bound to executable checks through `*.bindings.yaml`.

## Review rules

- Verification gates produce authoritative verification evidence.
- Review agents are read-only by default and run after the verification gate.
- Review-agent findings are candidate findings until the main/orchestrating agent validates relevance.
- Fusion is read-only synthesis, not majority voting.

## External reviewer provider

v0.2 includes a minimal Claude Code external reviewer provider:

- Claude Code CLI only;
- subscription-local only;
- API-key usage forbidden;
- wrapper must fail if `ANTHROPIC_API_KEY` is present;
- review packet in, normalized reviewer-report out;
- raw output and invocation metadata stored as evidence;
- findings remain candidate/unvalidated.

See:

- `docs/external-reviewer-provider-model.md`
- `docs/adr/ADR-0016-external-reviewer-provider-interface.md`
- `examples/external-reviewers/claude-code/`

## Quick validation

```bash
python scripts/validate_repo.py --root .
pytest -q
```

Example checks:

```bash
python scripts/contract_lint.py --contract examples/memory-policy/Docs/contracts/memory-policy.contract.md
python scripts/gherkin_lint.py --contract examples/memory-policy/Docs/contracts/memory-policy.contract.md
python scripts/bdd_binding_check.py --bindings examples/memory-policy/Docs/contracts/memory-policy.bindings.yaml
python scripts/evidence_validate.py --evidence examples/memory-policy/evidence-report.md
```

External reviewer wrapper smoke test without calling Claude:

```bash
python scripts/reviewers/run_external_reviewer.py \
  --provider claude-code \
  --config examples/external-reviewers/claude-code/claude-code.yaml \
  --input examples/external-reviewers/claude-code/review-packet.architecture.json \
  --mock-response examples/external-reviewers/claude-code/mock-raw-output.json \
  --output /tmp/reviewer-report.claude-architecture.json
```

## Suggested review path

Start here:

1. `docs/checkpoints/checkpoint-2026-06-17-v0.1.13.md`
2. `docs/retrospectives/documentation-consistency-review-2026-06-17-v0.1.13.md`
3. `docs/philosophy.md`
4. `docs/workflow-model.md`
5. `docs/mvp-ready-workflow-standard.md`
6. `docs/project-application-model.md`
7. `docs/project-initialization-model.md`
8. `docs/gate-executability-model.md`
9. `docs/behavior-binding-model.md`
10. `docs/review-control-model.md`
11. `docs/external-reviewer-provider-model.md`

## Development rule for coding agents

Do not expand scope. Implement accepted decisions. Make AgentsFlow usable for the v0.2 MVP path.
