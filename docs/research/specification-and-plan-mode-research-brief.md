# Research Brief: Specification Development and Plan Mode

Status: Planned
Workflow: research-to-ADR

## Research Question

How should this project model specification development and plan mode for modern agent-assisted development workflows?

## Motivation

The current v0.1 seed has strong structure for contracts, BDD, review, fusion, and evidence, but specification development needs deeper research.

## Areas to investigate

- Plan/goal modes in modern coding-agent harnesses.
- Read-only planning before edits.
- Repository grounding before plan generation.
- Plan approval and plan revision after user correction.
- Spec-first repositories and agent-specification frameworks.
- Arxiv/GitHub work on behavior-driven or test-driven agent definitions.
- Test-impact maps and regression prevention for coding agents.
- Scenario simulation harnesses for multi-turn agent behavior.

## Expected output

- research memo;
- comparison matrix;
- design implications;
- ADR for plan-mode/specification development;
- candidate new workflows and skills for v0.2.

## Candidate design outputs

- `plan-review-before-implementation` workflow;
- `plan-grounding` skill;
- `specification-discovery` skill refinement;
- `requirements-decomposition` skill;
- `architecture-option-mapping` skill;
- `spec_lint.py` script;
- `plan_lint.py` script.
