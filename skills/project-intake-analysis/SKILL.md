# project-intake-analysis

Use this skill during `project-initialization`.

## Purpose

Interpret a project intake/research assignment and turn it into analysis focus, constraints, preflight questions, domain-expertise questions, and open questions.

## Rules

- Do not modify source files.
- Unknown-project discovery is not an empty prompt; use `templates/research-assignment.unknown-project.md`.
- Give the user a chance to provide goals, known direction, constraints, non-goals and domain context before analysis proceeds.
- Treat outputs as candidate structured artifacts until validated/approved.
- Separate user-provided context, observed facts, inferred judgments, domain assumptions and recommendations.
- Include provenance, confidence and human-confirmation needs for non-trivial inferences.
- Ask whether the user is a domain expert and whether their domain knowledge should constrain initialization decisions.
- Analyze project documentation and Markdown implementation history when present.
