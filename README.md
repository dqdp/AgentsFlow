# AgentsFlow

<div align="center">

<strong>Modular workflow kit for controlled agent-assisted development.</strong>

<br>

<a href="docs/mvp-ready-workflow-standard.md"><img alt="version v0.2.0" src="https://img.shields.io/badge/version-v0.2.0-blue"></a>
<a href="docs/mvp-ready-workflow-standard.md"><img alt="MVP ready" src="https://img.shields.io/badge/status-MVP_ready-2ea44f"></a>
<a href="docs/enforcement-boundary.md"><img alt="repo validation passing" src="https://img.shields.io/badge/repo_validation-passing-2ea44f"></a>
<a href="LICENSE"><img alt="license MIT" src="https://img.shields.io/badge/license-MIT-yellow"></a>

<br>

<a href="docs/workflow-model.md"><img alt="workflow model" src="https://img.shields.io/badge/workflows-compose-0ea5e9"></a>
<a href="skills/"><img alt="skills" src="https://img.shields.io/badge/skills-guide-8b5cf6"></a>
<a href="scripts/"><img alt="scripts" src="https://img.shields.io/badge/scripts-verify-16a34a"></a>
<a href="templates/"><img alt="templates" src="https://img.shields.io/badge/templates-structure-f59e0b"></a>
<a href="schemas/"><img alt="schemas" src="https://img.shields.io/badge/schemas-validate-ef4444"></a>

<br>

<a href="docs/external-reviewer-provider-model.md"><img alt="Codex supported" src="https://img.shields.io/badge/Codex-supported-7c3aed"></a>
<a href="docs/external-reviewer-provider-model.md"><img alt="Claude Code supported" src="https://img.shields.io/badge/Claude_Code-supported-7c3aed"></a>
<a href="docs/external-reviewer-provider-model.md"><img alt="Claude API keys forbidden" src="https://img.shields.io/badge/Claude_API_keys-forbidden-critical"></a>

<br><br>

<a href="#quick-start">Quick start</a> |
<a href="#v02-supported-path">v0.2 path</a> |
<a href="#documentation-map">Documentation map</a> |
<a href="#external-reviewers">External reviewers</a> |
<a href="#pr-merge-readiness">PR readiness</a>

</div>

---

AgentsFlow is a text-first, tool-light methodology and artifact kit. It helps a
human and a main coding agent make work explicit, reviewable and reproducible
through contracts, plans, project overlays, gates, evidence, reviewer reports,
finding validation and fusion.

AgentsFlow is **not** an agent runtime, execution platform, UI, database,
package manager, CI system or replacement for coding harnesses such as Codex,
Claude Code, Cursor, OpenCode, Cline or Roo.

## Core Idea

```text
skills + scripts + templates + packs + profiles -> workflows
```

| Layer | Role | Where |
|---|---|---|
| Workflows | Compose the process for a class of work. | [workflows/](workflows/) |
| Skills | Guide agent behavior and task-specific procedures. | [skills/](skills/) |
| Scripts | Run deterministic checks and artifact preparation. | [scripts/](scripts/) |
| Templates | Give artifacts a consistent shape. | [templates/](templates/) |
| Schemas | Validate machine-readable artifacts. | [schemas/](schemas/) |
| Profiles | Tune review topology, reviewer roles and strictness. | [profiles/](profiles/) |
| Packs | Carry domain or project rules. | [packs/](packs/) |

## v0.2 Supported Path

v0.2 intentionally supports a narrow, usable path:

```text
project-initialization.prepare-workflow -> big-feature-contract-first
```

| Workflow | v0.2 status | Use it for |
|---|---|---|
| [project-initialization](workflows/project-initialization/workflow.yaml) | application workflow | Onboard or analyze a project, capture operating decisions, and prepare a target workflow. |
| [big-feature-contract-first](workflows/big-feature-contract-first/workflow.yaml) | supported target workflow | Implement a substantial feature through contract, design acceptance, red capture, implementation, green verification and review. |
| [review-only-fusion](workflows/review-only-fusion/workflow.yaml) | utility workflow | Review an existing artifact or evidence bundle without implementation. |
| [pr-merge-readiness](workflows/pr-merge-readiness/workflow.yaml) | utility workflow | Decide whether a branch is ready to open, accept or merge as a PR. |

Reference and experimental workflows remain schema-valid but are not supported
`prepare-workflow` targets in v0.2:

```text
agentic-system-hardening
bugfix-regression-capture
new-project-spec-first
prompt-behavior-eval
safe-refactor
research-to-ADR
```

The primary end-to-end example is
[examples/e2e/minimal-python-project](examples/e2e/minimal-python-project/).

## What AgentsFlow Enforces

AgentsFlow separates strong claims from protocol guidance.

| Claim type | Meaning | Start here |
|---|---|---|
| Script-enforced | A validator, test or deterministic checker fails on violation. | [Enforcement boundary](docs/enforcement-boundary.md) |
| Schema-validated | Artifact shape is checked, but semantic quality is not proven. | [Schemas](schemas/) |
| Agent protocol | Agents must follow the rule, but it is not fully machine-checked. | [AGENTS.md](AGENTS.md) |
| Human decision | The run must stop or record an explicit human answer. | [Human interaction protocol](docs/human-interaction-protocol.md) |

Do not infer that a rule is script-enforced just because it appears in a
workflow, ADR, template or skill.

## Project Application Model

AgentsFlow is applied to a concrete project through three layers:

```text
AgentsFlow upstream      -> pinned methodology source
Project overlay/binding  -> project-specific gates, paths, tools and policy
Workflow run             -> task-specific contracts, plans, evidence and reports
```

The canonical project overlay shape is:

```text
.agentsflow/
  project.yaml
  agentsflow.lock.yaml
  workflows/<workflow>.binding.yaml
  gates/<project-gate>.yaml
  scripts/<project-runner>
```

Ordinary target projects typically store workflow run artifacts under:

```text
Docs/agentsflow/runs/<run-id>/
```

AgentsFlow self-application uses:

```text
run-artifacts/agentsflow/runs/<run-id>/
```

That avoids a case-insensitive filesystem collision between repository
methodology source in [docs/](docs/) and project-style `Docs/` run history.

## Documentation Map

| Need | Open |
|---|---|
| Understand the project philosophy | [docs/philosophy.md](docs/philosophy.md) |
| Understand workflow structure and current workflow statuses | [docs/workflow-model.md](docs/workflow-model.md) |
| Check the v0.2 readiness definition | [docs/mvp-ready-workflow-standard.md](docs/mvp-ready-workflow-standard.md) |
| Know what is enforced versus policy-only | [docs/enforcement-boundary.md](docs/enforcement-boundary.md) |
| Apply AgentsFlow to a project | [docs/project-application-model.md](docs/project-application-model.md) |
| Bind workflows to project gates and paths | [docs/project-binding-model.md](docs/project-binding-model.md) |
| Run project initialization | [docs/project-initialization-model.md](docs/project-initialization-model.md) |
| Model gates and behavior bindings | [docs/gate-executability-model.md](docs/gate-executability-model.md), [docs/behavior-binding-model.md](docs/behavior-binding-model.md) |
| Run review, fusion and finding validation | [docs/review-control-model.md](docs/review-control-model.md), [docs/review-fusion-model.md](docs/review-fusion-model.md) |
| Prepare review packets and prompts | [docs/review-prompt-contract.md](docs/review-prompt-contract.md), [docs/review-artifact-preparation.md](docs/review-artifact-preparation.md) |
| Use Claude Code as an external reviewer | [docs/external-reviewer-provider-model.md](docs/external-reviewer-provider-model.md) |
| Decide PR merge readiness | [docs/pr-merge-readiness.md](docs/pr-merge-readiness.md) |
| See all repository files | [CONTENTS.md](CONTENTS.md) |

## Quick Start

Validate the repository:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python3 scripts/validate_repo.py --root .
python3 -m pytest -q
```

Run the CI-safe external reviewer smoke test without calling live Claude:

```bash
python3 scripts/reviewers/run_external_reviewer.py \
  --provider claude-code \
  --config examples/external-reviewers/claude-code/claude-code.yaml \
  --input examples/external-reviewers/claude-code/review-packet.architecture.json \
  --mock-response examples/external-reviewers/claude-code/mock-raw-output.json \
  --output /tmp/reviewer-report.claude-architecture.json
```

Useful targeted checks:

```bash
python3 scripts/contract_lint.py --contract examples/memory-policy/Docs/contracts/memory-policy.contract.md
python3 scripts/gherkin_lint.py --contract examples/memory-policy/Docs/contracts/memory-policy.contract.md
python3 scripts/bdd_binding_check.py --bindings examples/memory-policy/Docs/contracts/memory-policy.bindings.yaml
python3 scripts/evidence_validate.py --evidence examples/memory-policy/evidence-report.md
```

## External Reviewers

v0.2 includes a narrow Claude Code external reviewer provider:

| Rule | v0.2 behavior |
|---|---|
| Provider | `claude-code` through project-bound wrappers only. |
| Billing/auth | Subscription-local Claude Code CLI only. |
| API keys | Forbidden; configured Claude API/proxy environment routes fail fast. |
| Authority | Read-only reviewer; no tests, no patches, no verification authority. |
| Input | Bounded review packet and rendered prompt. |
| Output | Schema-bound `reviewer-report.json` plus invocation metadata. |
| Findings | Candidate findings until main-agent relevance validation. |

Provider/model diversity is not inferred from role names. It is proven through
reviewer assignments, invocation-set evidence and normalized reviewer reports.

See [docs/external-reviewer-provider-model.md](docs/external-reviewer-provider-model.md)
and [scripts/reviewers/README.md](scripts/reviewers/README.md).

## Review And Decision Flow

```text
contract / artifact
  -> deterministic verification gate
  -> read-only reviewer reports
  -> fusion
  -> finding validation
  -> human decision when required
  -> final report
```

Review findings are candidate findings, not truth. A P0/P1 candidate blocker or
mandatory evidence gap must be validated, resolved, rejected with recorded
rationale, or sent through the workflow's collision-control path.

## PR Merge Readiness

The [pr-merge-readiness](docs/pr-merge-readiness.md) utility composes existing
verification, review, finding-validation and human-decision artifacts into a
branch-scoped readiness report.

Accepted merge-ready status requires:

- green deterministic checks;
- fresh required review evidence;
- live Claude evidence when a Claude-backed review is required;
- no validated P0/P1 blockers or mandatory evidence gaps;
- a hash-bound human `merge.acceptance` decision.

If the human selects GitHub publication, the workflow may publish a single PR
summary comment after final local acceptance and record the publication result.

## Repository Layout

```text
docs/        methodology docs, ADRs, checkpoints, plans
workflows/   workflow definitions
skills/      reusable agent procedures
scripts/     validators, reviewers and deterministic helpers
templates/   artifact templates
schemas/     JSON/YAML schemas
profiles/    review topologies, review profiles and reviewer roles
examples/    runnable and schema-valid examples
gates/       upstream gate manifests
run-artifacts/ AgentsFlow self-application run history
```

## Suggested Review Path

1. [docs/checkpoints/checkpoint-2026-06-20-documentation-legacy-adoption-confirmation.md](docs/checkpoints/checkpoint-2026-06-20-documentation-legacy-adoption-confirmation.md)
2. [docs/checkpoints/checkpoint-2026-06-19-v0.2-supported-path.md](docs/checkpoints/checkpoint-2026-06-19-v0.2-supported-path.md)
3. [docs/checkpoints/checkpoint-2026-06-19-v0.2-expert-assessment-output-contract.md](docs/checkpoints/checkpoint-2026-06-19-v0.2-expert-assessment-output-contract.md)
4. [docs/checkpoints/checkpoint-2026-06-18-v0.2.0-slice2.md](docs/checkpoints/checkpoint-2026-06-18-v0.2.0-slice2.md)
5. [docs/philosophy.md](docs/philosophy.md)
6. [docs/workflow-model.md](docs/workflow-model.md)
7. [docs/mvp-ready-workflow-standard.md](docs/mvp-ready-workflow-standard.md)
8. [docs/enforcement-boundary.md](docs/enforcement-boundary.md)
9. [docs/project-application-model.md](docs/project-application-model.md)
10. [docs/project-initialization-model.md](docs/project-initialization-model.md)
11. [docs/review-control-model.md](docs/review-control-model.md)
12. [docs/external-reviewer-provider-model.md](docs/external-reviewer-provider-model.md)
13. [docs/pr-merge-readiness.md](docs/pr-merge-readiness.md)

## Development Rule For Coding Agents

Do not expand scope. Implement accepted decisions. Make AgentsFlow usable for
the v0.2 MVP path.
