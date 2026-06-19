# Specification Development Roadmap

Status: **open research area for v0.2+**.

`new-project-spec-first` is already an MVP workflow in v0.2; this roadmap tracks
the later deeper research/specification-development track beyond that MVP shape.

The current repository has enough structure for contracts and workflows, but the specification-development side is intentionally underdeveloped. This should become a first-class area rather than an afterthought.

## Why this matters

For agent-assisted development, many failures happen before implementation:

- the problem is framed too vaguely;
- non-goals are missing;
- architecture alternatives are not compared;
- acceptance criteria are written after the fact;
- the agent jumps into implementation without enough grounding;
- “plan mode” becomes a shallow checklist rather than a real specification process.

Therefore, spec-first workflows need their own skills, scripts, templates, and research base.

## Research track: plan mode in modern harnesses

Planned research questions:

1. How do current coding-agent harnesses structure planning before editing?
2. What is the boundary between plan, spec, task breakdown, and implementation?
3. Which harnesses support read-only planning or approval gates before writes?
4. How do they ground plans in repository evidence?
5. How do they prevent stale plans after user corrections?
6. How do they represent plan changes in traces/evidence?
7. How do they connect planning to tests and verification gates?

Candidate systems to investigate:

- Codex CLI / Codex IDE plan and goal flows;
- Claude Code planning flows;
- Gemini CLI planning/task behavior;
- spec-first toolkits and agent-specification repositories;
- research on test-driven or behavior-driven agent definitions;
- research on graph-based test impact and agent regression prevention;
- scenario/eval harnesses for multi-turn agent behavior.

This document deliberately does not assert final conclusions. It is a backlog for a separate research pass.

## Proposed spec-development workflows

### `new-project-spec-first`

Goal: turn a vague project idea into a structured project brief, architecture options, ADR seeds, and first behavioral contracts.

### `big-feature-spec-first`

Goal: turn a large feature request into a contract, boundaries, impact map, and implementation plan before coding.

### `research-to-ADR`

Goal: turn external research and alternatives into a decision memo and ADR draft.

### `plan-review-before-implementation`

Goal: require an implementation plan to be grounded, reviewed, and accepted before code changes.

This workflow does not exist yet in v0.1 and is a strong candidate for v0.2.

## Proposed new skills

- `problem-framing`
- `specification-discovery`
- `requirements-decomposition`
- `architecture-option-mapping`
- `plan-grounding`
- `plan-review`
- `acceptance-criteria-generation`
- `spec-to-contract-synthesis`
- `research-to-decision-memo`

## Proposed new scripts

- `spec_lint.py`
- `plan_lint.py`
- `grounding_evidence_check.py`
- `open_questions_check.py`
- `adr_candidate_check.py`

## Key design question

Should “plan mode” be a workflow, a phase common to several workflows, or a skill invoked by workflows?

Current hypothesis:

```text
Plan mode should be a phase pattern implemented by reusable skills/scripts,
not a single global workflow.
```

Workflows such as `new-project-spec-first`, `big-feature-contract-first`, and
`safe-refactor` can each invoke plan-mode skills at the depth declared by their
workflow default, with explicit project/run overrides only when justified.
