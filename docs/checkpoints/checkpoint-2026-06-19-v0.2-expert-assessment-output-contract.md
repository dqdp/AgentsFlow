# Checkpoint: v0.2 Expert Assessment Output Contract

Date: 2026-06-19

Status: accepted

## Decision

`project-initialization` expert assessment role reports are authoritative
workflow artifacts only when they are returned as strict JSON conforming to
`schemas/project-assessment.schema.json`.

Markdown or prose-only assessment output is invalid workflow evidence. The main
agent must reject it and rerun the assessment or pause the workflow instead of
silently normalizing it into an authoritative artifact.

Synthesis is allowed only after all required role reports are schema-valid. The
synthesis artifact must record role-report validation before presenting
candidate recommendations. Any findings inside role reports or synthesis must
remain `candidate-unvalidated` until main-agent relevance validation.

The default v0.2 expert assessment remains the required triad:

```text
architecture
verification
adversarial
```

For prompt-sensitive target workflows, `project-initialization` may add a
`prompt_engineering` role report. This is additive and does not replace any
required triad role.

## Rationale

The Bro dogfood run showed a procedure failure: assessment agents returned
structured prose instead of the schema-bound artifacts expected by the workflow.
The content could be manually normalized, but that would make the phase boundary
depend on the main agent's interpretation rather than a reproducible contract.

v0.2 needs deterministic checks at phase boundaries. Human-readable Markdown is
still acceptable for explanations and chat, but the artifact that advances the
workflow must be schema-bound.

## Consequences

- `workflows/project-initialization/workflow.yaml` declares an explicit
  `expert_assessment_output_contract`.
- `schemas/project-assessment.schema.json` requires readiness and validation
  metadata for role reports and synthesis.
- `scripts/validate_repo.py --root .` validates the workflow wiring, the
  project-onboarding-assessment skill contract, and example synthesis references
  to schema-valid JSON role reports.
- The active v0.2 behavior contract and binding manifest include an executable
  scenario for schema-bound expert assessment before synthesis.
