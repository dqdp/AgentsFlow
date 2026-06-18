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
- `Operating Context Preflight`
- `Open Questions`
- `Risk Notes`
- `Hidden Regression Candidates`

## Contract authority

A contract constrains implementation and review. Review agents should check whether the work satisfies the contract, not invent unrelated preferences.

When the contract is wrong or incomplete, the correct behavior is to propose a contract change, not silently implement outside it.

## Operating context preflight

For implementation workflows, the task contract should record whether enough
project context exists to run the workflow safely. A project may have completed
`project-initialization`, may be partly initialized, or may have been developed
with AgentsFlow from the start; the requirement is sufficient operating context,
not a mandatory prior onboarding run.

The preflight should identify concrete blockers such as:

```text
needs-project-binding
needs-verification-gate
needs-review-policy
needs-evidence-location
needs-red-capture-policy
needs-human-authority-decision
```

Unresolved blockers pause the workflow before implementation. Missing optional
or advisory context is recorded as a nonblocking known limitation or follow-up.

## Open questions

Open questions are not all equivalent. Each question must be classified before
the main/orchestrating agent decides whether to ask the human or proceed with a
default:

| Classification | Meaning | Default behavior |
|---|---|---|
| `blocking-material` | The answer can change scope, contract, gate policy, authority, evidence requirements, safety/compliance posture or accepted decisions. | Pause and ask the human. |
| `nonblocking-follow-up` | Useful later, but not required for the current acceptance decision. | Record follow-up; do not pause by default. |
| `nonblocking-known-limitation` | Current work can proceed with a stated limitation. | Record limitation and allowed default. |
| `out-of-scope` | The question belongs outside the current task. | Record as out of scope; do not pause. |

When multiple questions need human input, the main agent groups them into one
decision prompt: blocking-material questions first, then nonblocking questions
with proposed defaults. Answers are recorded in `human-decisions.yaml` and
reflected back into the task contract.

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
