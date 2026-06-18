# Checkpoint: AgentsFlow v0.2.0 Slice 2

## Purpose

This checkpoint supersedes the pre-Slice-2 project-initialization summary in
`checkpoint-2026-06-17-v0.1.13.md`. The older `scan-only + draft-overlay`
default is no longer the project-initialization source of truth.

## Accepted decisions recorded in this checkpoint

### Project initialization is mode-gated

`project-initialization` starts with an explicit `intent_mode`. The supported
intent modes are:

```text
unknown-discovery
adoption-onboarding
prepare-workflow
legacy-cleanup
risk-domain-assessment
```

Top-level initialization outputs are mode-neutral. Overlay drafting, binding
activation, validation and human approval are mode-specific continuations, not
universal outputs.

### Shared initialization backbone

The shared backbone is:

```text
intake with intent_mode
-> raw scan
-> structured inventory
-> domain identification
-> triad expert assessment
-> mode-specific exit or continuation
```

Legacy adoption decisions and migration/quarantine plans happen after the
structured inventory, domain identification and expert assessment exist.

### prepare-workflow does not require full onboarding

`prepare-workflow` requires a concrete `target_workflow` in the v0.2 MVP user
workflow set. It may be used for projects that were initialized earlier, were
partially initialized, or were developed with AgentsFlow from the start.

It validates target-workflow readiness through `target_workflow_readiness_gate`,
not the full `project_initialization_gate`. The full initialization gate remains
for adoption/onboarding overlay validation.

Missing `prepare-workflow` gate, review, evidence or authority context is stored
as a run-level target workflow decision packet. It must not be promoted into
`project-operating-decisions.yaml` unless the human explicitly chooses onboarding
or persistent policy activation.

### Human-mediated operating decisions

Operating decisions are collected through an agent-led dialogue. The human is
not asked to manually fill YAML/JSON. Review agents do not ask humans questions
directly; they produce candidate findings and questions for the main agent to
synthesize.

Blocking-material human questions require an explicit non-defaultable shape:

```yaml
classification: blocking-material
answer_required: true
default:
  allowed: false
```

### Post-gate review and finding validation

When project initialization activates or prepares bindings/policy, review runs
after the applicable mode-specific gate and before approval/activation. Reviewer
findings remain candidate findings until main-agent relevance validation.

### Big-feature plan gate

`big-feature-contract-first` keeps a manifest-level `plan_gate` hook for higher
strictness levels before red capture and implementation. Workflow docs must not
teach prose-only gates without a gate manifest reference.

Project workflow bindings declare the selected `strictness`. Binding validators
must require unconditional workflow gates plus conditional gates whose
`applies_to_strictness` includes the selected strictness. L2 bindings must not
need a dummy `plan_gate`; L3/L4 bindings must bind `plan_gate`.

## v0.2 Slice 2 exit check

Slice 2 is acceptable only when:

- repository validation passes;
- targeted tests pass;
- `project-initialization` mode-gated behavior is represented in workflow docs,
  schema/templates and validators;
- `prepare-workflow` uses `target_workflow_readiness_gate`;
- `big-feature-contract-first` includes a manifest-level `plan_gate` hook;
- review findings from the Slice 2 gate are recorded and resolved according to
  the P0/P1/P2/P3 severity taxonomy and review-cycle exit policy.
