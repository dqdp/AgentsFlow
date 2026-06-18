# Philosophy

## Project thesis

Agent-assisted development should be organized as explicit, reviewable workflows rather than improvised chats or monolithic prompts.

The central project idea:

```text
Skills and scripts are modular building blocks.
Workflows are composed from those building blocks.
```

This repository should not grow by adding one giant workflow prompt per use case. It should grow by adding small, reusable capabilities that can be recombined.

## Core abstractions

### Workflow

A workflow is an orchestration recipe for a type of work:

- starting a new project;
- designing a large feature;
- hardening an agentic system;
- evaluating a prompt change;
- performing a safe refactor;
- capturing a bug regression;
- running multi-agent review and fusion.

A workflow declares what it uses. It does not duplicate all underlying logic.

### Skill

A skill is a reusable reasoning/procedure block. It tells an agent how to perform a specific intellectual operation:

- author a contract;
- design BDD scenarios;
- build an impact map;
- check ADR consistency;
- perform adversarial review;
- synthesize reviewer disagreement.

Skills are agent-readable and human-reviewable.

### Script

A script is deterministic automation:

- lint a contract;
- check changed-file boundaries;
- validate evidence;
- check a test impact map;
- detect vague Gherkin assertions.

Scripts should be CI-friendly and should not hide model judgment.

### Template

A template defines the shape of an artifact:

- task contract;
- evidence report;
- reviewer report;
- fusion report;
- ADR;
- research brief.

Templates reduce ambiguity and make outputs comparable across workflows.

### Domain pack

A domain pack injects domain-specific constraints:

- agentic systems;
- coding agents;
- backend services;
- C++ low-latency systems.

Domain packs should not replace workflows. They parameterize them.

### Profile

A profile tunes execution depth:

- strictness level;
- review topology;
- evidence level.

Strictness is metadata, not the main abstraction.

## Why not “BDD framework”?

BDD is important, but this project is not a BDD-only framework.

BDD/Gherkin is used as a human-readable language for behavioral contracts, especially for:

- forbidden behavior;
- agent process constraints;
- policy behavior;
- memory/tool/context behavior;
- regression scenarios;
- acceptance criteria.

BDD lives inside a broader workflow system.

## Rule of composition

A workflow may invoke:

```text
skills + scripts + templates + packs + profiles + reviewers
```

A workflow should not own the internals of those components.

## Rule of authority

Contracts are the source of truth for a task.

Tests, scripts, review agents, and fusion do not replace the contract. They check whether implementation and evidence satisfy it.

## Rule of determinism

Use deterministic scripts where possible.

Use model-based reviewers where judgment is necessary.

Use fusion to classify disagreement, not to average away blocking issues.

## Rule of red-before-green

When a workflow implements, the contract is first turned into executable tests that
are run against the unimplemented state to capture a failing (red) result;
implementation then makes them pass (green). This keeps tests honest — an
always-green or never-run test cannot certify implementation (ADR-0010) — and makes
the contract's behavior binding (ADR-0011) executable before code exists. The rule
is structural: an `implementation` phase must always be framed by a red-capture
phase before it and a green-verify phase after it. See `docs/adr/ADR-0017-test-framed-implementation-phase.md`
(accepted rule; structural workflow enforcement is in `validate_repo.py`).

## Rule of gradual adoption

Do not use heavy process for small work.

The same workflow can be executed with different strictness profiles. A low-risk change may need only boundaries and evidence; a high-risk prompt/policy/runtime change may need BDD scenarios, impact map, independent reviewers, fusion, and hidden regressions.

## Review controls are composable, not hard-coded

Review gates and review agents are not a fixed methodology baked into the project core.
They are composable control primitives. The core defines common interfaces for gates,
reviewers, evidence, severity, topology, and fusion. Each workflow decides how many
gates and reviewers it needs, which topology to use, and how strict the final
acceptance decision should be.

This preserves the project philosophy: skills and scripts are reusable bricks,
workflows are assemblies, and strictness/review topology are parameters of assembly.


## Reviewer findings are candidate findings

Review agents are valuable because they are independent, but independence does not make their findings authoritative truth. A reviewer report is an input to the workflow. The main/orchestrating agent must validate relevance against the contract, artifact/diff, evidence, workflow context, and accepted decisions before treating a finding as an accepted issue or required change.

P0/P1 candidate findings must be preserved until accepted, rejected with reason, or escalated to a human decision.
