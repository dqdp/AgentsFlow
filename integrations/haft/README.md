# haft / quint code Integration

Status: optional advanced planning provider, not a core dependency.

AgentsFlow may use haft/quint code for high-risk planning and decision engineering.

## When to use

Use haft-like planning when a workflow needs deeper decision support:

- major architecture choice;
- new project foundation;
- high-risk agent runtime or policy decision;
- large refactor with expensive rollback;
- conflicting requirements;
- long-lived ADRs with freshness concerns.

Do not use for small bugfixes, obvious refactors, or tasks already constrained by accepted ADRs.

## Mapping to AgentsFlow artifacts

haft-style outputs should be mapped to AgentsFlow artifacts:

```text
problem frame         → problem-frame.md / research-brief.md
option comparison     → decision-contract.md
chosen decision       → ADR draft / decision-contract.md
verification evidence → evidence-summary.md
plan                  → plan.md
task decomposition    → task-breakdown.md
```

## Design rule

AgentsFlow borrows selected ideas from haft but does not reimplement the full governance runtime in core.
