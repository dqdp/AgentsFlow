# Skill: problem-framing

## Purpose

Turn a vague idea into a clear problem statement, goals, non-goals, actors, constraints, and open questions.

## Inputs

- `raw_user_intent`
- `domain_pack`
- `strictness`


## Outputs

- `problem_statement`
- `goals`
- `non_goals`
- `actors`
- `constraints`
- `open_questions`


## Procedure

1. Restate the user intent in concrete terms.
2. Identify actors/users and operating context.
3. Separate goals from non-goals.
4. Extract constraints and unknowns.
5. Avoid proposing implementation before problem framing is stable.


## Quality bar

- Problem statement is specific enough to drive architecture options.
- Non-goals prevent scope creep.
- Open questions are explicit.


## Anti-patterns

- Jumping directly into implementation.
- Treating vague goals as fixed requirements.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.
