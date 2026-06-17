# Risk and Strictness Profiles

Strictness is a profile parameter, not the main abstraction.

The workflow defines what type of work is being done. Strictness controls how deep gates, review, and evidence should go.

## Levels

| Level | Name | Typical use |
|---|---|---|
| L0 | lightweight | Small low-risk changes. |
| L1 | controlled | Scoped changes with boundaries and evidence. |
| L2 | contract | Contract-first work with BDD scenarios and impact map. |
| L3 | reviewed | Independent review agents and fusion summary. |
| L4 | critical | Adversarial review, hidden regressions, scenario simulation, human decision points. |

## Risk signals

Increase strictness when work touches:

- architecture decisions;
- memory/policy/tool permissions;
- system prompts;
- safety boundaries;
- public APIs;
- persistence or migrations;
- low-latency/hot-path code;
- authentication/authorization;
- irreversible operations.

## Anti-overload rule

Do not use L3/L4 by default. Heavy gates should be justified by risk.

## Test-framed implementation is not strictness-scaled

The red-before/green-after discipline (ADR-0017) is not an L3/L4-only behavior. It
applies whenever a workflow has a `kind: implementation` phase, independent of the
strictness level.
