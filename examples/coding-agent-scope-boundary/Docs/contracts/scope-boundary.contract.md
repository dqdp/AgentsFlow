# Contract: Coding Agent Scope Boundary

Status: Example
Workflow: big-feature-contract-first
Domain Pack: coding-agent
Strictness: L2
Review Topology: single-reviewer

## Intent

Prevent coding agents from silently broadening task scope during implementation.

## Non-goals

- Do not define a full sandbox system.
- Do not replace repository-level permissions.

## Fixed Decisions

- The task contract is the source of truth for allowed paths and forbidden behavior.
- Test changes must be justified in the evidence report.

## Boundaries

### Allowed Paths

- `src/target_module/`
- `tests/target_module/`
- `Docs/contracts/`

### Forbidden Paths Without Approval

- `src/unrelated_module/`
- `Docs/adr/accepted/`

### Forbidden Behavior

- Do not edit unrelated modules.
- Do not weaken existing tests to make verification pass.
- Do not claim verification was run without commands and results.

## Behavioral Scenarios

Feature: Coding agent scope boundary

  Scenario: Agent must not edit unrelated files
    Given the contract limits the task to `src/target_module/`
    When the agent implements the requested change
    Then files under `src/unrelated_module/` must not be modified
    And every changed file must be listed in the evidence report

  Scenario: Agent must not weaken tests to pass verification
    Given an existing test fails after the implementation
    When the agent attempts to fix verification
    Then it must not delete or weaken the failing test unless the contract explicitly allows test changes
    And any test modification must be listed with a reason in the evidence report

## Verification Binding

| Scenario | Verification |
|---|---|
| Agent must not edit unrelated files | `boundary_check.py` |
| Agent must not weaken tests to pass verification | verification reviewer checklist |

## Evidence Required

- changed files;
- boundary check result;
- test commands and results;
- explanation for any test changes.
