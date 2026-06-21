# Workflow Model

## Definition

A workflow is a named, reusable process for a class of agent-assisted development work.

A workflow answers:

- What is the goal of this work?
- What artifacts are expected?
- Which skills are invoked?
- Which scripts are mandatory or optional?
- Which templates should be used?
- Which domain packs can parameterize it?
- What default strictness and supported override values apply?
- Which review topologies make sense?
- Which risk surfaces can change gate, evidence or review depth?

## Workflow is the primary abstraction

Strictness is not the primary abstraction. A workflow owns its normal depth through
`default_strictness`; a project binding or run may explicitly override it only
with a reason.

Example:

```yaml
workflow: prompt-behavior-eval
domain_pack: coding-agent
default_strictness: L3
effective_strictness: L3
review_topology: heterogeneous-variable
```

The workflow defines the type of work and its baseline gate/review/evidence
depth. The effective strictness controls conditional gates for a concrete
binding or run. Humans should not be asked to choose an `L*` value by default;
the main agent should inherit the workflow default and ask only when project risk
or task constraints justify an override.

The number of strictness labels is not a goal. v0.2 remains compatible with the
current `L*` identifiers, but the model should also support a smaller future
taxonomy such as standard/elevated/critical without changing the workflow
boundary.

When a workflow uses the term "gate", it should be clear which authority mode is
intended:

```text
deterministic_gate
  A project-bound runner decides from declared checks/evidence.

review_gate
  Reviewer reports are relevance-validated before the workflow exits.

human_mediated_gate
  The main agent presents synthesized evidence/options and records the human
  decision before proceeding.
```

The distinction matters most around planning. A `plan_gate` can be a
deterministic check that the plan packet is grounded and complete; an agentic
review of that plan followed by human approval is a separate
`human_mediated_gate` unless the workflow or project binding explicitly models
it as part of the plan gate's required evidence and decision policy.

## Workflow manifest shape

See `schemas/workflow.schema.json` and `templates/workflow.yaml`.

Minimal fields:

```yaml
name: big-feature-contract-first
version: 0.1
intent: "Design and implement a large feature through a contract-first process."
default_strictness: L3
entry_criteria: []
outputs: []
uses:
  skills: []
  scripts: []
  templates: []
supported_profiles:
  strictness: []
  review_topologies: []
```

A phase sequence carries one structural constraint: any phase of `kind:
implementation` must be preceded by a red-capture (failing-test) phase and followed
by a green-verify phase; `validate_repo.py` enforces this workflow topology with
`test_framing` markers (ADR-0017). Refactor-only workflows may use
`baseline_capture` before `change_type: refactor`, because the pre-change
behavior-preservation baseline is expected to pass rather than fail.

Workflow phases may also declare `human_interaction`. This does not create a
runtime; it tells the main/orchestrating agent when a workflow run may enter
`paused_waiting_for_human`, which question/decision artifacts to update, and which
resume states are allowed. See `docs/human-interaction-protocol.md`.

Workflow runs may declare a lightweight `phase_guard` in `workflow-run.yaml`.
This is not a workflow engine. It is a run-state pointer for the
main/orchestrating agent:

- `current_phase`;
- `completed_phases`;
- `allowed_next_phases`;
- `allowed_outputs`;
- `draft_artifacts`;
- `forbidden_outputs_until_phase_exit`;
- `blocked` / `blocked_by`.

When `phase_guard` is present, repository validation checks declared run
artifacts against the current phase's allowed outputs. `draft_artifacts` may
appear only in draft-labeled top-level `artifacts` slots; evidence, output and
report ledger fields require `allowed_outputs`. This prevents an agent from
making a future-phase artifact look authoritative before the current phase
exits. The guard is intentionally protocol-level in v0.2: it validates the run
artifact ledger, not every file that may exist on disk.

## Risk surfaces across workflow levels

Risk surfaces are defined in `docs/risk-and-strictness.md` and flow through the
same three-level model as other workflow policy:

```text
Workflow Definition
  May name common surfaces that usually matter for this workflow class.

Project Binding / Overlay
  Selects project-default surfaces, project-local surfaces, required path
  classes, review escalation rules and evidence storage/freshness policy.

Workflow Run
  Selects the concrete feature surfaces, records a Failure Path Matrix, binds
  path classes to checks/evidence, and invalidates stale evidence after material
  changes.
```

Upstream workflows must not hard-code project-specific commands or local risk
surface names. They may require that a project or run declare the selected
surfaces and bind them to project-level gates.

Evidence freshness is run-scoped. A workflow run should record the latest
`material_change_id`, the green verification evidence produced after that change,
and the review packet prepared from that evidence. Review/fusion evidence before
the latest material change is not authoritative for the changed scope.

## Current workflows

| Workflow | v0.2 status | Purpose |
|---|---|---|
| `big-feature-contract-first` | supported target | Implement a large feature through contract, BDD scenarios, impact map, verification, evidence. |
| `review-only-fusion` | utility | Run independent review and fusion on an existing artifact or diff. |
| `new-project-spec-first` | reference/next | Start a new project with problem framing, specs, ADR seeds, and initial contracts. |
| `bugfix-regression-capture` | reference/next | Reproduce a bug, fix it, and convert it into a regression scenario. |
| `agentic-system-hardening` | reference/experimental | Harden agent systems: prompts, tools, memory, context, policy, model router, traces. |
| `prompt-behavior-eval` | reference/experimental | Evaluate changes to prompts/skills/instructions using behavioral scenarios. |
| `safe-refactor` | reference/experimental | Perform scoped refactoring with boundary and regression protection. |
| `research-to-ADR` | reference/experimental | Turn research into decision memos and ADRs. |

## Candidate future workflows

The following are known candidate workflows, but they are not promoted into the
v0.2 supported path:

| Candidate workflow | Candidate status | Purpose |
|---|---|---|
| `release-pr-readiness` | candidate/next | Decide whether a branch is ready to open, accept or merge as a pull request by composing validation, documentation consistency, review-gate evidence, finding relevance validation, human merge approval and post-merge verification planning. |
| `knowledge-extraction` | candidate/next | Extract normalized project knowledge from a project documentation corpus or knowledge base with provenance, confidence, human-confirmation boundaries and persistence scope. |

Current `project-initialization` may already produce
`project-knowledge-extraction.md` when the human selects documentation
`knowledge-extraction`. That run-level artifact is not the same thing as a
standalone `knowledge-extraction` workflow. A future workflow should reuse the
same documentation-disposition and human-decision rules rather than creating a
parallel abstraction.

See `docs/plans/v0.2-next-slices.md` for the current high-level sequencing note
covering release/PR readiness, a fresh Bro Tools Gateway TG-A dogfood run, and a
future standalone knowledge-extraction workflow.

## Workflow selection guidance

For v0.2 `prepare-workflow`, only `big-feature-contract-first` is a supported
target workflow. Other workflows are utility, reference or experimental unless a
future accepted decision promotes them into the supported target set.

Use `new-project-spec-first` when the main risk is ambiguous initial direction.

Use `big-feature-contract-first` when the main risk is scope creep or architecture drift during implementation.

Use `agentic-system-hardening` when the main risk is runtime behavior of agents, tools, memory, or policy.

Use `prompt-behavior-eval` when the main artifact is a prompt, instruction set, or skill behavior.

Use `safe-refactor` when behavior should remain stable and scope boundaries matter.

Use `bugfix-regression-capture` when a known failure must become a permanent scenario.

Use `research-to-ADR` when implementation should not start until alternatives and decisions are explicit.

Use `review-only-fusion` when the work is already done and the need is independent review.

## Workflow definition, project binding and workflow run

AgentsFlow separates three levels:

```text
Workflow Definition
  Universal upstream process shape under `workflows/`.

Project Binding / Overlay
  Project-specific mapping from workflow requirements to repo paths, commands,
  gates, instruments, evidence sources and local rules.

Workflow Run
  Concrete task instance with task contract, plan, behavior bindings, gate reports,
  evidence bundle, reviewer reports, finding validation and fusion report.
```

Upstream workflow definitions must not be edited for each project. Projects
should create `.agentsflow/` overlays and workflow binding files.
