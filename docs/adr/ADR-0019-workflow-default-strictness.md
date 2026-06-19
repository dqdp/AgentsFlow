# ADR-0019: Workflow Default Strictness

## Status

Proposed.

Date: 2026-06-19

## Context

AgentsFlow has used `strictness` as a profile parameter that can be set in a
project workflow binding or workflow run. In practice this can push the human or
main agent toward choosing an artificial process mode for every run, even when
the workflow itself already implies the normal amount of planning, evidence,
review and human decision control.

This is a workflow stability risk. If `big-feature-contract-first` normally
needs deeper planning than `bugfix-regression-capture`, that should be declared
by the workflow rather than rediscovered during each project initialization or
feature discussion.

The current `L*` identifiers are also more numerous than the project may need
long term. The valuable distinction is not the exact number of labels; it is
whether the effective gate/review/evidence depth is explicit and reviewable.

## Proposed Decision

If accepted, every workflow that uses strictness-sensitive behavior should
declare:

```yaml
default_strictness: L3
```

Project workflow bindings inherit this value by default. A binding or run may
set `strictness` only as an explicit override and should record:

```yaml
strictness_source: project_override
strictness_override_reason: "Why this project/run differs from the workflow default."
```

The effective strictness is computed as:

```text
binding/run strictness override if present
else workflow.default_strictness
```

Conditional phases and gates that use `applies_to_strictness` are evaluated
against the effective strictness.

The main/orchestrating agent should not ask the human to choose an `L*` level as
a routine setup question. It should inherit the workflow default and ask only
when observed project risk, pilot scope or task constraints suggest a material
override.

## Compact Taxonomy Direction

This ADR does not require keeping five project-facing levels forever. v0.2 may
remain compatible with the current `L*` identifiers while a future slice decides
whether to collapse them into a smaller taxonomy, for example:

```text
standard
elevated
critical
```

The taxonomy can change without changing the core model:

```text
workflow default -> effective strictness -> conditional gate/review depth
```

## Consequences If Accepted

- Workflow selection carries more process meaning by default.
- Project initialization has fewer routine questions for the human.
- Strictness changes become explicit design decisions with reasons.
- Fixtures and pilots can still use lighter depth, but must not overclaim
  evidence that the lighter path did not produce.
- Phase transition control can consume effective strictness without inventing
  extra gates or hidden review phases.

## Alternatives Considered

### Keep strictness as a routine project-binding choice

Rejected as the default direction. It makes workflow execution depend too much
on prompt discipline and repeated human choices.

### Make every workflow support every strictness level equally

Rejected. That creates artificial mode matrices and weakens the meaning of a
workflow.

### Collapse the taxonomy immediately

Deferred. The existing schemas, validators, examples and tests currently use
`L*` identifiers. Collapsing them should be a separate migration with explicit
compatibility handling.

## Open Questions

- Which compact taxonomy should replace or alias the current `L*` labels, if
  any?
- Should future schemas forbid `strictness_source: workflow_default` together
  with a local `strictness` value unless the value matches the workflow default?
- Should project initialization record a project-wide strictness override policy
  or only per-workflow binding overrides?
