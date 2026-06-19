# project-onboarding-assessment

Use this skill during `project-initialization`.

## Purpose

Produce candidate workflow/gate/risk recommendations for an AgentsFlow project overlay.

## Rules

- Do not modify source files.
- Treat outputs as candidate structured artifacts until validated/approved.
- Produce strict JSON role reports for architecture, verification and adversarial
  assessment using `templates/project-assessment.role.json` and conforming to
  `schemas/project-assessment.schema.json`.
- For prompt-sensitive target workflows, add a conditional `prompt_engineering`
  role report using the same template and schema.
- Validate all required role reports before synthesis. Markdown or prose-only
  role output is invalid workflow evidence; reject it and rerun or pause instead
  of normalizing it as authoritative.
- Synthesize role reports into `project-assessment.json` only after every
  required role report is schema-valid.
- Role reports may overlap and findings must remain `candidate-unvalidated`
  until main-agent relevance validation.
- Separate observed facts from inferred judgments.
- Include provenance, confidence and human-confirmation needs for non-trivial inferences.
- Analyze project documentation and Markdown implementation history when present.
