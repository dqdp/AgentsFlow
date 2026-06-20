# Enforcement Boundary

## Status

Accepted for v0.2.

## Purpose

AgentsFlow must be clear about what it actually enforces and what it only
represents as workflow policy. A rule is not a script-level guarantee just because
it appears in a workflow, ADR, skill or template.

The v0.2 MVP may keep some important controls as agent protocol or human decision
points, but it must label them honestly.

## Enforcement levels

Use these labels for major guarantees:

```text
enforced_by_script
  A validator, test or deterministic checker fails when the rule is violated.

schema_validated
  The artifact shape is checked by JSON/YAML schema. This does not prove semantic
  quality.

represented_as_artifact
  The concept has a document, template/schema/example or workflow wiring, but no
  full deterministic enforcement.

agent_protocol
  The rule is mandatory for agents through AGENTS.md, workflow manifests, skills
  or prompts, but is not fully machine-checked.

human_decision
  The rule depends on explicit human confirmation or an unresolved-decision marker.

accepted_not_implemented
  The design is accepted, but the validator/script/runtime mechanism is still
  future work.
```

## v0.2 enforced baseline

The repository validator is expected to enforce:

```text
- YAML and JSON parseability.
- Core workflow manifests validate against `schemas/workflow.schema.json`.
- Referenced skills, scripts, templates, packs, review topologies and gates exist.
- Gate/verification phases reference an upstream gate manifest.
- Review phases do not declare deterministic scripts.
- Gate manifests have the required executable-gate contract shape.
- Required behavior bindings have checks and gates.
- Claude Code external reviewer configs forbid API/proxy environment routes.
- Active primary review gates declare at least two reviewers and reject
  `single-reviewer` topology.
- Active review gates declare fresh-context/no-fork reviewer context policy.
- Active review gates declare review composition and prompt policy; homogeneous
  review must use the same prompt, packet and rubric, while focused/heterogeneous
  review must declare explicit focus zones.
- `review-prompt-contract.yaml` has a schema-validated assembly shape and
  records rendered prompt, packet, rubric, role-contract and output-schema hashes.
- Claude Code external reviewer configs and packets declare fresh-context/no-fork
  context policy and no session persistence.
- `project-initialization` wires the human operating-decisions interview and
  `project-operating-decisions.yaml`.
- `project-initialization` wires project documentation disposition for existing
  project modes and schema-validates `project-documentation-disposition.yaml`
  template/example artifacts.
- `project-initialization` declares the expert-assessment strict-JSON output
  contract, validates the invoked assessment skill contract, schema-validates
  project-assessment template/example artifacts, and checks example synthesis
  references to schema-valid JSON role reports.
- `project-initialization` declares main-agent-mediated human-pause phases and
  question/decision artifacts.
- Canonical project overlay examples use flat `.agentsflow/project.yaml` and
  structured `.agentsflow/workflows/*.binding.yaml`.
- An implementation phase is structurally framed by a preceding red-capture phase
  and a following green-verify phase.
- When `workflow-run.yaml` declares `phase_guard`, declared run artifact paths in
  `artifacts`, `phase_evidence` and artifact-like `phase_status` fields are
  checked against the current phase's allowed outputs; draft artifacts are
  accepted only in draft-labeled top-level `artifacts` slots.
```

## v0.2 policy-only or partial controls

These controls are important, but are not full deterministic guarantees in v0.2:

```text
- BDD scenario quality and semantic test coverage.
- Whether a test truly exercises a required behavior.
- Truth of model-produced project inventory fields.
- Quality of expert assessment and review/fusion reasoning.
- Live-run proof that every expert-assessment agent actually returned strict JSON
  before synthesis. v0.2 validates declared workflow/skill/example artifacts and
  deterministic synthesis references; arbitrary project-run assessment outputs
  still require project-bound validation or main-agent protocol enforcement.
- Reviewer finding relevance before the main agent validates it.
- Runtime proof that a non-wrapper/internal reviewer was actually launched with
  zero inherited conversation context.
- Semantic quality of a reviewer role definition beyond schema presence.
- Human authority choices beyond the existence/status of the decision artifact.
- Correctness of model-produced documentation disposition classifications.
- Risk-surface selection and Failure Path Matrix semantic completeness. v0.2
  schemas can require review packets, task contracts and bindings to carry the
  selected risk/FPM/freshness envelope, but deciding that the selected surfaces
  and rows are complete remains agent protocol plus project-bound gate evidence.
- Red/green evidence-pair content validation inside gate reports.
- `phase_guard` as a full runtime state machine. v0.2 validation is ledger-only:
  it checks declared artifact paths, not whether an agent performed every action
  in the correct order.
```

The red/green phase topology is enforced at workflow-manifest level. Checking the
actual failing-run/passing-run evidence pair in run artifacts remains future work.

## Documentation rule

Docs should not imply `enforced_by_script` unless a validator or test actually
checks the condition. When a rule is represented, protocol-only, or future work,
say so directly.

## Design consequence

When adding a new control, decide its level explicitly before writing strong
claims. If the control is not script-enforced, either:

```text
1. add deterministic validation, or
2. mark it as schema_validated, represented_as_artifact, agent_protocol,
   human_decision, or accepted_not_implemented.
```

## Validator and schema change review rule

Small diffs to schemas or validators can still be high-risk when they change
artifact authority, gate behavior, review policy, evidence semantics or workflow
phase progression. Treat these changes as governance-boundary changes, not as
ordinary documentation or plumbing edits.

Before accepting such a change, check:

- every artifact surface the validator is expected to read;
- which surfaces are authoritative outputs, evidence, reports or draft-only
  placeholders;
- which malformed shapes must fail closed instead of being skipped;
- whether templates teach the same artifact authority model as the workflow;
- whether negative tests cover bypasses through each declared surface;
- whether docs state the exact enforcement level and limitation.
