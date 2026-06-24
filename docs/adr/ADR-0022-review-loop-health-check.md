# ADR-0022: Review Loop Health Check

## Status

Accepted.

Date: 2026-06-24

Decision provenance: accepted by the human-mediated Slice A planning and
decision discussion on 2026-06-24. Local run artifacts may record a normalized
decision log, but this ADR is the repository authority for the accepted rule.

## Context

Review-fix loops can fail in a way that local patching does not solve. Repeated
validated blockers may indicate:

- a contract gap;
- a wrong failure-path matrix;
- stale or false-green verification evidence;
- unclear authority boundaries;
- scope drift;
- the main/orchestrating agent repeatedly patching symptoms rather than root
  cause.

AgentsFlow already has finding validation, fusion and review-cycle reports. The
missing control is a lightweight health checkpoint that activates only when the
loop itself shows a repeated problem.

## Decision

AgentsFlow defines a **review-loop health checkpoint**.

The checkpoint is an exception path, not a standard phase of every review
cycle. When no trigger fires, no health-check artifact is required.

The checkpoint is required when any trigger fires. Trigger policy is `OR`, not
`AND`:

1. three consecutive review cycles have validated P0/P1 blockers or mandatory
   evidence gaps;
2. the same validated risk surface repeats in two cycles;
3. stale or false-green evidence blockers repeat.

Triggers count only main-agent validated findings and mandatory evidence gaps.
Raw reviewer candidates do not trigger the checkpoint by themselves. Rejected,
duplicate or downgraded findings do not count unless finding validation keeps a
grounded blocker or mandatory-evidence path open.

Repeated-surface detection uses canonical selected risk surface ids from the
run, for example:

- `risk_surface_profile.selected_risk_surfaces`;
- declared project-local surfaces;
- Failure Path Matrix rows that reference selected surfaces.

Reviewer wording is not a source of truth. Finding validation maps each
material candidate to a canonical selected `risk_surface_id` or records it as
`unmapped_or_new_surface_candidate` with a decision about whether the contract
or project-local risk policy needs an update.

## Checkpoint Ownership

The main/orchestrating agent owns the checkpoint by default.

The checkpoint is not:

- a new review gate;
- a standard artifact for every review cycle;
- a cycle cap;
- an automatic reviewer launch;
- a replacement for phase-transition control;
- a workflow runtime.

Optional fresh-context diagnostic reviewers may be launched only when at least
one diagnostic condition is present:

- the blocker pattern is unclear;
- classification is disputed, such as `contract_gap` vs
  `implementation_defect`;
- repeated P1 findings come from different reviewers and root cause is
  unclear;
- there is a concrete risk that the main agent is stuck in local patching;
- accepted scope or authority decisions may be drifting.

Diagnostic reviewers are read-only. Their outputs are diagnostic inputs, not
substantive review-gate findings until the main agent validates relevance.

## Checkpoint Content

A health checkpoint records:

- trigger id and trigger evidence;
- review cycles considered;
- validated findings or mandatory evidence gaps counted;
- canonical risk surface ids involved;
- root-cause classification;
- correction obligations before the next review gate;
- whether diagnostic reviewers were used, and why;
- whether human decision is required;
- closure requirements.

Suggested root-cause classifications:

```text
contract_gap
failure_path_matrix_gap
verification_gap
false_green_or_stale_evidence
implementation_defect
authority_boundary_gap
scope_drift
provider_or_environment_blocker
main_agent_looping_on_local_patch
unknown_requires_diagnostic_review
```

## Closure

After a health checkpoint fires, a closure record is required before the next
substantive review gate. For the MVP this may be a structured section in the
next review-cycle or review-fix-loop report. A standalone closure schema should
be added only if later validation needs justify it.

Closure starts minimal. Do not add a standalone closure schema while a section
in the existing review-cycle/report artifact can carry the required evidence.

Closure records:

- which correction obligations were completed;
- what evidence was refreshed;
- whether contract, scope, FPM, verification or implementation changed
  materially;
- whether review must rerun;
- remaining residual risk or human-approved deferral.

The next review packet includes the checkpoint and closure record so reviewers
can inspect whether the repeated class of problem was addressed.

## Relationship To Existing Controls

The checkpoint complements ADR-0007 finding validation. It uses validated
findings as input; it does not change the candidate-finding rule.

It complements ADR-0018 phase transition control. Phase transition control
decides whether the workflow can cross declared phase boundaries. Review-loop
health asks whether a repeated review/fix loop needs root-cause correction
before another substantive review gate.

It preserves ADR-0020's operating-protocol boundary. The checkpoint records
judgment and correction obligations; it does not orchestrate reviewers or
implementation automatically.

## Consequences

- Repeated blockers produce root-cause evidence instead of only another local
  patch attempt.
- Health control remains bounded and trigger-based.
- Fresh diagnostic review is available for unclear root cause without becoming
  mandatory review inflation.
- Later implementation can start minimal and add a standalone schema only if
  validation needs require it.

## Non-Goals

- Do not use the checkpoint as a fixed review-cycle cap.
- Do not launch a review gate only to create a checkpoint.
- Do not require a checkpoint artifact when no trigger fired.
- Do not count raw reviewer candidates as health triggers.
- Do not replace finding validation, fusion or phase transition checks.
