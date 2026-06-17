# Skill: prompt-behavior-check

## Purpose

Evaluate prompt/skill/instruction changes for ambiguity, policy bypass, model-specific regressions, and forbidden behavior.

## Inputs

- `prompt_or_skill_diff`
- `behavioral_scenarios`
- `domain_pack`
- `strictness`


## Outputs

- `prompt_risk_notes`
- `scenario_assessment`
- `regression_candidates`


## Procedure

1. Identify behavior changed by the prompt.
2. Check for ambiguous instructions.
3. Check for conflicts with policy/domain pack.
4. Generate regression candidates.
5. Recommend trace/tool-call assertions where possible.


## Quality bar

- Risks are behavior-specific.
- Recommendations are testable.


## Anti-patterns

- Judging prompt style without behavioral evidence.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.
