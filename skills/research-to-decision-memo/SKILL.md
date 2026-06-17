# Skill: research-to-decision-memo

## Purpose

Convert research into option maps, decision memos, and ADR candidates.

## Inputs

- `research_question`
- `sources`
- `constraints`
- `domain_pack`


## Outputs

- `research_brief`
- `option_map`
- `decision_memo`
- `adr_candidates`


## Procedure

1. Frame the question.
2. Collect evidence.
3. Compare options.
4. Separate facts, judgments, and unknowns.
5. Draft decision implications.


## Quality bar

- Sources/evidence are traceable.
- Decision rationale is explicit.
- Uncertainty is visible.


## Anti-patterns

- Treating research as implementation permission without ADR.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.
