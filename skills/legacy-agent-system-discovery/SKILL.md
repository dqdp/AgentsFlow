# legacy-agent-system-discovery

Use this skill during `project-initialization` for existing projects with legacy agent/process artifacts.

## Purpose

Discover and classify existing agent/process artifacts before AgentsFlow adoption.

## Rules

- Do not delete or overwrite existing agent/process instructions without backup and human approval.
- Classify every legacy artifact as active, imported, archived, deprecated, non-authoritative, or needs-human-decision.
- Preserve useful domain/process knowledge by extracting it into AgentsFlow artifacts when appropriate.
- Ensure the final project state has one active authority layer and no ambiguous legacy instructions.
- Treat recommendations as candidate assessments until validated by the main/orchestrating agent and approved by the human when required.

## Outputs

- legacy-agent-system-inventory
- agent-instruction-conflicts
- adoption-mode-recommendation
