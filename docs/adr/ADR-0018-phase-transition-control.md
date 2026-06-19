# ADR-0018: Phase Transition Control

## Status

Proposed.

Date: 2026-06-19

## Context

AgentsFlow v0.2 already has several controls for workflow execution:

- `phase_guard` records the current workflow-run phase, allowed outputs and
  allowed next phases.
- human interaction is mediated through `human-questions.yaml` and
  `human-decisions.yaml`.
- project bindings map upstream gate contracts to project-bound runners.
- gate reports, review-cycle reports and finding-validation reports preserve
  evidence and review decisions.

These controls are not a workflow runtime. In particular, `phase_guard` is
currently a ledger-oriented run-state pointer: validators can reject future-phase
artifacts in the run ledger, but they do not compute the next permitted action.

The term "gate" is also overloaded unless its authority mode is explicit:

```text
deterministic_gate
  decided by a runner over declared checks/evidence;

review_gate
  decided by review outputs plus main-agent relevance validation;

human_mediated_gate
  decided by the human after main-agent synthesis of evidence, review outputs and
  options.
```

A real downstream pilot exposed the gap: the conversation-level plan and the
actual workflow run state drifted. The agent remembered the intended workflow
order imperfectly and needed human correction before proceeding. That failure is
central to AgentsFlow's purpose: important workflow sequencing must not depend
only on prompt discipline or conversation memory.

## Proposed Decision

If accepted, AgentsFlow will add a read-only **phase transition check** as a
phase-boundary control.

The check will:

- read workflow definition, project binding, workflow-run metadata, human
  decision artifacts and declared gate/review evidence references;
- return a schema-valid phase-transition report with one primary next action or
  a blocker;
- include all detected blockers and observations;
- recommend only actions declared by the workflow, project binding, gate
  manifest or run state;
- be run by the main/orchestrating agent before declared phase boundary
  transitions, such as entering red capture, starting implementation, running
  green verification, launching post-verification review, or making final
  acceptance;
- preserve `phase_guard` as the run-state pointer;
- preserve `human-decisions.yaml` as the normalized run decision log.

The check will not:

- mutate `run.yaml`;
- run gates, tests or scripts other than itself;
- launch reviewers;
- create hidden workflow phases;
- infer project policy that is not declared in workflow or project binding;
- choose or override strictness; it only consumes declared effective strictness;
- replace gate reports, review-cycle reports or finding-validation reports;
- implement an artifact dependency graph or automatic rewind engine;
- collapse deterministic, review and human-mediated gate authority into one
  implicit action.
- add formal human-decision versioning or conflict-graph semantics.

## Human Design Loop Boundary

Human discussion inside a phase remains flexible. The proposed control does not
require YAML for every message.

Before phase exit, material decisions must be normalized into existing run-level
decision artifacts. Confirmed transition effects, if needed, should be expressed
as optional typed fields on `human-decisions.yaml`, not as a new primary
decision-impact artifact.

`human-questions.yaml` remains a prompt/options artifact. It may describe option
impact and affected artifacts, but confirmed recovery/transition state belongs
in `human-decisions.yaml` or in the phase-transition report.

A pre-implementation plan review with human approval is a
`human_mediated_gate`, not an automatic `plan_gate` side effect. The workflow or
project binding must declare that control before a transition checker can require
it.

The v0.2 checker catches procedural drift only. It may block on unresolved
blocking decisions, missing current-phase artifacts, missing declared gate/manual
evidence, undeclared transitions or pending recovery. It does not decide whether
an architecture or feature plan is substantively good.

## Relationship To Existing ADRs

This ADR would refine:

- ADR-0010, because phase transition control must not replace gate executability.
- ADR-0012, because declared project-bound gates remain the source of gate
  execution authority.
- ADR-0013, because phase transition reports are workflow-run artifacts.
- ADR-0014, because transition effects are normalized through existing
  human-mediated decision artifacts.
- ADR-0017, because the checker can prevent implementation from starting before
  declared red-capture or gate preconditions are satisfied.

It also depends on the proposed default/effective strictness model in ADR-0019
for strictness-sensitive phase transitions.

## Consequences If Accepted

- Agents have a deterministic read-only checkpoint before moving across phase
  boundaries.
- The checker makes workflow drift visible without becoming a workflow runtime.
- Project-specific additions, such as extra manual evidence for a gate, must be
  declared in project binding or gate manifest before the checker can enforce
  them.
- Strictness-sensitive transitions use effective strictness from the workflow
  default plus any explicit project/run override; the checker must not invent a
  strictness override as a way to reach a desired next phase.
- Hidden review phases remain forbidden. A pre-implementation review must be a
  declared workflow/binding feature before any checker can recommend collecting
  that evidence.
- Human-mediated gates become explicit controls rather than implicit pauses in
  the conversation.
- Existing review/fusion/finding controls remain unchanged.

## Alternatives Considered

### Rely on `phase_guard` only

Rejected as insufficient. `phase_guard` prevents some artifact-ledger drift but
does not compute the next procedural action.

### Build a workflow runtime

Rejected for v0.2. A runtime would be too large and would blur the boundary
between deterministic checks, model judgment and human decisions.

### Add separate decision-impact records

Rejected for the current plan. Existing human question/decision artifacts already
carry run-level decisions. A new required decision-impact directory would create
parallel authority.

### Let the checker launch reviewers or run gates

Rejected. That would turn a read-only boundary check into an orchestrator. The
main/orchestrating agent remains responsible for acting on the report.

## Open Questions

- Should project bindings get a first-class field for additional required gates
  or phase manual evidence in a later slice, or is explicit workflow/binding
  phase and gate declaration sufficient?
- Should phase-transition report validation be wired into repository validation
  immediately, or covered by targeted tests first?

## Follow-Up

Human-decision versioning is intentionally deferred. v0.2 keeps the existing
human decision statuses, including `superseded`, without adding revision numbers,
conflict graphs, active-decision uniqueness checks or append-only enforcement.
