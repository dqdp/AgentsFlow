# Design Decision Review: <title>

## Purpose

Explain what design boundary this packet controls and what phase transition, if
any, human acceptance authorizes. Do not ask for blanket approval without a
decision inventory.

## Review Procedure

1. Present the full open decision inventory.
2. Review each decision independently.
3. For each decision, show viable options, tradeoffs, recommendation and
   rationale.
4. Record explicit human acceptance, change requests or approved deferrals.
5. Proceed only when blocking decisions are accepted, changed or explicitly
   deferred with residual risk.

## Open Decision Inventory

| ID | Decision | Blocking before phase exit? | Recommended path |
|---|---|---:|---|
| DDR-001 | <decision name> | yes | <recommended option> |

## DDR-001: <Decision Name>

### Problem

What must be decided, and why does it matter now?

### Options

| Option | Description | Strengths | Costs / risks |
|---|---|---|---|
| A | <option> | <strengths> | <costs/risks> |
| B | <option> | <strengths> | <costs/risks> |

### Recommendation

State the recommended path.

### Rationale

Explain why this recommendation best fits the contract, accepted decisions,
evidence, risk posture and current workflow phase.

### Human Acceptance Question

State the exact question the human must answer for this decision.

## Aggregate Recommendation

State which decisions must be accepted before the workflow may leave the current
human-mediated gate, and which decisions, if any, may be deferred with explicit
residual risk.

## Evidence

- <artifact path or evidence source>

## Freshness / Revisit Triggers

- dependency major version changed
- failed verification gate
- reviewer flags drift
- new requirement invalidates assumption

## Rollback / Migration Notes

Describe how to undo the selected design path if it proves wrong.
