# Risk and Strictness

Strictness is a workflow depth control, not the main abstraction.

The workflow defines what type of work is being done and declares its
`default_strictness`. Project bindings and workflow runs use the workflow default
unless they explicitly record a `strictness_override` with a reason.

The effective strictness controls how deep gates, review, and evidence should go
for one concrete binding or run.

## Default and Override

```text
workflow.default_strictness
  baseline depth for the workflow's normal use

binding.strictness
  optional project-level override

run.strictness
  recorded effective value for a concrete run
```

An override is appropriate only when the project risk, pilot scope, regulatory
context or task constraints differ materially from the workflow default.

## Current Compatibility Levels

| Level | Name | Typical use |
|---|---|---|
| L0 | lightweight | Small low-risk changes. |
| L1 | controlled | Scoped changes with boundaries and evidence. |
| L2 | contract | Contract-first work with BDD scenarios and impact map. |
| L3 | reviewed | Independent review agents and fusion summary. |
| L4 | critical | Adversarial review, hidden regressions, scenario simulation, human decision points. |

These `L*` labels are compatibility identifiers, not a requirement that
AgentsFlow must keep five meaningful modes forever. A future slice may collapse
the taxonomy to two or three project-facing levels, as long as workflow defaults,
effective strictness and override reasons remain explicit.

## Risk signals

Override upward when work touches:

- architecture decisions;
- memory/policy/tool permissions;
- system prompts;
- safety boundaries;
- public APIs;
- persistence or migrations;
- low-latency/hot-path code;
- authentication/authorization;
- irreversible operations.

Override downward only for bounded pilots, examples, fixtures or deliberately
reduced-scope work, and record the reason.

## Anti-overload rule

Do not ask the human to choose a heavy profile as routine setup. The workflow
default should already encode normal risk. Heavy overrides should be justified by
specific project or task evidence.

## Test-framed implementation is not strictness-scaled

The red-before/green-after discipline (ADR-0017) is not an L3/L4-only behavior. It
applies whenever a workflow has a `kind: implementation` phase, independent of the
effective strictness.
