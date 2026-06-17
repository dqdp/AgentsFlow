# Skill: specification-discovery

## Purpose

Develop initial requirements/specification artifacts from problem framing, repository evidence, and constraints.

## Inputs

- `problem_statement`
- `repository_evidence`
- `domain_pack`
- `strictness`


## Outputs

- `requirements`
- `assumptions`
- `acceptance_criteria_candidates`
- `open_questions`
- `specification_brief`


## Procedure

1. Collect known constraints.
2. Distinguish requirements, assumptions, and open questions.
3. Propose acceptance criteria candidates.
4. Mark uncertainty instead of hiding it.
5. Prepare a specification brief.


## Quality bar

- Requirements are testable or explicitly marked as exploratory.
- Spec does not force premature architecture.


## Anti-patterns

- Inventing missing requirements.
- Conflating assumptions with decisions.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.
