# Specification / Plan Mode

## Decision

AgentsFlow treats Specification / Plan Mode as a reusable phase pattern, not as a new top-level abstraction and not as a single global workflow.

A workflow may include this phase pattern with different depth depending on
workflow type, workflow default strictness, project risk and domain pack.

## Native model

Specification / Plan Mode is composed from existing AgentsFlow primitives:

- workflow phases;
- skills;
- scripts;
- templates;
- artifacts;
- gates;
- profiles.

It introduces no new top-level abstraction.

## Read-only planning rule

Planning agents are read-only.

They may inspect context, read repository files, ask questions, draft specs, compare options, and produce plans. They must not modify implementation files, run implementation steps, or silently switch into implementation.

## Minimal phase chain

```text
problem framing
→ repository grounding / research
→ requirements / behavior spec
→ technical plan
→ task decomposition
→ plan gate
→ implementation
```

## Common artifacts

- problem frame;
- repository grounding report;
- research brief;
- requirements / bugfix spec;
- design spec;
- technical plan;
- task breakdown;
- decision contract;
- term map;
- target system spec;
- enabling system spec;
- plan gate report.

## Plan gate

A plan gate validates that a plan is:

- grounded in repository/project evidence;
- scoped;
- consistent with accepted ADRs;
- testable;
- tied to verification commands or checks;
- explicit about non-goals and forbidden scope;
- safe to hand to an implementation agent.

A plan gate does not implement.

## Workflow binding

- `new-project-spec-first`: reference/next deep specification stack.
- `big-feature-contract-first`: plan gate required when effective strictness
  includes the plan-gate depth, inherited from the workflow default unless
  explicitly overridden.
- `agentic-system-hardening`: behavior/prompt/tool/policy planning required.
- `prompt-behavior-eval`: eval scenarios before prompt changes.
- `safe-refactor`: refactor boundary and rollback plan required.
- `bugfix-regression-capture`: reference/next lightweight diagnosis and regression plan.
- `research-to-ADR`: frame / explore / compare / decide / verify.
- `review-only-fusion`: v0.2 utility that reviews existing plans/specs/evidence only.

## haft / quint code relation

AgentsFlow may use haft/quint code as an optional external advanced planning provider. AgentsFlow does not reimplement haft in core.

Native AgentsFlow remains lightweight. External advanced planning providers must map their outputs back into AgentsFlow artifacts.

## Planning actor note

Specification / Plan Mode is a reusable phase pattern, not a requirement to use a
separate Planning Agent. Current AgentsFlow workflows model planning as a
human-guided phase coordinated by the main/orchestrating agent.

`Planning Agent` remains a reserved optional future actor for cases where planning,
research, or external planning-provider integration is delegated explicitly.
