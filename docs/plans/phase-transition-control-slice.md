# Phase Transition Control Slice Plan

Status: accepted design baseline; implementation not started
Date: 2026-06-19

## Purpose

Add a small deterministic control point at workflow phase boundaries without
turning AgentsFlow into a workflow runtime.

The motivating failure came from applying AgentsFlow to a real downstream
project: the conversation-level plan and the actual run state drifted. The
agent remembered the intended order imperfectly, while the existing `phase_guard`
only constrained artifact ledgers and did not compute the next permitted action.

## Core Design

Keep the existing abstractions:

- `phase_guard` remains the workflow-run state pointer.
- `human-questions.yaml` remains the human decision prompt artifact.
- `human-decisions.yaml` remains the normalized run decision log.
- gate reports remain gate results.
- review-cycle and finding-validation reports remain review/finding controls.

Clarify gate terminology:

- `deterministic_gate`: decided by a runner over declared checks/evidence;
- `review_gate`: reviewer reports plus main-agent relevance validation;
- `human_mediated_gate`: main-agent synthesis plus recorded human decision.

The planned checker must respect the declared gate authority mode. It must not
turn a deterministic `plan_gate` into a hidden review or human approval flow.

## Accepted Design Baseline

The following decisions are accepted for this slice:

1. The main/orchestrating agent must run `phase-transition-check` before a
   declared phase boundary transition, not on every discussion turn inside a
   phase. Required boundary examples include:
   - moving from planning/specification to `red_capture`;
   - starting implementation;
   - running the green `verification_gate`;
   - launching the post-verification review gate;
   - making the final acceptance decision.
2. `phase-transition-report` stays narrow. It has one `primary_next_action`,
   plus `blockers[]`, `observations[]`, `checked_refs[]`, `may_transition` and
   `target_phase`. It is not a dispatcher and must not return several competing
   next steps for the main agent to choose from.
3. Agentic plan review plus human approval before red capture is an explicit
   `human_mediated_gate`. It is not an implicit side effect of deterministic
   `plan_gate`.
4. `human-decisions.yaml` gets only minimal transition-control extensions:
   `transition_effect`, `invalidated_artifacts` and `recovery`. Formal decision
   versioning, conflict graphs and append-only enforcement remain out of scope.
5. v0.2 phase transition control catches procedural drift only: unresolved
   blocking decisions, missing current-phase artifacts, missing declared
   gate/manual evidence, undeclared phase transitions and pending recovery. It
   does not judge architectural quality.

Add one read-only checker:

```text
phase-transition-check
```

It reads workflow definition, project binding, run state, human decision
artifacts, gate/report references and current phase evidence. It returns one
primary next action or a blocker. It must not mutate `run.yaml`, run gates,
launch reviewers, run tests, edit files or insert hidden workflow phases.

## Non-Goals

Do not add:

- a workflow runtime;
- automatic `run.yaml` mutation;
- a new gate type;
- a new review/fusion/finding mechanism;
- a required `decision-impact-records/` directory;
- `decision-impact-record` schema/template as a new primary decision artifact;
- an artifact dependency graph;
- implicit lighter-profile `plan_gate` override semantics;
- ad hoc strictness selection at phase transition time;
- implicit pre-implementation review inside `plan_gate`;
- an undeclared human-mediated plan approval gate.
- formal human-decision versioning, conflict graphs or append-only enforcement.

## Existing Abstractions Reused

`phase_guard` already records:

- `current_phase`;
- `completed_phases`;
- `allowed_next_phases`;
- `allowed_outputs`;
- `forbidden_outputs_until_phase_exit`;
- blocked state.

The new checker interprets that state. It does not replace it.

`human-decisions.yaml` already records run-level decisions with
`classification`, `status` and `affected_artifacts`. Confirmed transition effects
belong there, not in a parallel decision artifact.

`human-questions.yaml` should stay focused on prompts, options, option impacts
and affected artifacts. It should not carry confirmed transition/recovery state.

## Lessons From 3-Agent Plan Review

The initial plan had three material defects:

1. It treated strictness as an ad hoc binding choice and a lighter-profile
   `plan_gate` exception as if it were already a first-class source-of-truth
   concept. That is the wrong direction. The checker must consume effective
   strictness derived from workflow `default_strictness` plus an explicit
   override reason.
2. It allowed `next_action=launch_reviewers` while the current
   `big-feature-contract-first` workflow defines review after
   `verification_gate`, not after `plan_gate`. A checker must not invent hidden
   review phases.
3. Its `next_action` set was too broad and could become an implicit dispatcher.
   Next actions must be phase-local, derived from workflow/binding declarations,
   and accompanied by all blockers/observations.

## Revised Transition Report Contract

Add:

```text
schemas/phase-transition-report.schema.json
templates/phase-transition-report.yaml
```

Required report shape:

```yaml
schema_version: 1
run_id: YYYY-MM-DD-task-slug
status: blocked
current_phase: plan_gate
primary_next_action:
  type: collect_declared_manual_evidence
  source: project_binding
  target_phase: plan_gate
  declared_ref: .agentsflow/workflows/big-feature-contract-first.binding.yaml#gates.plan_gate
may_transition: false
target_phase: null
blockers:
  - id: missing-plan-gate-review-evidence
    severity: blocking
    reason: "The project binding declares required manual review evidence for plan_gate."
    refs:
      - .agentsflow/gates/plan_gate.yaml
      - .agentsflow/workflows/big-feature-contract-first.binding.yaml
observations: []
checked_refs:
  - run.yaml
  - human-decisions.yaml
  - workflow binding
  - gate manifest
```

`primary_next_action` is singular. `blockers[]` and `observations[]` may contain
multiple entries so the report does not hide secondary issues.

## Allowed Statuses

```text
invalid_state
blocked
needs_human_decision
continue_current_phase
ready_for_gate
ready_to_transition
```

## Narrow Action Types

Use phase-local advisory actions only:

```text
normalize_discussion
resolve_human_decisions
update_current_phase_artifacts
run_declared_gate
collect_declared_manual_evidence
refresh_declared_gate_evidence
validate_findings
transition_to_declared_next_phase
stop_blocked
```

The checker must not recommend an action unless it can cite the workflow,
project binding, gate manifest or run state that declares that action or
evidence requirement.

## Human Decision Extensions

Extend only `human-decisions.yaml` schema/template with typed optional fields.

Candidate fields:

```yaml
decision_kind: workflow-design
transition_effect:
  type: refresh-current-phase
  requires_recovery: true
  status: pending
invalidated_artifacts:
  - contract-gate-report.md
recovery:
  status: pending
  required_action: refresh_contract_and_rerun_contract_gate
  evidence_refs: []
```

Use existing top-level decision statuses only:

```text
confirmed
defaulted
unresolved
rejected
superseded
explicitly_deferred_with_constraints
```

Do not introduce top-level `accepted` or `pending` decision statuses.

Blocking rule:

```text
confirmed blocking-material decisions with transition_effect.requires_recovery
and recovery.status != completed block phase transition, unless explicitly
deferred with constraints by the human.
```

## Workflow-Run Integration

Transition reports may be referenced from `phase_status` or `phase_evidence`.
Because existing validation scans artifact-like keys in those sections, any
example that references `phase-transition-report.yaml` must include that exact
path in the current phase's `phase_guard.allowed_outputs`.

Do not store a runtime log inside `phase_guard`. If needed, `phase_guard` may
contain only a reference to the latest transition report, but that reference must
not become a second source of truth.

## Minimal Checker Behavior

Add:

```text
scripts/phase_transition_check.py
scripts/contracts/phase_transition_check.yaml
```

The script is read-only.

Minimum checks:

1. Parse workflow binding and run state.
2. Validate that `current_phase` exists in the referenced workflow or project
   binding context.
3. Detect open or unresolved `blocking-material` questions/decisions.
4. Detect confirmed `blocking-material` decisions with pending recovery.
5. Detect missing current-phase required artifacts declared by `phase_guard`.
6. Detect missing declared gate/manual evidence only when it is explicitly
   declared by workflow, project binding or gate manifest.
7. Refuse to produce a next action that cannot cite a declaring source.
8. Produce a schema-valid `phase-transition-report`.

The checker does not decide architectural correctness. It only reports whether
the current run state permits a declared next procedural step.

## Corrected Bro-Like Case

If `big-feature-contract-first` inherits its default strictness and that
effective strictness requires `plan_gate`, and `plan_gate` has passed with no
extra declared manual evidence requirement, the checker may report:

```text
ready_to_transition -> transition_to_declared_next_phase(red_capture)
```

If a project binding explicitly declares required plan-gate manual evidence, the
checker may report:

```text
blocked or ready_for_gate -> collect_declared_manual_evidence
```

It must not infer `launch_reviewers` merely because the human conversation wanted
pre-implementation review. That review must be represented in workflow or
project binding first.

If the intended control is "agent plan review plus human approval before
red-capture", model it explicitly as a `human_mediated_gate`, for example:

```text
technical_plan
-> deterministic plan_gate
-> plan reviewer reports
-> main-agent synthesis/finding validation
-> human_mediated_gate: plan_review_decision
-> red_capture
```

The phase-transition checker can then require the declared
`plan_review_decision` output before permitting transition to red-capture.

## Red Tests

Add failing tests first for:

1. phase-transition report rejects multiple primary next actions.
2. blocked/needs-human-decision reports require `blockers[]`.
3. malformed human decision `transition_effect` fails schema validation.
4. top-level decision `status: accepted` fails schema validation.
5. confirmed blocking-material decision with pending recovery blocks transition.
6. checker refuses an undeclared next action.
7. transition report references in `phase_status` require matching
   `phase_guard.allowed_outputs`.
8. `validate_repo.py` validates the new report schema/template, or targeted tests
   explicitly cover it until repository validation is wired.

## Implementation Surfaces

Add:

- `schemas/phase-transition-report.schema.json`
- `templates/phase-transition-report.yaml`
- `scripts/phase_transition_check.py`
- `scripts/contracts/phase_transition_check.yaml`

Extend:

- `schemas/human-decisions.schema.json`
- `templates/human-decisions.yaml`
- `templates/workflow-run.yaml`
- `docs/workflow-model.md`
- `docs/human-interaction-protocol.md`
- `docs/enforcement-boundary.md`
- `docs/contracts/agentsflow-v0.2-mvp.contract.md`
- `docs/contracts/agentsflow-v0.2-mvp.bindings.yaml`
- repository validation/tests as needed

Do not extend `human-questions.yaml` with confirmed transition/recovery fields.

## Green Checks

Run after implementation:

```bash
python3 scripts/validate_repo.py --root .
python3 -m pytest -q
```

Also run targeted tests for `phase_transition_check.py` and the new schema
fixtures.

## Review Gate

After green checks, run two fresh-context read-only reviewers with the same
prompt, packet, rubric and output schema.

Reviewer scope:

- phase-transition report schema/template;
- human decision schema/template extensions;
- phase transition checker;
- workflow model docs;
- enforcement-boundary claims;
- v0.2 contract/bindings/tests.

Reviewer severity:

- P1 if the checker can invent undeclared workflow actions, mutate run state,
  bypass unresolved blocking decisions, or conflict with existing
  `big-feature-contract-first` phase order.
- P2 for schema/docs drift, missing negative tests, or ambiguous enforcement
  level.
- P3 for clarity and future extension concerns.

## Stop Conditions

Stop and discuss before implementation if the slice requires:

- a new workflow runtime;
- automatic phase rewinds;
- automatic `run.yaml` updates;
- artifact dependency graph calculation;
- hidden review phases;
- changing strictness semantics beyond consuming declared effective strictness;
- changing existing review-cycle/finding-validation semantics.

## Open Design Questions

1. Should project bindings get a first-class `additional_required_gates` or
   `phase_manual_evidence` field in a later slice, or is explicit
   workflow/binding phase and gate declaration sufficient?
2. Should `phase_transition_check.py` be wired into `validate_repo.py` immediately
   for templates/examples, or covered by targeted tests first?

## Follow-Ups

- Consider human-decision versioning after real workflow pilots. v0.2 keeps
  `human-decisions.yaml` as a simple run-level decision log with existing
  statuses such as `confirmed`, `defaulted`, `unresolved`, `rejected`,
  `superseded` and `explicitly_deferred_with_constraints`. Do not add revision
  numbers, conflict graphs, active-decision uniqueness checks or append-only
  enforcement in this slice.
- Decide whether to collapse current `L*` strictness identifiers into a smaller
  taxonomy. The phase-transition checker should depend only on effective
  strictness, not on a fixed number of project-facing modes.
