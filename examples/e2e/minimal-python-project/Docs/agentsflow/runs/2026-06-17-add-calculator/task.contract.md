# Task Contract: Add integer addition behavior

## Intent

Provide a minimal calculator addition behavior.

## Boundaries

Allowed:
- `src/minicalc/**`
- `tests/**`

Forbidden without approval:
- unrelated package metadata changes
- network or filesystem side effects

## Behavioral Scenarios

Scenario: Add two integers
  Given inputs 2 and 3
  When the addition function is called
  Then the result must be 5
