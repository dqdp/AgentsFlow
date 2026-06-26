# Core Workflow Simplification Audit

Status: Draft for discussion

Date: 2026-06-26

Branch: `codex/simplify-core-workflows`

## Purpose

This audit evaluates whether the PR readiness simplification pattern should be
applied to the v0.2 core workflows:

- `project-initialization`
- `big-feature-contract-first`

The working hypothesis is that the main complexity problem is not the presence
of protective gates. The problem is over-formalized connective tissue: workflow
definitions have started to duplicate reusable review, finding-validation,
materiality, human-interaction and project-binding rules that already belong to
shared models, skills, templates, schemas or project bindings.

This document is intentionally an audit and cut proposal. It does not implement
workflow changes.

## Sources Reviewed

- `docs/philosophy.md`
- `docs/review-control-model.md`
- `docs/review-fusion-model.md`
- `docs/project-initialization-model.md`
- `docs/project-binding-model.md`
- `docs/adr/ADR-0001-modular-workflow-composition.md`
- `docs/adr/ADR-0007-review-findings-require-relevance-validation.md`
- `docs/adr/ADR-0018-phase-transition-control.md`
- `workflows/project-initialization/workflow.yaml`
- `workflows/big-feature-contract-first/workflow.yaml`
- `schemas/workflow.schema.json`
- `schemas/review-cycle.schema.json`
- `templates/finding-validation-report.md`
- `templates/review-cycle-report.md`

## Ownership Classes

Use these ownership classes when deciding whether workflow YAML should keep a
rule:

| Class | Owner | Belongs in workflow YAML? |
|---|---|---|
| `workflow-owned` | workflow definition | Yes, when it defines phase order, phase kind, required outputs, default strictness, default topology, gate identity or authority mode. |
| `skill-owned` | skill instructions | No, when it explains how an agent performs an intellectual task. |
| `script-owned` | deterministic script or validator | No, when it describes executable validation or evidence computation. The workflow should reference the script/gate. |
| `template-owned` | artifact template | No, when it describes report/table/field content for run artifacts. |
| `project-binding-owned` | project overlay or binding | No, when it maps workflow requirements to project-specific commands, gates, providers, evidence locations or review assignments. |
| `run-artifact-owned` | concrete workflow run | No, when it records task-specific decisions, selected risk surfaces, FPM rows, material changes or evidence references. |
| `review-control-owned` | shared review/fusion/finding-validation model | No, unless the workflow is explicitly selecting or overriding a policy with a reason. |

## Protective Invariants To Preserve

The simplification should not remove these controls:

- red-capture before implementation and green verification after implementation;
- concrete gates must remain executable through project-bound runners;
- review agents are read-only and run after verification by default;
- reviewer findings remain candidate findings until main-agent relevance
  validation;
- validated P0/P1 findings and mandatory evidence gaps block acceptance;
- human-mediated decisions remain explicit and recorded;
- project-specific commands and provider details remain in project bindings or
  run evidence, not upstream workflow definitions;
- documentation legacy adoption remains human-confirmed for existing projects.

## Findings

### F-001: BFCF Duplicates The Shared Review-Control Pipeline

Area:

- `workflows/big-feature-contract-first/workflow.yaml`
- `review_control_rules`
- `review_cycle`

Observed issue:

`big-feature-contract-first` repeats shared review-control semantics:

- reviewers are read-only;
- reviewers run after verification;
- findings are candidates;
- P0/P1 candidates must not be silently discarded;
- default exit is no validated blockers;
- missing mandatory evidence blocks;
- post-fix materiality must be classified;
- validated severities and final states are listed locally.

These rules are already defined in:

- `docs/review-control-model.md`
- `docs/review-fusion-model.md`
- `templates/finding-validation-report.md`
- `templates/review-cycle-report.md`

Ownership:

- Current location: workflow YAML.
- Correct owner: `review-control-owned`, with workflow selection only.

Why it creates complexity:

- Every workflow can drift from the shared control model.
- Reviewers can find process bugs in copied policy instead of product/workflow
  behavior.
- Adding a new review-control rule encourages editing every workflow.
- The workflow starts to look like a review runtime rather than an orchestration
  recipe.

Minimal cut:

- Replace most of `review_control_rules` and `review_cycle` with a short
  reference to the standard review-control pipeline.
- Keep only BFCF-specific selections:
  - review phase exists after green verification;
  - fusion is enabled when selected by the workflow topology;
  - default topology is `homogeneous-dual`;
  - BFCF has implementation materiality because it changes source behavior and
    evidence.
- Let `finding-validation-report.md` and `review-cycle-report.md` carry the
  materiality decision for each run.

Do not cut:

- the `review`, `fusion` and `finding_validation` phases;
- the requirement that review evidence is fresh after material changes;
- the full-packet rerun rule after material changes.

### F-002: BFCF Review Topology Mixes Workflow Default, Profile Details And Gate List

Area:

- `workflows/big-feature-contract-first/workflow.yaml`
- top-level `review`

Observed issue:

The top-level review block contains several different layers:

- workflow default topology;
- risk-surface escalation policy;
- concrete default reviewer ids;
- prompt sameness policy;
- context policy;
- a list of gates;
- blocking policy.

Some of this is workflow-owned. Some is review-profile-owned or
project-binding-owned.

Ownership:

- `topology: homogeneous-dual`: workflow-owned.
- `risk_surface_escalation_policy`: workflow-owned at a high level, but should
  probably reference risk policy/profile definitions rather than embed a long
  rule.
- `reviewers`: project-binding-owned for concrete runs when provider/model
  assignments matter.
- `same_prompt`, `same_packet`, `same_rubric`, `same_output_schema`:
  review-profile-owned.
- `context_policy`: review-control-owned/profile-owned.
- `gates`: workflow-owned only if it lists workflow phase gates; not
  review-profile-owned.
- `blocking_policy`: review-control-owned.

Why it creates complexity:

- Topology, prompt construction and gate sequencing become entangled.
- Project-specific reviewer/provider assignments are easy to misread as
  upstream defaults.
- A future topology change can force edits to BFCF even when the core workflow
  phase sequence is unchanged.

Minimal cut:

- Keep a small workflow-level review selection:

  ```yaml
  review:
    topology: homogeneous-dual
    topology_source: workflow_default
    control_policy: standard-review-control
    escalation_policy: risk_surface_driven
  ```

- Move or reference prompt/context details through review profiles.
- Keep concrete provider/model assignment out of upstream BFCF.

### F-003: BFCF Repeats Permission And Fusion Semantics Already Owned By Review Control

Area:

- `workflows/big-feature-contract-first/workflow.yaml`
- `review_agent_permissions`
- `fusion`
- parts of the `review` and `fusion` phases

Observed issue:

BFCF declares that review agents are read-only, cannot run tests, cannot mutate
files, and that fusion is read-only and cannot launch reviewers or run gates.
Those are shared review-control invariants.

Ownership:

- Correct owner: `review-control-owned` and reviewer role/profile definitions.
- Workflow owner: only whether the phase exists and what it consumes/produces.

Why it creates complexity:

- It duplicates safety invariants in multiple places.
- If a reviewer role ever gets a declared tool exception, workflow YAML can
  conflict with role/profile policy.

Minimal cut:

- Keep phase-level `kind: review`, `runs_after: verification_gate`, and
  high-level outputs.
- Remove or reference the shared permission policy instead of repeating it.

### F-004: Project Initialization Duplicates Review-Control Rules For Initialization Review

Area:

- `workflows/project-initialization/workflow.yaml`
- `review_control_rules`
- `review`
- `review_cycle`

Observed issue:

Project initialization repeats the same candidate-finding, relevance-validation,
topology and materiality controls that are already defined in the shared review
model.

Ownership:

- Current location: workflow YAML.
- Correct owner: `review-control-owned`, with workflow selection only.

Why it creates complexity:

- Initialization review is not special enough to need a separate copy of the
  review-control model.
- The copied `materiality_classification` includes fields that do not naturally
  belong to initialization, such as `affected_implementation_behavior` and
  `behavior_bindings`.

Minimal cut:

- Keep only:
  - initialization review phase exists for `adoption-onboarding` and
    `prepare-workflow`;
  - review is read-only and candidate findings require main-agent validation via
    the standard review-control pipeline;
  - `fusion_required: false` if that is a real workflow selection.
- Remove local materiality enumerations and rely on the standard
  finding-validation/review-cycle templates.

### F-005: Project Initialization Is Both Router And Procedure

Area:

- `workflows/project-initialization/workflow.yaml`
- `mode_gated_outputs`
- `intent_mode_phase_policy`
- mode-specific phases

Observed issue:

`project-initialization` has a legitimate mode-gated design, but the workflow
YAML currently acts as both:

- a router across intent modes;
- a detailed procedure for each mode;
- a catalog of all possible outputs;
- a human-decision policy;
- a review policy;
- a partial target-workflow readiness model.

Ownership:

- Router and phase order: workflow-owned.
- Detailed mode procedures: skill/model-doc-owned.
- Complete artifact field shapes: template/schema-owned.
- Project-specific activation policy: project-binding-owned or
  human-decision-owned.

Why it creates complexity:

- A single workflow accumulates every special case.
- `unknown-discovery`, `adoption-onboarding`, `prepare-workflow`,
  `legacy-cleanup` and `risk-domain-assessment` are hard to reason about
  independently.
- Small changes to one mode can look like changes to the whole workflow.

Minimal cut:

- Do not split into separate workflows yet.
- Make the YAML a smaller mode router:
  - common spine;
  - supported modes;
  - per-mode required phase ids;
  - per-mode required artifact classes.
- Move detailed mode-specific procedure text to
  `docs/project-initialization-model.md` and the relevant skills/templates.

### F-006: `target_workflow_context_decision_packet` Is Too Broad

Area:

- `workflows/project-initialization/workflow.yaml`
- `target_workflow_context_decision_packet`

Observed issue:

The phase can capture missing gate, review, evidence, authority, scope, ADR,
risk-surface, FPM, contract and workflow-design decisions. This is useful as an
escape hatch, but it is also a broad glue artifact.

Ownership:

- Current location: workflow YAML.
- Correct owner: mixed:
  - target workflow preflight owns missing requirements;
  - run artifact owns concrete open decisions;
  - human-decision artifact owns accepted/deferred answers;
  - project binding owns persistent gate/review/evidence policy.

Why it creates complexity:

- It can become a catch-all for any missing target-workflow design.
- It blurs whether a decision is run-scoped or persistent project policy.
- It encourages prepare-workflow to absorb BFCF decisions rather than hand off
  bounded open decisions.

Minimal cut:

- Keep the phase, but narrow its semantics:
  - it records target-workflow open decisions discovered by readiness preflight;
  - each decision must reference an owning workflow requirement or project
    binding requirement;
  - it must classify `run_scoped` versus `persistent_policy_candidate`;
  - unresolved blocking decisions block target-workflow readiness;
  - persistent policy is not activated without onboarding or explicit human
    activation.
- Avoid a broad free-form category list in workflow YAML.

### F-007: Documentation Disposition Is Verbose But Mostly Protective

Area:

- `workflows/project-initialization/workflow.yaml`
- `documentation_disposition_decision`

Observed issue:

The documentation disposition phase includes detailed mode names, extraction
depths and consequences. This is verbose and partially duplicates the model doc
and checkpoint.

Ownership:

- Human-confirmed decision requirement: workflow-owned/protective invariant.
- Mode definitions and extraction semantics: model-doc/template/schema-owned.

Why it creates complexity:

- The workflow becomes a mini-spec for documentation legacy adoption.
- Future changes need multiple synchronized edits.

Minimal cut:

- Not a first implementation slice.
- Preserve the human-confirmation invariant.
- Later, replace detailed mode descriptions with a reference to
  `project-documentation-disposition.yaml` schema/template and the accepted
  documentation legacy adoption checkpoint.

### F-008: Expert Assessment Output Contract Is Verbose But Guarding A Real Failure Mode

Area:

- `workflows/project-initialization/workflow.yaml`
- `expert_assessment`
- `expert_assessment_output_contract`

Observed issue:

This block encodes strict JSON, no prose, schema validation before synthesis,
and invalid output policy.

Ownership:

- Output artifact and schema: template/schema-owned.
- Strict evidence boundary: workflow-owned enough to keep as a required
  invariant.
- Prompt details: skill-owned.

Why it creates complexity:

- Some launch prompt requirements are procedural details that could live in the
  assessment skill.

Minimal cut:

- Do not simplify this first. It protects against a known failure mode:
  prose-only expert output being normalized as authoritative evidence.
- Later, keep the invariant in workflow and move prompt wording to the skill.

### F-009: Workflow Schema Allows Arbitrary Glue Fields

Area:

- `schemas/workflow.schema.json`

Observed issue:

Several top-level workflow properties allow arbitrary nested content:

- `review`
- `review_control_rules`
- `actor_model`
- `human_interaction`
- `verification`
- `review_agent_permissions`
- `fusion`

This makes it easy to add new glue fields when a review finds a gap.

Ownership:

- Schema-owned.

Why it creates complexity:

- Validation cannot distinguish a legitimate workflow selection from a local
  duplicate of shared policy.
- New process concepts can be introduced without an ADR, model doc, template or
  script owner.

Minimal cut:

- Do not start with strict schema closure; that would be too disruptive.
- First add a documentation rule or lint target that discourages duplicated
  standard policy blocks unless the workflow records an explicit override reason.
- Only tighten schema after the YAML has been simplified and current examples
  are aligned.

## Proposed Minimal Cut Order

### Slice A: BFCF Review-Control Contraction

Goal:

Remove duplicated review-control and review-cycle internals from
`big-feature-contract-first` while preserving the phase sequence and protective
review invariants.

Expected changes:

- Replace local `review_control_rules` with a compact reference to the standard
  review-control pipeline.
- Replace local `review_cycle` details with a compact policy selection and
  reference to `templates/review-cycle-report.md`.
- Remove duplicated `blocking_default`, `validation_required_for`,
  `final_states` and detailed materiality lists from BFCF unless a BFCF-specific
  override is required.
- Keep BFCF-specific phase sequence, red/green framing, review/fusion/finding
  validation phases and fresh evidence requirements.

Why first:

- The duplication is obvious.
- PR readiness already established the producer/consumer pattern.
- This slice should delete more YAML than it adds.

### Slice B: Project Initialization Review-Control Contraction

Goal:

Apply the same shared review-control reference to initialization review without
changing mode behavior.

Expected changes:

- Remove duplicated `review_control_rules` and `review_cycle` materiality lists.
- Keep initialization review phase and `fusion_required: false` if still
  intended.
- Keep human-confirmed documentation disposition and overlay approval rules.

Why second:

- Less risky after BFCF establishes the pattern.
- Project initialization has more mode-gated behavior, so it should not be the
  first cut.

### Slice C: Prepare-Workflow Decision Packet Narrowing

Goal:

Keep `target_workflow_context_decision_packet` as a real escape hatch, but stop
it from acting as a universal glue bucket.

Expected changes:

- Rename or clarify it as target-workflow open decisions.
- Require each decision to reference an owning workflow or binding requirement.
- Classify run-scoped decisions separately from persistent policy candidates.
- Keep unresolved blocking decisions as readiness blockers.

Why third:

- This is semantically important and may need careful review.
- It touches project-initialization behavior, not just duplicated policy.

### Slice D: Workflow Schema Guardrail

Goal:

Prevent the same over-formalized glue pattern from returning.

Expected changes:

- Add a light validation or documentation guard that says workflow definitions
  should not duplicate standard review-control policy without an explicit
  override reason.
- Avoid closing broad schema fields immediately.

Why fourth:

- Schema tightening before YAML cleanup would probably create churn.
- The first guard should be small and aligned with actual simplified examples.

## Non-Goals For This Branch

- Do not remove red-capture / green-verify framing.
- Do not remove project initialization documentation legacy adoption human
  confirmation.
- Do not remove finding validation.
- Do not introduce a validation-agent or fusion-agent as a mandatory new actor.
- Do not split `project-initialization` into multiple workflows in the first
  pass.
- Do not build a workflow runtime.
- Do not add strict complexity budgets or hard stop caps.

## Open Discussion Points

1. Should BFCF keep `fusion` as a mandatory phase, or should the review topology
   decide whether fusion is required?
2. Should `project-initialization` keep `fusion_required: false`, or should it
   simply select a standard review topology with no fusion phase?
3. Should workflow YAML use `control_policy: standard-review-control`, or should
   that be expressed through a profile reference?
4. Should `target_workflow_context_decision_packet` be renamed, or only narrowed
   in place?
5. What is the minimum validation that prevents duplicated glue from returning
   without turning schema validation into another heavy subsystem?
