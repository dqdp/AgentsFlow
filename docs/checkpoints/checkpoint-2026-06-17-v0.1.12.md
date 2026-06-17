# Checkpoint: v0.1.12 — External Reviewer Provider Interface

Date: 2026-06-17

## Accepted decisions

### External Reviewer Provider Interface

AgentsFlow may use external model providers as read-only reviewer providers through explicit project-bound wrappers.

The first provider is Claude Code CLI, invoked from another harness such as Codex. v0.1.13 clarifies that this provider is in v0.2 MVP scope.

### Subscription-local only for Claude

API-key based Claude usage is forbidden for the v0.2 MVP.

Wrappers must:

- use subscription-local mode only;
- fail if `ANTHROPIC_API_KEY` is present;
- avoid API-key-only execution paths;
- record billing/auth mode in invocation metadata.

### Wrapper contract

External reviewer wrappers receive a structured review packet and return a normalized reviewer report.

They must preserve raw output, invocation metadata and schema-validation status.

### Review semantics

External reviewer outputs are candidate findings only. They must go through main/orchestrating-agent relevance validation before fusion or final decision.

## Added artifacts

- `docs/external-reviewer-provider-model.md`
- `docs/adr/ADR-0016-external-reviewer-provider-interface.md`
- `templates/external-review-provider.yaml`
- `templates/review-packet.json`
- `templates/reviewer-invocation.json`
- `schemas/external-review-provider.schema.json`
- `schemas/review-packet.schema.json`
- `schemas/reviewer-invocation.schema.json`
- `examples/external-reviewers/claude-code/`

## Resolved or superseded by v0.1.13

- v0.2 includes a minimal Python wrapper for the Claude Code provider.
- The wrapper remains project-bound in usage, but a reference implementation is provided in `scripts/reviewers/`.
- Robust local-auth discovery remains intentionally minimal: API-key environment variables fail fast; subscription-local execution is otherwise delegated to the local Claude Code CLI.
- Reviewer role selection remains workflow/project-overlay configuration.
