# ADR-0017: Test-framed implementation phase (red-before, green-after)

## Status

Accepted for v0.2 (pre-handoff design, 2026-06-18).

**Implementation status: NOT yet built.** The structural check in `validate_repo.py`,
the `failing_run`/`passing_run` schema fields, the `redgreen_check` runner, and the
red-capture phase in `big-feature-contract-first` do not exist yet. This ADR records
the accepted rule; building it is tracked in
`docs/handoff/codex-v0.2-prehandoff-tasks.md`.

## Context

AgentsFlow already has the two outer halves of test-driven discipline, but the
middle — the "red" step — is implicit and only half-present:

- "Specification/test-first" is dissolved into contract-first authoring, BDD
  scenarios and behavior bindings (behavior is written before code).
- "Green" (verification) is produced by the verification gate.
- "Red" (a recorded failing run against the unsatisfied state) is explicit ONLY in
  `bugfix-regression-capture` (the `reproduce` phase + `regression_gate`), and even
  there it is soft ("reproduced or simulated"). The term "TDD" appears nowhere as an
  applied rule, and `big-feature-contract-first` has no red-capture step before
  implementation.

Consequence of the gap: an implementation can be accepted on an always-green test,
or on a test that was never run against broken code — exactly the "model
self-certifies verification" failure the project exists to prevent (ADR-0010). The
discipline existed in spirit but was lost behind higher abstractions and applied
inconsistently.

## Decision

Make red-before / green-after a first-class **phase-topology rule** on the
implementation phase, rather than a scattered convention or a standalone check.

In any workflow that contains a phase of `kind: implementation`, that phase MUST be
framed by two phases:

```
[ contract → executable tests → run, capture RED ]   (pre-implementation)
        ↓
[ implementation ]
        ↓
[ re-run the same tests → GREEN ]                    (post-implementation)
```

- The pre-implementation phase translates the contract / required acceptance
  scenarios into real executable tests and runs them against the not-yet-implemented
  state; the failing (red) runs are captured as evidence.
- The post-implementation phase re-runs the same tests; the passing (green) runs are
  captured as evidence.
- The red→green evidence pair is therefore a natural byproduct of the phase
  structure, not a separately mandated artifact.

This rule is to be enforced structurally: `validate_repo.py` / the workflow schema
must reject a workflow that contains an `implementation` phase without the framing
red-capture and green-verify phases — mirroring the existing checks that a
gate/verification phase must declare a gate manifest and that a review phase declares
no scripts. (See Implementation status above: this check is not yet built.)

## Alternatives considered

- **Standalone red→green evidence check only (no phase rule).** A deterministic
  checker that inspects the evidence bundle for a failing-then-passing pair, without
  changing workflow structure. Rejected as the *primary* mechanism: it verifies the
  symptom without guaranteeing the process. The topological rule makes the red and
  green runs happen by construction and keeps the workflow definition honest. The
  deterministic evidence check is retained, but as the *enforcement* of this rule,
  not as a substitute for it.
- **A strictness-profile-scaled mandate (mandatory only at L3/L4).** Rejected as
  overcomplicated for v0.2: the rule is about the presence of an implementation
  phase, not about risk level. Workflows without an implementation phase
  (review-only, spec-first) are simply unaffected, which already provides
  proportionality.

## Consequences

- `big-feature-contract-first` gains an explicit pre-implementation red-capture
  phase; `bugfix-regression-capture` already conforms (`reproduce` → fix →
  `regression_gate`) and is aligned to the same shape.
- `validate_repo.py` (and the workflow schema) gain a structural check for the
  framing.
- The behavior-binding / evidence schema gains fields to record the failing-run /
  passing-run pair; a deterministic `redgreen_check` enforces their presence as part
  of the verification gate.
- Workflows with no implementation phase (e.g. `review-only-fusion`,
  `new-project-spec-first`) are unaffected — the rule is proportionate by
  construction.
- Refines and depends on ADR-0010 (gate executability) and ADR-0011 (behavior
  binding). Supersedes the standalone "red→green check" framing previously recorded
  as ODD-2 layer A, folding it in as this rule's enforcement detail.
- The reviewer "does the test actually exercise its scenario?" judgment (ODD-2 layer
  B) remains separate and complementary.
