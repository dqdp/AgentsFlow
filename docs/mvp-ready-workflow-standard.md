# MVP-Ready Workflow Standard

## Status

Accepted for AgentsFlow v0.2 and updated in v0.1.13.

## v0.2 MVP scope

AgentsFlow v0.2 has one mandatory application/onboarding workflow and four MVP user workflows.

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

Non-MVP workflows remain in the repository as reference/experimental workflows and must remain schema-valid only:

```text
agentic-system-hardening
prompt-behavior-eval
safe-refactor
research-to-ADR
```

## MVP-ready definition

A workflow is MVP-ready when it is not just a prose idea but a reproducible workflow definition usable by a main/orchestrating agent and a human.

Each MVP workflow must have:

- validated `workflow.yaml`;
- explicit phase sequence;
- declared inputs and outputs;
- declared artifact templates;
- referenced upstream gate contracts;
- deterministic gate runner interface and project-binding requirements;
- review-cycle policy where applicable;
- behavior bindings for required acceptance scenarios where applicable;
- at least one validated example or project-overlay example;
- repo-validation coverage;
- for workflows with an implementation phase, a red-capture (failing-test) phase before implementation and a green-verify phase after it (ADR-0017).

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
- Claude Code external reviewer provider minimally works in subscription-local mode;
- one end-to-end example exists under `examples/e2e/minimal-python-project/`;
- `AGENTS.md` is usable by coding agents;
- non-MVP workflows remain reference/experimental and schema-valid only.

## Primary e2e example

The primary v0.2 end-to-end example is:

```text
examples/e2e/minimal-python-project/
```

CMake FetchContent / FetchPackage-style usage is documented as a pattern/skeleton only in v0.2. A complete CMake e2e example is not part of the MVP.

## Claude external reviewer provider requirement

The Claude provider is in v0.2 MVP scope, but narrowly:

- Claude Code CLI only;
- subscription-local only;
- API-key usage forbidden;
- `ANTHROPIC_API_KEY` must fail fast;
- project-bound wrapper only;
- review packet in, normalized reviewer report out;
- raw output and invocation metadata stored;
- findings remain candidate/unvalidated.

## Workflow-specific notes

### project-initialization

Mandatory application/onboarding workflow:

```text
intake -> raw scan -> structured inventory -> domain identification
-> legacy adoption decision -> draft project overlay -> validate project binding
-> initialization report -> human approval
```

Default mode: `scan-only + draft-overlay`.

### big-feature-contract-first

Reference end-to-end development workflow:

```text
intake -> repository grounding -> contract -> behavior bindings -> plan gate
-> red capture (contract scenarios as executable tests, failing run) -> implementation
-> verification gate (green re-run) -> review -> finding validation -> fusion -> final decision
```

### bugfix-regression-capture

Lightweight bugfix workflow:

```text
bug intake -> reproduction/diagnosis -> regression scenario -> minimal fix plan
-> implementation -> regression verification gate -> evidence -> final decision
```

Default rule:

```text
No fix without captured regression unless the workflow explicitly records why reproduction is impossible.
```

This reproduce-before-fix rule is the bugfix instance of the test-framed
implementation discipline (ADR-0017): the failing (red) run is captured before the
fix, and the regression gate confirms the green re-run after.

### review-only-fusion

Review utility workflow:

```text
existing artifact/evidence -> evidence availability gate -> independent read-only reviews
-> finding validation -> fusion -> final decision support
```

It does not run implementation checks itself. If implementation evidence is required but missing, it returns `needs-verification-evidence`.

### new-project-spec-first

Specification workflow, not an implementation workflow in v0.2:

```text
problem framing -> target system spec -> enabling system spec -> term map
-> research brief -> options/decision contracts -> architecture sketch
-> initial contracts -> roadmap -> spec review gate -> final specification package
```

## Language and artifact policy

Repository docs are primarily English for portability across coding agents and future users. Russian handoff prompts are allowed outside the repository or in clearly marked handoff artifacts.

Workflow run artifacts live under:

```text
Docs/agentsflow/runs/
```

Reports and summaries are committed to the repository. Heavy raw logs are optional and may be gitignored.

Schemas are strict for core artifacts and more permissive for exploratory assessments.
