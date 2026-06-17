# Contract: Memory Policy Behavior

Status: Example
Workflow: agentic-system-hardening
Domain Pack: agentic-system
Strictness: L2
Review Topology: single-reviewer

## Intent

Ensure the assistant writes long-term memory only when policy allows it, and that memory decisions are observable in evidence or trace.

## Non-goals

- Do not replace the memory backend.
- Do not redesign the whole agent runtime.
- Do not introduce unrelated prompt changes.

## Fixed Decisions

- Long-term memory decisions are policy-mediated.
- Memory behavior must be testable through scenarios or trace assertions.
- Accepted ADRs must not be changed by this task.

## Assumptions

- The runtime can record a memory decision such as `allow`, `skip`, or `reject`.
- The assistant response can be checked for claims such as “I will remember that.”

## Boundaries

### Allowed Paths

- `src/memory/`
- `src/policy/`
- `tests/memory/`
- `tests/policy/`
- `Docs/contracts/`

### Forbidden Paths Without Approval

- `Docs/adr/accepted/`
- `src/model_router/`
- `src/tools/`

### Forbidden Behavior

- Do not store sensitive inferred attributes without explicit user request.
- Do not claim that memory was stored when policy skipped or rejected it.
- Do not bypass policy for convenience.

## Behavioral Scenarios

Feature: Memory write policy

  Scenario: Temporary facts are not stored
    Given the user casually mentions a short-lived fact
    When the assistant evaluates memory write eligibility
    Then the fact must not be persisted
    And the trace must contain memory_decision="skip"

  Scenario: Explicit memory request is routed through policy
    Given the user says "remember that I prefer Russian prompts"
    When the assistant evaluates memory write eligibility
    Then the memory proposal must be sent to the policy layer
    And the trace must contain memory_decision="allow"

  Scenario: Sensitive inferred attributes require explicit user request
    Given the assistant infers a sensitive personal attribute
    When the memory subsystem proposes a long-term write
    Then the policy layer must reject the write
    And the assistant response must not claim that the fact was remembered

## Verification Binding

| Scenario | Verification |
|---|---|
| Temporary facts are not stored | `tests/memory/test_memory_policy.py::test_temporary_fact_skipped` |
| Explicit memory request is routed through policy | `tests/policy/test_memory_write_policy.py::test_explicit_request_policy_allow` |
| Sensitive inferred attributes require explicit user request | `tests/policy/test_memory_write_policy.py::test_sensitive_inferred_rejected` |

## Evidence Required

The final evidence report must include:

- changed files;
- scenario coverage;
- commands run and results;
- boundary check result;
- known limitations.

## Open Questions

- Should memory decisions be represented as trace fields, event-envelope metadata, or both?

## Hidden Regression Candidates

- Assistant claims “I will remember that” when the memory decision is `skip`.
- Agent bypasses policy for explicit memory requests.
