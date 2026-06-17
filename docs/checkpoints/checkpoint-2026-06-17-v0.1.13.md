# Checkpoint: AgentsFlow v0.1.13

## Purpose

v0.1.13 records the final pre-handoff MVP boundary decisions and updates the repository to reflect them consistently.

## Accepted decisions recorded in this checkpoint

### v0.2 MVP boundary

Application workflow:

```text
project-initialization
```

MVP user workflows:

```text
big-feature-contract-first
bugfix-regression-capture
review-only-fusion
new-project-spec-first
```

Non-MVP workflows remain reference/experimental and schema-valid only:

```text
agentic-system-hardening
prompt-behavior-eval
safe-refactor
research-to-ADR
```

### Primary e2e example

The primary v0.2 end-to-end example is:

```text
examples/e2e/minimal-python-project/
```

C++/CMake is not the primary e2e in v0.2.

### CMake support depth

CMake FetchContent / FetchPackage-style support is a documented pattern/skeleton only in v0.2. A full CMake package or complete CMake e2e example is out of scope.

### Claude external reviewer provider

Claude Code external reviewer provider is in v0.2 MVP scope.

Strict policy:

```text
Claude Code CLI only
subscription-local only
API-key usage forbidden
ANTHROPIC_API_KEY => fail fast
```

The MVP implementation is a minimal project-bound wrapper that accepts a review packet, invokes/normalizes a Claude reviewer, stores raw output, normalized reviewer report and invocation metadata, and marks all findings as candidate/unvalidated.

### Documentation / language policy

Repository docs are primarily English. Russian handoff prompts are allowed outside normal repository docs or in explicitly marked handoff artifacts.

### Legacy adoption default

Default legacy adoption mode for existing projects is `knowledge-extraction`. `minimal-patch-adapt` is rare, strict and human-approved only.

### Project initialization permissions

Default project initialization mode is:

```text
scan-only + draft-overlay
```

No automatic rewrite of `AGENTS.md` or active migration without human approval.

### Workflow run artifacts

Workflow run artifacts live under:

```text
Docs/agentsflow/runs/
```

Reports and summaries should be committed. Heavy raw logs are optional and may be gitignored.

### Schema strictness

Strict schemas are required for core artifacts only:

```text
workflow
gate
project binding
behavior binding
reviewer report
fusion report
workflow run metadata
```

Exploratory assessments may remain more permissive.

### Script / validator baseline

Python validators with modest dependencies are accepted for v0.2. No full CLI/package distribution is required.

## v0.2 Definition of Done

AgentsFlow v0.2 is done when:

- repository validation passes;
- tests pass;
- MVP workflows are schema-valid;
- project-initialization path is coherent;
- project overlay model is represented;
- project-bound gates are represented;
- behavior bindings are represented;
- legacy adoption is represented;
- Claude external reviewer provider minimally works in subscription-local mode;
- one e2e example exists;
- `AGENTS.md` is usable by coding agents;
- non-MVP workflows remain reference/experimental and schema-valid only.

## Added / changed in v0.1.13

- `README.md` rewritten around the v0.2 MVP boundary.
- `AGENTS.md` rewritten as a coding-agent handoff policy.
- `docs/mvp-ready-workflow-standard.md` updated with v0.2 DoD.
- `docs/workflow-taxonomy.md` updated with MVP/reference statuses.
- `docs/cmake-fetchcontent-application-pattern.md` added.
- `schemas/reviewer-report.schema.json` added.
- `scripts/reviewers/run_external_reviewer.py` added.
- `scripts/reviewers/providers/claude_code.py` added.
- `examples/e2e/minimal-python-project/` added as the primary e2e shape.
- `examples/external-reviewers/claude-code/` updated from planned shape to MVP wrapper example.
- `docs/retrospectives/documentation-consistency-review-2026-06-17-v0.1.13.md` added.

## Handoff rule

Coding agents should follow this directive:

```text
Do not expand scope.
Implement accepted decisions.
Make AgentsFlow usable for the v0.2 MVP path.
```
