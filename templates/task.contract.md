# Contract: <task-or-feature-name>

Status: Draft
Workflow: <workflow-name>
Domain Pack: <domain-pack>
Effective Strictness: <workflow-default-or-explicit-override>
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

## Risk Surface Profile

Select only surfaces that materially affect this feature. Use the upstream
catalog in `docs/risk-and-strictness.md` unless the project overlay defines a
project-local surface.

| Risk surface | Why selected | Required path classes | Coverage status | Review impact |
|---|---|---|---|---|
| `authority_boundary` | ... | `valid_delegation`, `malformed_request`, `direct_bypass_attempt` | bound/deferred/not-applicable | homogeneous-dual/focused/heterogeneous |

## Failure Path Matrix

Required when selected risk surfaces include denial, failure, timeout, rejection,
persistence or authority semantics.

| ID | Risk surface | Path class | Trigger | Expected authority | Expected context/state | Expected audit/persistence | Must not happen | Evidence binding |
|---|---|---|---|---|---|---|---|---|
| FPM-001 | `audit_persistence` | `denied_attempt_persisted` | ... | ... | ... | ... | silent deny without durable evidence | `AF-BHV-...` / gate check / approved deferral |

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

| Scenario | Risk surface | Path class | Verification |
|---|---|---|---|
| Scenario name | `audit_persistence` | `denied_attempt_persisted` | `pytest tests/...`, trace assertion, boundary check, review checklist |

## Audit and Persistence Contract

Fill this when `audit_persistence` or `persistence_consistency` is selected.

| Item | Decision |
|---|---|
| Event or attempt recorded | ... |
| Write timing relative to side effect | before/with/after/not-applicable |
| Denied/rejected/timeout/downstream-failure paths recorded | yes/no/details |
| Correlation id / run id | ... |
| Redacted or omitted fields | ... |
| Read-back / consistency evidence | ... |

## Evidence Required

The final evidence report must include:

- changed files;
- scenario coverage;
- risk surface and Failure Path Matrix coverage when selected;
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
