# Skill: contract-authoring

## Purpose

Create a task/feature contract with intent, fixed decisions, boundaries,
feature-specific risk surfaces, Failure Path Matrix coverage when required,
scenarios, verification binding, review-topology rationale and evidence
requirements.

## Inputs

- `intent`
- `specification_brief`
- `domain_pack`
- `strictness`
- `project_operating_decisions` or workflow binding when available
- `risk_surface_policy`
- `target_workflow`


## Outputs

- `task_contract`
- `boundaries`
- `fixed_decisions`
- `risk_surface_profile`
- `failure_path_matrix` when selected risk surfaces require it
- `verification_binding`
- `review_topology_rationale`


## Procedure

1. Write intent and non-goals.
2. List fixed decisions and relevant ADRs.
3. Define allowed and forbidden paths/behavior.
4. Select only the feature-specific risk surfaces that materially affect the
   task, using `docs/risk-and-strictness.md` and project-local surface policy.
   Do not treat project defaults as automatic coverage claims.
5. For each selected surface, record required path classes. If the surface has
   denial, failure, timeout, rejection, persistence or authority semantics,
   create a Failure Path Matrix row for each required path class.
6. For each Failure Path Matrix row, state trigger, expected authority,
   expected context/state, expected audit/persistence behavior, forbidden
   outcome and evidence binding or explicit deferral.
7. Add or link BDD scenarios for the selected behavior and failure paths.
8. Bind required scenarios and FPM rows to tests, scripts, trace/log assertions,
   manual evidence or a human-approved residual-risk deferral before red capture
   or implementation.
9. Derive the minimal review topology from selected risk surfaces. Record the
   topology source, selected surfaces and escalation reason; do not add reviewers
   merely because the feature feels complex.


## Quality bar

- Contract is actionable.
- Boundaries are explicit.
- Evidence requirements are checkable.
- Selected risk surfaces are justified by the feature, not copied blindly from a
  generic list.
- Required FPM rows are bound to evidence or explicitly deferred with residual
  risk.


## Anti-patterns

- Writing broad prose without enforceable constraints.
- Changing accepted decisions silently.
- Listing risk surfaces without path classes or evidence bindings.
- Using risk-driven review as an implicit reviewer router without recorded
  topology rationale.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.
