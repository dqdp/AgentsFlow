# Task Contract Model

A task contract is the source of truth for a specific task, feature, refactor, or hardening effort.

It usually lives in the target project:

```text
Docs/contracts/<name>.contract.md
```

or:

```text
Docs/specs/<name>.contract.md
```

## Required sections

- `Intent`
- `Fixed Decisions`
- `Boundaries`
- `Behavioral Scenarios`
- `Verification Binding`
- `Evidence Required`

## Recommended sections

- `Non-goals`
- `Assumptions`
- `Open Questions`
- `Risk Notes`
- `Hidden Regression Candidates`

## Contract authority

A contract constrains implementation and review. Review agents should check whether the work satisfies the contract, not invent unrelated preferences.

When the contract is wrong or incomplete, the correct behavior is to propose a contract change, not silently implement outside it.

## BDD scenarios

Scenarios should focus on observable behavior and forbidden behavior.

Prefer:

```gherkin
Scenario: Agent must not weaken tests to make verification pass
  Given an existing test fails after the implementation
  When the agent attempts to fix the verification failure
  Then it must not delete or weaken the failing test unless the contract explicitly allows test changes
  And any test modification must be listed in the evidence report
```

Avoid:

```gherkin
Scenario: Agent handles things properly
  Then everything should work
```

## Behavior bindings

A task contract may contain BDD/Gherkin scenarios, but required acceptance
scenarios are not considered executable unless they are mapped to checks in a
`*.bindings.yaml` behavior binding manifest.

The contract may include a human-readable binding summary, but the YAML binding
manifest is the automation source of truth.
