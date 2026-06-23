# Plan Gate Report

Default authority mode: `deterministic_gate`.

This report checks whether the plan packet is grounded, scoped and ready for the
next declared workflow step. If the workflow requires reviewer evaluation plus
human approval of the plan, record that as a separate `human_mediated_gate` or as
explicitly declared required evidence; do not imply it happened merely because
the plan gate passed.

## Plan Under Review

## Inputs Checked

- problem frame:
- repository grounding report:
- accepted ADRs:
- task contract:
- plan:
- task breakdown:

## Checks

| Check | Result | Evidence |
|-------|--------|----------|
| scope is explicit | | |
| non-goals are explicit | | |
| repository grounding exists | | |
| ADR consistency checked | | |
| tests/checks planned | | |
| rollback or revisit path described | | |

## Decision

- pass
- pass-with-notes
- needs-changes
- needs-human-decision

## Blocking Issues

## Notes
