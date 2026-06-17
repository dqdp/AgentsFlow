# ADR-0010: Gate Executability Rule

## Status

Accepted

## Context

AgentsFlow uses gates as control points in workflows. If a gate is only described
in prose or BDD, the decision about whether it passed becomes a model judgment.
That conflicts with the separation between verification, review and fusion.

## Decision

Every concrete gate included in an AgentsFlow workflow must have a deterministic
runner entrypoint.

BDD scenarios, contracts and prose specifications may define what must be checked,
but they are not executable gates by themselves.

A gate runner may orchestrate tests, scripts, BDD runners, static analysis,
dynamic analysis, debuggers, profilers, fuzzers, network traffic analyzers,
benchmarks, security scanners or custom domain tools.

Each runner must produce structured evidence and a gate report with explicit
result states: `pass`, `pass_with_notes`, `fail`, `inconclusive`,
`needs_human_decision`, or `blocked`.

## Consequences

- Workflows reference gate manifests rather than informal gate names.
- Gate manifests live under `gates/`.
- Gate runners live under `scripts/gates/` or another explicitly declared path.
- `validate_repo.py` validates gate references and runner existence.
- Review agents and fusion agents consume gate reports; they do not substitute
  for executable gates.
- BDD scenarios must be bound to tests/evals/checks/instruments before they can
  serve as gate evidence.
- Refined by ADR-0017: an implementation phase must be framed by a red-capture
  (pre) and green-verify (post) phase, so the failing-then-passing run pair becomes
  gate evidence by construction rather than a self-certified always-green test.
