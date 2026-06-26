# Core Workflow Simplification Contract

Status: Draft for discussion

Date: 2026-06-26

Branch: `codex/simplify-core-workflows`

## Accepted Direction

The design review accepted the following direction before implementation:

1. Use `review.control_policy: standard-review-control` as a lightweight
   workflow reference to the shared review-control / review-fusion model. Do not
   introduce a new policy registry or control-policy subsystem in this branch.
2. Keep `fusion` required in `big-feature-contract-first` while the workflow
   defaults to L3, because L3 requires a fusion report. This branch removes
   duplicated fusion-control glue from workflow YAML; it does not redefine L3 or
   make BFCF's default path no-fusion.
3. Narrow `target_workflow_context_decision_packet` in place. Do not rename it in
   the first pass. It records bounded target-workflow open decisions discovered by
   readiness preflight, not a universal glue bucket.
4. Add a guardrail only after workflow cleanup. Start with a documentation rule
   and, if needed, a small validator for the already observed duplicated
   review-control glue pattern. Do not close broad workflow schema fields in the
   first pass.

## Problem

The core v0.2 workflows are at risk of becoming too complex because workflow
YAML is absorbing connective tissue that belongs to reusable components.

The target problem is not that AgentsFlow has review gates, red/green evidence,
human-mediated decisions or finding validation. Those are protective
invariants.

The target problem is that workflow definitions have started to duplicate or
locally formalize internals of:

- review-control and finding-validation;
- fusion behavior;
- post-review materiality classification;
- reviewer prompt/profile policy;
- project-specific binding choices;
- run-scoped open decisions;
- artifact report structure.

This makes workflows harder to reason about, easier to drift, and more likely
to grow new process machinery in response to every review finding.

## Goal

Make `project-initialization` and `big-feature-contract-first` thinner
orchestration contracts.

The desired shape is:

```text
workflow = phase order + required gates + artifact classes + default policy selections
```

The workflow should declare what it uses and where authority lives. It should
not duplicate the detailed procedure of the skills, scripts, templates, review
control model, project binding or run artifacts it composes.

## Non-Goals

This branch must not:

- remove red-capture before implementation or green verification after
  implementation;
- remove executable project-bound gates;
- remove review gates where the workflow requires review;
- remove main-agent finding relevance validation;
- make reviewer findings authoritative without validation;
- weaken evidence freshness after material changes;
- remove human-mediated decisions where current methodology requires them;
- let project-specific commands or provider details move into upstream workflow
  definitions;
- split `project-initialization` into multiple workflows in the first pass;
- introduce a workflow runtime;
- introduce a mandatory validation-agent or fusion-agent as a new standard
  actor;
- introduce strict complexity budgets or hard stop caps;
- convert this simplification into another large schema or telemetry subsystem.

## Layer Ownership Rule

Use this rule before changing workflow YAML:

```text
Workflow owns composition.
Composed capabilities own their internals.
```

Concrete ownership:

| Concern | Owner |
|---|---|
| Phase order, phase kind, gate identity, default strictness, default topology, authority mode | workflow definition |
| How an agent authors a contract, assessment, review or synthesis | skill |
| Deterministic validation, linting, evidence checks and repo checks | script / validator |
| Report tables, artifact field shape and run evidence layout | template / schema |
| Project-specific commands, paths, runners, provider/model assignment and evidence locations | project binding / overlay |
| Selected risk surfaces, Failure Path Matrix rows, material changes and concrete human decisions | workflow run artifacts |
| Candidate-finding semantics, fusion semantics, blocker validation and review-cycle exit rules | shared review-control / review-fusion model |

If a workflow needs to deviate from a shared rule, it must record an explicit
workflow-specific override and the reason. Otherwise it should reference the
shared rule.

## Allowed Cuts

Allowed simplifications:

- replace duplicated review-control blocks with references to the standard
  review-control pipeline;
- replace local review-cycle materiality enumerations with run-level
  materiality classification in `finding-validation-report.md` or
  `review-cycle-report.md`;
- remove duplicated reviewer permission rules when the shared review-control
  model or reviewer role/profile already owns them;
- move mode-specific explanatory prose from workflow YAML into
  `docs/project-initialization-model.md` or skill instructions;
- narrow broad glue artifacts into bounded open-decision records;
- keep only workflow-specific policy selections in workflow YAML;
- add a light guardrail against future duplicated glue after current examples
  are simplified.

## Forbidden Cuts

Forbidden simplifications:

- deleting a protective invariant because it is verbose;
- replacing explicit human decisions with implicit agent defaults;
- moving project-specific execution details into upstream workflows;
- treating a review topology label as proof that review evidence exists;
- treating fusion as final truth;
- allowing closure-only review to accept material changes;
- deleting schema/template fields that current validators or examples still
  require without first updating the owning component;
- making schema validation stricter before current workflow examples are
  simplified and aligned.

## Proposed Slice Order

### Slice A: BFCF Review-Control Contraction

Thin `big-feature-contract-first` by replacing duplicated
`review_control_rules`, `review_cycle`, blocker defaults, validation-required
lists and detailed materiality lists with a compact reference to the standard
review-control pipeline.

Keep the BFCF phase sequence, red/green framing, review/fusion/finding-validation
phases and fresh-evidence requirements.

Implementation direction:

- use `review.control_policy: standard-review-control`;
- keep review after green verification;
- keep fusion required for BFCF's default L3 path while moving detailed fusion
  control semantics to the shared model;
- keep finding validation as the authority step for candidate findings.

### Slice B: Project Initialization Review-Control Contraction

Apply the same pattern to `project-initialization` review controls without
changing intent-mode behavior.

Keep initialization review, human-confirmed documentation disposition,
target-workflow readiness, overlay draft/activation boundaries and human
approval semantics.

### Slice C: Prepare-Workflow Decision Packet Narrowing

Narrow `target_workflow_context_decision_packet` so it records bounded
target-workflow open decisions rather than acting as a universal glue bucket.

Each decision should reference the owning workflow or project-binding
requirement and classify whether it is run-scoped or a persistent policy
candidate.

Implementation direction:

- narrow in place for the first pass;
- do not rename the phase unless a later slice proves the name still causes
  confusion;
- do not let this packet activate persistent policy by itself.

### Slice D: Light Guardrail Against Glue Re-Expansion

Add a small guardrail after simplification. Prefer documentation or a focused
validator/lint rule over broad schema closure.

The guardrail should catch duplicated standard policy blocks or new local glue
fields without explicit ownership and override rationale.

## Acceptance Criteria

The branch is acceptable only if:

- repository validation passes;
- tests pass;
- `project-initialization` and `big-feature-contract-first` remain schema-valid;
- the supported v0.2 path remains:

  ```text
  project-initialization.prepare-workflow -> big-feature-contract-first
  ```

- protective invariants are not weakened;
- workflow YAML deletes or contracts duplicated glue rather than adding more;
- ownership of moved/removed rules is documented in the owning model, skill,
  template, schema or project-binding layer;
- examples and templates remain coherent with the simplified workflow shape;
- review focuses on wrong-layer responsibility and lost protective invariants,
  not on adding more procedural machinery.

## Review Focus For This Branch

Reviewers should check:

- whether a removed workflow rule still has an owner elsewhere;
- whether the simplification accidentally weakens red/green, finding validation,
  evidence freshness, human decisions or project-binding boundaries;
- whether remaining workflow fields are true composition choices rather than
  copied internal policy;
- whether the branch deletes more glue than it adds;
- whether any new schema or validator change is narrowly justified.

## Discussion Questions

These questions were reviewed and the accepted direction above should guide the
first implementation pass. Reopen only if implementation evidence shows the
accepted direction adds complexity or weakens a protective invariant.
