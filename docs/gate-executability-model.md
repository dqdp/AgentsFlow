# Gate Executability Model

## Purpose

This document defines how AgentsFlow formalizes gates while preserving the
separation between upstream methodology and project-specific execution.

## Gate Executability Rule

```text
Every concrete project-bound gate included in a real AgentsFlow workflow run must have a deterministic runner entrypoint.
```

BDD scenarios, contracts, Markdown specs, ADRs and prose requirements may define
what must be checked. They do not by themselves constitute an executable gate.

Correct flow:

```text
BDD/prose/contract requirement
  -> behavior binding or gate contract
  -> project-bound runner/instruments
  -> structured evidence and gate report
```

Incorrect flow:

```text
BDD scenario exists
  -> model says gate passed
```

## Gate authority modes

The word "gate" is a workflow-control term, not a single authority model. When
the distinction matters, a workflow or project binding should identify the gate
authority mode.

```text
deterministic_gate
  A deterministic runner evaluates declared checks, scripts, schemas or manual
  evidence presence and emits a gate report.

review_gate
  Independent review agents inspect a declared packet and emit candidate
  findings. The main/orchestrating agent validates relevance. The exit condition
  is no validated blockers and no mandatory evidence gaps, unless project policy
  adds human approval.

human_mediated_gate
  The main/orchestrating agent synthesizes evidence, reviewer findings and
  options for the human. The human decision is recorded in the workflow-run
  decision artifacts before the workflow can proceed.
```

These modes can be combined in a larger workflow control sequence, but they must
not be collapsed into one implicit step. For example, a deterministic `plan_gate`
can check that the plan packet is present and grounded; a separate
human-mediated plan decision can consume reviewer findings and record human
approval or amendment before red-capture begins.

This document's executability rule applies to project-bound executable gate
manifests and runners. It does not turn review agents or human approval into
deterministic scripts.

## Upstream gate contract vs project-bound executable gate

AgentsFlow has two gate layers.

### Upstream gate contract

Lives in AgentsFlow upstream:

```text
gates/<gate-id>.yaml
schemas/gate.schema.json
templates/*-gate-report.md
scripts/gates/run_gate.py  # generic manifest/report helper, not project proof
```

It defines:

- gate purpose;
- required inputs and outputs;
- allowed instrument classes;
- required evidence categories;
- result states;
- pass/fail/inconclusive policy;
- runner interface expectations;
- whether project binding is required.

### Project-bound executable gate

Lives in a project overlay:

```text
.agentsflow/gates/<gate-id>.yaml
.agentsflow/scripts/run_<gate-id>.sh
```

It maps the upstream contract to concrete commands, tools and evidence sources:

- tests;
- deterministic scripts;
- BDD/scenario runners;
- static analysis;
- dynamic analysis;
- debuggers;
- trace/log analysis;
- network traffic analysis;
- profilers;
- fuzzers;
- benchmarks;
- security scanners;
- custom domain tools;
- manual evidence checks.

## Refined rule

```text
A gate is not executable for a real workflow run until it is bound to a deterministic project-level runner.
```

Upstream may provide generic validators and dry-run runners, but those do not
prove project-specific correctness.

## Result states

Gate runners must return structured outcomes:

```text
pass
pass_with_notes
fail
inconclusive
needs_human_decision
blocked
```

A gate must not convert uncertainty into pass. Missing mandatory evidence is a
blocking condition or a `needs_human_decision` condition, depending on policy.

## BDD role

BDD is the human-readable behavior-spec layer. It is not the executable gate.

Required BDD scenarios become gate-relevant through behavior binding manifests:

```text
*.bindings.yaml
```

The gate runner checks the binding, executes or confirms the bound checks, and
includes results in the gate report.

## Red-capture relationship

Executability is necessary but not sufficient: a bound check must also have been run
against the unsatisfied state. For implementation work, ADR-0017 requires the same
check to produce a captured failing run (red) before implementation and a passing
run (green) after. This closes the gap where an always-green test, or a test never
run against broken code, could self-certify the gate — the failure mode this rule
exists to prevent. `validate_repo.py` enforces the framing structurally: a workflow
with a `kind: implementation` phase must frame it with a red-capture phase and a
green-verify phase using `test_framing` markers. Refactor-only workflows may use
`baseline_capture` before `change_type: refactor`, because the pre-change
behavior-preservation baseline is expected to pass rather than fail.

## Review/fusion relation

Review agents and fusion agents consume gate reports. They do not replace gates.

Review may identify that a gate is incomplete, misconfigured, unbound, or missing
evidence. That is a candidate finding. The missing or failed gate remains the
authoritative verification signal.

## Repository and project validation

`validate_repo.py` checks upstream consistency:

- workflow references resolve to upstream gate contracts;
- gate manifests have runner interfaces/generic runner paths;
- schemas/templates/scripts exist;
- workflow phases declare gate references;
- a workflow with a `kind: implementation` phase frames it with a pre-implementation red-capture phase, or refactor baseline-capture phase, and a post-implementation green-verify phase.

`validate_project_binding.py` checks a concrete project overlay:

- workflow binding extends an upstream workflow;
- project gate bindings extend upstream gate contracts;
- project-level runners exist;
- required commands/instruments are declared;
- project-bound gates and runners referenced by workflow bindings exist.
