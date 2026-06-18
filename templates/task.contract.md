# Contract: <task-or-feature-name>

Status: Draft
Workflow: <workflow-name>
Domain Pack: <domain-pack>
Strictness: <L0-L4>
Review Topology: <none|homogeneous-dual|homogeneous-plus-focused|heterogeneous-variable>
Target Workflow: <workflow-name>

## Intent

Describe what this task is trying to achieve and why it matters.

## Operating Context Preflight

| Item | Required? | Source | Status | Blocking code / notes |
|---|---:|---|---|---|
| Project binding or accepted project policy | yes | `.agentsflow/` or project decision | present/missing | `needs-project-binding` |
| Verification gate binding and runner | yes | `.agentsflow/gates/*` | present/missing | `needs-verification-gate` |
| Review policy and reviewer count | yes | project operating decisions / binding | present/missing | `needs-review-policy` |
| Evidence and run artifact location | yes | project policy / binding | present/missing | `needs-evidence-location` |
| Red-capture applicability | implementation workflows only | contract / binding | required/not-required | `needs-red-capture-policy` |
| Human authority / approval boundaries | yes | project operating decisions / accepted decision packet | present/missing | `needs-human-authority-decision` |
| Human final acceptance policy | policy-defined | project operating decisions | required/not-required | `needs-human-authority-decision` when required but missing |

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

Questions are classified before asking the human. Blocking questions pause the
workflow; nonblocking questions use a recorded default when one is allowed.

| ID | Question | Classification | Default | Answer required before implementation? | Decision / status | Affected artifacts |
|---|---|---|---|---:|---|---|
| Q-001 | ... | blocking-material / nonblocking-follow-up / nonblocking-known-limitation / out-of-scope | ... | yes/no | open/confirmed/unresolved; defaulted only for nonblocking classifications with an allowed default | ... |

## Grouped Decision Packet

When human input is needed, the main agent asks one grouped decision prompt:
blocking-material questions first, then nonblocking questions with proposed
defaults. The agent records answers in `human-decisions.yaml` and updates this
contract instead of asking the human to fill structured files by hand.

## Hidden Regression Candidates

List behavior that should eventually become hidden regression cases.
