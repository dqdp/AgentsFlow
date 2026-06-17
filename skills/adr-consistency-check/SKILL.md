# Skill: adr-consistency-check

## Purpose

Check whether a plan, contract, or diff preserves accepted ADR decisions.

## Inputs

- `artifact`
- `relevant_adrs`
- `domain_pack`


## Outputs

- `adr_consistency_notes`
- `violations`
- `decision_change_requests`


## Procedure

1. List relevant ADRs.
2. Extract fixed decisions.
3. Compare artifact against decisions.
4. Flag drift and competing architectures.
5. Require explicit approval for ADR changes.


## Quality bar

- ADR violations are specific and cited by file/decision.
- Unclear cases are marked for human decision.


## Anti-patterns

- Treating accepted ADRs as suggestions.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.
