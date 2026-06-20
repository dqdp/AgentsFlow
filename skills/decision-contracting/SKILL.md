# Decision Contracting

Reusable AgentsFlow skill for the Specification / Plan phase pattern.

## Purpose

This skill helps create or validate planning/specification artifacts without implementing code.

For `project-initialization.prepare-workflow`, it also helps normalize run-level
target workflow decisions before readiness: missing gate, review, evidence,
risk-surface, Failure Path Matrix, authority, scope or workflow-design decisions
are captured as structured decision artifacts rather than hidden in chat.

## Rules

- Stay read-only unless a workflow explicitly assigns implementation authority to a different actor class.
- Produce structured artifacts, not vague chat notes.
- Surface assumptions, unknowns, and required evidence.
- Keep scope boundaries explicit.
- For prepare-workflow readiness, classify each missing or disputed decision as
  blocking-material, nonblocking-follow-up, nonblocking-known-limitation or
  out-of-scope.
- Record selected options, defaults, deferrals, residual risk and affected
  artifacts in `human-decisions.yaml` or the declared target workflow decision
  packet.
- Do not promote run-level prepare-workflow decisions into persistent
  `project-operating-decisions.yaml` unless the human explicitly chooses
  onboarding or policy activation.
