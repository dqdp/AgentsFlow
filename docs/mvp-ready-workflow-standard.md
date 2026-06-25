# MVP-Ready Workflow Standard

## Status

Accepted for AgentsFlow v0.2 and updated in v0.1.13.

## v0.2 MVP scope

AgentsFlow v0.2 has one application/onboarding workflow, one supported target
workflow and utility workflows for review/fusion and PR merge readiness.

Application workflow:

```text
project-initialization
```

MVP supported target workflow:

```text
big-feature-contract-first
```

v0.2 utility workflows:

```text
review-only-fusion
pr-merge-readiness
```

Non-MVP workflows remain in the repository as reference/experimental workflows and must remain schema-valid only:

```text
agentic-system-hardening
bugfix-regression-capture
new-project-spec-first
prompt-behavior-eval
safe-refactor
research-to-ADR
```

The supported v0.2 end-to-end path is:

```text
project-initialization.prepare-workflow -> big-feature-contract-first
```

## MVP-ready definition

A workflow is MVP-ready when it is not just a prose idea but a reproducible workflow definition usable by a main/orchestrating agent and a human.

The MVP supported target workflow must have:

- validated `workflow.yaml`;
- explicit phase sequence;
- declared inputs and outputs;
- declared artifact templates;
- referenced upstream gate contracts;
- deterministic gate runner interface and project-binding requirements;
- review-cycle policy where applicable;
- behavior bindings for required acceptance scenarios where applicable;
- selected risk surfaces, required path classes and Failure Path Matrix coverage
  where the task contract selects control, persistence, failure or authority
  risks;
- at least one validated example or project-overlay example;
- repo-validation coverage;
- for workflows with an implementation phase, a red-capture (failing-test) phase before implementation and a green-verify phase after it (ADR-0017).

Guarantee strength must follow `docs/enforcement-boundary.md`: do not describe a
workflow property as script-enforced unless a validator or test actually checks it.

## v0.2 Definition of Done

AgentsFlow v0.2 is done when:

- repository validation passes;
- tests pass;
- the MVP supported target workflow is schema-valid;
- project-initialization path is coherent;
- project overlay model is represented;
- project-bound gates are represented;
- behavior bindings are represented;
- legacy adoption is represented;
- Claude Code external reviewer provider minimally works in subscription-local mode;
- one end-to-end example exists under `examples/e2e/minimal-python-project/`;
- `AGENTS.md` is usable by coding agents;
- non-MVP workflows remain reference/experimental and schema-valid only.

The project overlay model uses one canonical v0.2 shape: flat
`.agentsflow/project.yaml`, structured `.agentsflow/workflows/*.binding.yaml`,
and upstream pinning in `.agentsflow/agentsflow.lock.yaml`.

Human interaction in v0.2 is main-agent mediated. Workflows that need human
decisions declare pause-capable phases and record questions/answers as run
artifacts; review agents do not question humans directly.

When a workflow says "gate", it must not hide who has authority. Deterministic
gates are runner-decided, review gates are reviewer-output plus relevance
validation, and human-mediated gates require main-agent synthesis plus a
recorded human decision.

Workflow runs may use `phase_guard` in `workflow-run.yaml` as a lightweight
phase pointer. The guard records the current phase, allowed next phases and
allowed outputs. It is deliberately smaller than a workflow runtime: v0.2
validators check the declared run artifacts against the current phase's allowed
outputs, with draft artifacts accepted only in draft-labeled top-level artifact
slots, so future-phase artifacts are not silently promoted during project
initialization or other phased workflows.

## DoD interpretation

Soft DoD terms are interpreted as operational checks:

- `represented` means Doc + Instance + Wired: a model document in `docs/`, a
  concrete artifact instance (schema + template + at least one `examples/`
  instance), and a reference from at least one MVP `workflow.yaml` or project
  binding.
- `project-initialization path is coherent` means every
  `workflows/project-initialization/workflow.yaml` output has a corresponding
  template, concrete example, or explicit deferred/optional status.
- `Claude Code external reviewer provider minimally works` means the automated
  mock smoke test passes through the project-bound wrapper without a live Claude
  call. This is the CI-safe MVP check.
- PR merge readiness may require additional operator evidence from a live
  subscription-local Claude Code review gate. That evidence should be recorded as
  a readiness artifact, not as a mandatory repository test, because it depends on
  local Claude subscription auth and an escalated Codex sandbox.
- `AGENTS.md is usable by coding agents` means it contains source-of-truth order,
  explicit v0.2 scope, scope-expansion prohibition, validation commands, and
  accepted-decision pointers.

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
- configured Claude API/proxy environment variables must fail fast;
- project-bound wrapper only;
- review packet in, normalized reviewer report out;
- invocation metadata stored, with raw output stored only when explicitly
  non-sensitive;
- standalone external review can use `lite`: a bounded review request with
  referenced artifact paths and hashes. Use `strict-sealed` when a concrete risk
  requires embedding or otherwise proving the exact sealed provider input set,
  or when the current workflow validator requires strict invocation-set
  evidence;
- Codex-launched live runs use escalated sandbox access for subscription-local
  auth. Stdin packet transport disables Claude Code tools with `--tools ""`;
  file prompt transport may use only `--tools Read` for the generated prompt
  file in an isolated temporary directory;
- provider/model diversity is proved through assignment, invocation-set and
  reviewer-report evidence, not by role names alone;
- findings remain candidate/unvalidated.

`run_external_review_lite.py` is the helper for ordinary standalone live
external review. The strict packet-bound `run_external_reviewer.py` path remains
available for explicit `strict-sealed` runs and current PR-readiness
invocation-set validation. Live runs must not bypass project-bound wrappers with
direct provider commands.

## Release / PR readiness note

v0.2 MVP readiness and PR merge readiness are related but not identical. MVP
readiness is the repository baseline above: schemas, examples, validators, tests
and CI-safe smoke checks. PR readiness is a concrete branch decision and should
add branch-scoped evidence such as:

- clean worktree and intended commit range;
- repository validation and tests;
- source-of-truth documentation consistency check;
- review gate evidence, including live external reviewer evidence when available;
- relevance validation for P0/P1 candidate findings;
- human merge decision and post-merge verification plan.

This repository defines `pr-merge-readiness` as a dedicated utility workflow for
that branch-scoped decision. It stays small and composes existing validation,
review, finding-validation and human-decision artifacts instead of becoming a
general release-management runtime.

## Workflow-specific notes

### project-initialization

Mandatory application workflow with mode-gated continuations:

```text
intake with intent_mode -> raw scan -> structured inventory -> domain identification
-> schema-bound triad expert assessment -> documentation disposition for existing-project modes
-> mode-specific exit or continuation
```

Expert assessment role reports are strict JSON artifacts bound to
`schemas/project-assessment.schema.json`. Synthesis is not allowed until all
required role reports are schema-valid; Markdown or prose-only role output is
rejected, rerun or paused instead of normalized as authoritative evidence.

Mode-specific continuations:

```text
unknown-discovery
  stop after scan, inventory, assessments and questions unless the human asks to continue

risk-domain-assessment
  stop after domain/risk assessment and domain-expertise questions unless the human asks to continue

adoption-onboarding
  documentation disposition with explicit human-confirmed documentation adoption mode
  -> legacy adoption decision/migration plan when legacy artifacts are in scope
  -> human operating-decisions interview -> draft overlay/bindings/gates
  -> validate draft overlay -> initialization review -> finding validation
  -> initialization report -> human approval

prepare-workflow
  require target_workflow -> documentation disposition with explicit human-confirmed documentation adoption mode
  -> confirm sufficient target workflow operating context
  -> capture missing target workflow decisions or material design forks as a run-level decision packet
  -> target workflow readiness gate
  -> draft target workflow binding/readiness handoff only when ready
  -> initialization review -> finding validation

legacy-cleanup
  documentation disposition with explicit human-confirmed documentation adoption mode -> legacy adoption decision
  -> migration/quarantine plan -> draft active instruction map
  -> human approval before activation
```

Overlay drafting, validation and approval are not universal initialization
outputs. They apply to adoption-onboarding, legacy activation, or
prepare-workflow binding/policy activation. `prepare-workflow` requires
`target_workflow: big-feature-contract-first` and enough operating context for
that workflow: project or draft binding, gate policy, review policy, evidence
location and human-owned decisions. Material design forks discovered while
preparing that target workflow are handled as human-mediated checkpoints and
recorded in the same run-level decision packet before readiness validation.
Unresolved blocking-material forks block readiness unless explicitly deferred
with stated constraints.

### big-feature-contract-first

Reference end-to-end development workflow:

```text
intake -> operating context preflight -> repository grounding -> contract
-> behavior bindings -> plan gate when effective strictness requires it
-> contract acceptance as a human-mediated design decision review
-> red capture (contract scenarios as executable tests, failing run)
-> implementation -> verification gate (green re-run) -> review
-> fusion -> finding validation -> final decision
```

`big-feature-contract-first` declares a workflow default for its normal depth.
Project bindings inherit that default unless they explicitly record a lighter or
heavier strictness override with a reason.

If a project requires agentic review of the plan followed by human approval
before red capture, model it explicitly as a human-mediated gate or a declared
project-bound policy. Do not treat that step as an implicit side effect of
`plan_gate`.

The built-in `contract_acceptance` phase is a human-mediated design decision
review, not a blanket approval prompt. The main agent presents an open decision
inventory, then discusses each blocking or material decision with options,
tradeoffs, recommended path, rationale and the exact acceptance question.
Blocking decisions must be accepted, changed or explicitly deferred with
residual risk before red capture starts.

Open questions are classified in the task contract. Unresolved
`blocking-material` questions pause the workflow; nonblocking questions are
recorded as defaults, limitations or follow-up items. Post-review fixes are
classified as material or non-material before deciding whether to rerun review.

The contract phase selects the feature-specific risk surfaces from
`docs/risk-and-strictness.md` or the project overlay. When selected surfaces have
failure, denial, timeout, persistence or authority semantics, the contract must
include a Failure Path Matrix before red capture starts. Behavior bindings and
gate evidence classify checks with the corresponding risk surface and path
class. A selected path class may be deferred only with explicit residual-risk
language and human approval when required by project policy.

Review topology is derived from the task's selected risk surfaces and recorded
explicitly. The default remains `homogeneous-dual`; focused or heterogeneous
review is used only when the risk profile justifies it and reviewer roles resolve
to existing role contracts.

Verification and review evidence must be fresh for the latest material change.
Changes to the task contract, selected risk surfaces, Failure Path Matrix,
behavior bindings, gate/review policy, mandatory evidence or affected
implementation behavior invalidate prior evidence for the changed scope. The run
records the material change and refreshes green verification and review according
to the review-cycle policy.

Supplemental human-requested review is allowed after green evidence, but its
findings remain candidate findings. It reopens the fix loop only for
main-agent-validated P0/P1 findings or mandatory evidence gaps; otherwise it is
recorded without forcing another primary review cycle.

### bugfix-regression-capture

Reference/next workflow in v0.2. It remains schema-valid, but is not a supported
`prepare-workflow.target_workflow` and is not part of the v0.2 end-to-end pilot.

Lightweight bugfix shape:

```text
bug intake -> reproduction/diagnosis -> regression scenario -> minimal fix plan
-> implementation -> regression verification gate -> evidence -> review
-> finding validation -> final decision
```

Default rule:

```text
No fix without captured regression unless the workflow explicitly records why reproduction is impossible.
```

This reproduce-before-fix rule is the bugfix instance of the test-framed
implementation discipline (ADR-0017): the failing (red) run is captured before the
fix, and the regression gate confirms the green re-run after.

### review-only-fusion

v0.2 utility workflow. It supports review-control modeling and can be invoked as
a utility pattern, but is not a supported `prepare-workflow.target_workflow`.

Review utility shape:

```text
existing artifact/evidence -> evidence availability gate -> independent read-only reviews
-> fusion -> finding validation -> final decision support
```

It does not run implementation checks itself. If implementation evidence is required but missing, it returns `needs-verification-evidence`.

### new-project-spec-first

Reference/next workflow in v0.2. It remains schema-valid, but is not a supported
`prepare-workflow.target_workflow`. The v0.2 pilot targets an existing project
through `project-initialization.prepare-workflow -> big-feature-contract-first`,
not greenfield project specification.

Specification workflow shape:

```text
problem framing -> target system spec -> enabling system spec -> term map
-> research brief -> options/decision contracts -> architecture sketch
-> initial contracts -> roadmap -> spec review gate -> spec review
-> finding validation -> final specification package
```

## Language and artifact policy

Repository docs are primarily English for portability across coding agents and future users. Russian handoff prompts are allowed outside the repository or in clearly marked handoff artifacts.

For ordinary target projects, workflow run artifacts live under:

```text
Docs/agentsflow/runs/
```

AgentsFlow self-application runs live under:

```text
run-artifacts/agentsflow/runs/
```

This avoids a case-insensitive filesystem collision between the repository's
methodology source directory `docs/` and the project-style `Docs/` run-history
root.

Reports and summaries are committed to the repository when they are useful and
non-sensitive. Heavy raw logs are optional and may be gitignored.

Schemas are strict for core artifacts and more permissive for exploratory assessments.
