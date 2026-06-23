# ADR-0011: Behavior Binding Rule

## Status

Accepted.

## Context

AgentsFlow uses BDD/Gherkin scenarios as a human-readable behavior layer. But a
scenario is not an executable check. Without a binding, a contract may claim a
behavior is required while no deterministic test, eval, script or evidence check
actually verifies it.

## Decision

BDD/Gherkin scenarios are behavior specifications, not executable gates.

Any scenario required for acceptance must be bound to one or more executable
checks through a machine-readable behavior binding manifest.

The canonical binding format is `*.bindings.yaml`.

Gate runners consume binding manifests and must report whether required scenario
checks were executed and evidenced.

Contracts may include human-readable binding summaries, but YAML bindings are the
source of truth for automation.

## Consequences

- BDD remains lightweight and human-readable.
- Required behavior becomes traceable to executable checks.
- Review agents can distinguish specification-only scenarios from verified acceptance scenarios.
- Gate reports can identify missing required bindings as failures, blockers or inconclusive results according to workflow policy.
- Refined by ADR-0017: scenarios bound to test-type checks must be exercised by a captured failing run before implementation and a passing run after, so a required binding is evidenced as a red→green pair, not a single green run.
