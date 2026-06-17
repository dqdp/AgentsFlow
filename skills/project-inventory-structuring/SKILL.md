# project-inventory-structuring

Use this skill during `project-initialization`.

## Purpose

Fill a structured project inventory from raw scan evidence and selected documentation while separating observed facts, user-provided context, model-inferred fields, domain assumptions, and unknowns.

## Rules

- Do not modify source files.
- Treat outputs as candidate structured artifacts until validated/approved.
- Separate observed facts from inferred judgments.
- Include provenance, confidence and human-confirmation needs for non-trivial inferences.
- Identify apparent project domain(s) explicitly.
- For every domain classification, include observed evidence, model inference, confidence and human-confirmation status.
- Record unknown domain terms and questions for the user.
- Analyze project documentation and Markdown implementation history when present.
