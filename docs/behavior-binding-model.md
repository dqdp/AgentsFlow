# Behavior Binding Model

## Status

Accepted in v0.1.8.

## Purpose

BDD/Gherkin scenarios are the human-readable behavior specification layer.
They describe what must be true, but they are not executable gates by themselves.

AgentsFlow therefore uses **behavior binding manifests** to connect required
behavior scenarios to executable checks. The gate runner consumes those bindings
and reports whether the required scenario checks ran and produced evidence.

## Core rule

```text
BDD scenario defines expected behavior.
Behavior binding maps the behavior to executable checks.
Gate runner executes or validates the checks.
Evidence report proves what happened.
```

## Canonical artifact

The canonical machine-readable artifact is:

```text
*.bindings.yaml
```

Contracts may include a human-readable verification-binding summary, but YAML
bindings are the source of truth for automation.

## Required vs specification-only scenarios

Not every scenario must be executable immediately.

```yaml
required: true
```

means the scenario is an acceptance requirement and must be bound to one or more
executable checks.

```yaml
required: false
status: specification-only
```

means the scenario is a useful specification or future coverage candidate, but
it does not block the current workflow by default.

Workflow profiles may strengthen this rule, for example:

```text
L3/L4: all P0/P1 acceptance scenarios must have executable bindings.
```

## Binding shape

```yaml
version: 1
contract: task.contract.md
bindings:
  - id: AF-BHV-001
    scenario: "Agent must not modify unrelated files"
    required: true
    source:
      type: contract
      path: task.contract.md
      section: Behavioral Scenarios
    checks:
      - id: boundary-check
        type: script
        command: "python3 scripts/boundary_check.py --contract task.contract.md --changed-files changed-files.txt"
        evidence:
          - boundary-check-report
    gates:
      - verification_gate
```

## Check types

Behavior bindings may point to:

- tests;
- deterministic scripts;
- BDD/scenario runners;
- eval runners;
- trace assertions;
- log assertions;
- static analysis;
- dynamic analysis;
- benchmarks;
- security scanners;
- manual evidence checks;
- external tools.

Gate instrument types and behavior-binding check types use the same vocabulary
where possible. When a gate manifest uses a broader instrument class, map it to a
binding check type as follows:

| Gate instrument type | Behavior-binding check type |
|---|---|
| `tests` or `test` | `test` |
| `deterministic_script` or `script` | `script` |
| `bdd_runner` | `bdd_runner` |
| `eval` or `eval_runner` | `eval` |
| `trace_assertion` | `trace_assertion` |
| `log_assertion` | `log_assertion` |
| `static_analysis` | `static_analysis` |
| `dynamic_analysis` | `dynamic_analysis` |
| `benchmark` | `benchmark` |
| `security_scan` | `security_scan` |
| `manual_evidence` | `manual_evidence` |
| `external_tool` | `external_tool` |

Manual evidence is allowed only if the gate runner can deterministically check
that the required artifact exists and is referenced in the gate report.

## Gate behavior

A verification gate consuming behavior bindings must check that:

- all required scenarios have at least one binding;
- each binding has at least one executable check or manual evidence requirement;
- required bound checks are reported in the evidence bundle;
- missing required bindings fail or block according to the workflow policy;
- optional unbound scenarios are reported as warnings, not silently ignored.

## Red/green evidence (failing-run / passing-run pair)

For any behavior bound to an implementation phase, the evidence bundle must record a
failing run (red) captured before implementation and a passing run (green) captured
after, for the same bound check. `validate_repo.py` enforces the workflow phase
topology that makes this evidence pair mandatory by structure. The future
`redgreen_check` gate runner will confirm that the failing-then-passing pair is
present in concrete run artifacts. This model is the canonical home for the
`failing_run` / `passing_run` evidence pair introduced by
`docs/adr/ADR-0017-test-framed-implementation-phase.md`, which refines ADR-0010
(gate executability) and ADR-0011 (behavior binding).

## Non-goal

Behavior bindings are not intended to become a heavy test-management system in
v0.2. The minimal implementation is one template, one schema, one checker, and
integration with gate reports. Recording a failing-run/passing-run pair per ADR-0017
is part of this minimal footprint, not a test-management system: it is a structural
byproduct of the test-framed implementation phase and adds no authoring surface
beyond the existing template, schema, checker and gate-report integration.
