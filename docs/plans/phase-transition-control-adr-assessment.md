# ADR Assessment: Phase Transition Control

Status: draft assessment
Date: 2026-06-19

## Question

Should the phase transition control design be recorded as a new ADR or folded
into existing ADRs?

## Existing ADR Coverage

Relevant existing ADRs:

- ADR-0010: gate executability rule.
- ADR-0012: project-bound executable gates.
- ADR-0013: project application model.
- ADR-0014: project initialization and human operating decisions.
- ADR-0017: test-framed implementation phase.
- ADR-0019: workflow default/effective strictness, if accepted.

These ADRs cover gates, project binding, workflow-run artifacts, human decisions
and red/green framing. They do not directly decide how a workflow run computes
or audits the next permitted phase-boundary action.

## Recommendation

Use the proposed ADR now created as:

```text
ADR-0018-phase-transition-control.md
```

Do not silently patch the existing ADRs as the only authority source. The
decision is cross-cutting: it touches workflow runs, project bindings,
human-decision artifacts, gate evidence and enforcement boundaries. A dedicated
ADR will make the boundary clear.

## Proposed ADR Decision

The ADR should decide:

- AgentsFlow v0.2 adds a read-only `phase-transition-check` as a phase-exit
  advisory control.
- `phase_guard` remains the run-state pointer and does not become a runtime.
- The checker returns one primary next action or a blocker, plus complete
  blockers/observations.
- The checker may only recommend actions declared by workflow, project binding,
  gate manifest or run state.
- Human design discussion remains flexible; confirmed transition effects are
  normalized into existing `human-decisions.yaml`, not a new primary decision
  artifact.
- Gate authority modes are explicit: deterministic, review, or human-mediated.
- Strictness-sensitive phase transitions consume effective strictness from the
  workflow default plus explicit overrides; the checker does not choose
  strictness.
- A pre-red-capture plan approval step is a `human_mediated_gate` unless it is
  deliberately modeled as declared manual evidence for a deterministic gate.
- The checker does not mutate files, run gates, run tests, launch reviewers or
  create hidden phases.

## ADRs To Reference, Not Replace

The new ADR should reference:

- ADR-0010 for gate result semantics.
- ADR-0012 for project-bound executable gates.
- ADR-0013 for project overlay/workflow-run separation.
- ADR-0014 for human-mediated decision capture.
- ADR-0017 for red/green implementation framing.
- ADR-0019 for default/effective strictness if both ADRs remain in scope.

## Possible Existing ADR Updates

After ADR-0018 is accepted, make small cross-reference updates only:

- ADR-0013: mention phase-transition reports as workflow-run artifacts.
- ADR-0014: mention transition-effect fields as run-level human-decision
  annotations.
- ADR-0017: mention that phase-transition-check can prevent implementation from
  starting before declared preconditions are met.

Do not rewrite these ADRs to host the whole decision.

## Why Not Only Update ADR-0013 Or ADR-0014

ADR-0013 is about project application structure. ADR-0014 is about project
initialization and human operating decisions. Phase transition control applies
beyond initialization and is specifically about preventing run-state drift at
phase boundaries. Folding it into either ADR would hide the central decision.

## Timing

Keep ADR-0018 in Proposed status while the draft plan is under design review.
Promote it to Accepted only after the plan decisions are confirmed.
