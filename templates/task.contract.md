# Contract: <task-or-feature-name>

Status: Draft
Workflow: <workflow-name>
Domain Pack: <domain-pack>
Strictness: <L0-L4>
Review Topology: <none|single-reviewer|triad-fusion|multi-model-fusion>

## Intent

Describe what this task is trying to achieve and why it matters.

## Non-goals

List what is explicitly out of scope.

## Fixed Decisions

List accepted ADRs, prior decisions, or constraints that must not be changed without explicit approval.

## Assumptions

List assumptions that the implementer may rely on.

## Boundaries

### Allowed Paths

- `src/<module>/**`
- `tests/<module>/**`

### Forbidden Paths Without Approval

- `Docs/adr/accepted/**`
- `src/unrelated/**`

### Forbidden Behavior

- Do not replace accepted architecture.
- Do not weaken existing tests to make verification pass.
- Do not introduce unrelated refactors.

## Behavioral Scenarios

```gherkin
Feature: <feature-name>

  Scenario: <concrete behavior>
    Given <initial state>
    When <event/action>
    Then <observable result>
    And <evidence or forbidden behavior>
```

## Verification Binding

Map scenarios to checks:

| Scenario | Verification |
|---|---|
| Scenario name | `pytest tests/...`, trace assertion, boundary check, review checklist |

## Evidence Required

The final evidence report must include:

- changed files;
- scenario coverage;
- commands run and results;
- boundary check result;
- impact map result;
- review/fusion result if applicable;
- known limitations.

## Open Questions

- ...

## Hidden Regression Candidates

List behavior that should eventually become hidden regression cases.
