# ADR-0009: Actor Model, Verification Instruments, and Fusion Semantics

## Status

Accepted.

## Context

AgentsFlow now distinguishes planning, implementation, verification, review,
finding validation, and fusion. Without a clearer actor model, roles can blur:
review agents might start acting like verification gates, fusion might become an
implicit orchestrator, and planning might be misread as a default delegated
Planning Agent.

## Decision

AgentsFlow defines actor roles as workflow protocol roles, not new top-level
building blocks.

Current workflows treat planning as a human-guided phase coordinated by the
main/orchestrating agent. `Planning Agent` is reserved as an optional future role,
like `Implementation Agent`.

Verification Gate is defined broadly as a workflow-defined evidence-producing
control point. It may run tests, deterministic scripts, static analysis, dynamic
analysis, debuggers, trace/log/network analysis tools, profilers, fuzzers,
benchmarks, security scanners, and other verification instruments declared by the
workflow/profile.

Review agents are read-only by default. They may receive explicit, scoped tool
exceptions only when the workflow, reviewer manifest, or prompt says so. Such
observations remain candidate findings and do not replace verification evidence.

Fusion Agent is a read-only synthesis actor by default. It does not launch
reviewers, run gates, run tests, or modify artifacts. It may request or recommend
additional review/verification, but orchestration remains with the main agent.

## Consequences

AgentsFlow avoids becoming a multi-agent runtime with unclear permissions. The
main/orchestrating agent remains responsible for orchestration, while gates,
reviewers, and fusion stages have bounded responsibilities.

Future work may introduce explicit Planning Agent or Implementation Agent
protocols, but current workflows must not assume them as default actors.
