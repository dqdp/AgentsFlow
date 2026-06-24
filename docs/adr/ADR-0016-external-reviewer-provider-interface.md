# ADR-0016: External Reviewer Provider Interface

Status: Accepted

Date: 2026-06-17

## Context

AgentsFlow supports independent review agents and fusion. To increase model diversity, a workflow orchestrated by one harness, such as Codex, may call another model or harness, such as Claude Code CLI, as an external reviewer.

A direct ad-hoc command such as `claude -p "review this diff"` is too loose. It does not define what context was passed, what permissions were granted, what output format is required, what billing mode was used, or how findings become part of AgentsFlow review/fusion.

## Decision

AgentsFlow defines an **External Reviewer Provider Interface**.

External model reviewers are invoked only through explicit project-bound wrappers. A wrapper receives a structured review packet and must return a normalized reviewer report.

For the v0.2 MVP:

- Claude Code CLI is implemented as the first external reviewer provider.
- Only local subscription-based Claude Code CLI usage is allowed.
- API-key based Claude usage is forbidden.
- Provider wrappers must fail fast if API-key usage is detected.
- External reviewer findings are candidate findings and require main-agent relevance validation.
- External reviewers do not replace verification gates.
- External reviewers do not modify files or run tests by default.
- The implementation is minimal: one provider, one wrapper path, one normalized reviewer-report output format, and stored invocation metadata.

Updated for review-gate hardening on 2026-06-24:

- when a review topology requires an external reviewer, provider
  unavailability, missing config, preflight failure or permission failure is a
  workflow blocker and must not silently fall back to internal-only review;
- a provider preflight/config blocker is not a substantive review cycle and is
  not a reviewer finding;
- live Claude Code review launched from Codex requires the project-bound wrapper
  to use the host-approved escalated/unsandboxed permission mode needed for
  subscription-local auth and keychain access;
- provider config must be tracked, or the run must explicitly record it as a
  local required config with enough metadata to reproduce the evidence decision;
- provider usage, token and cost evidence is recorded only when exposed by the
  provider, not estimated by AgentsFlow.

## Consequences

AgentsFlow can support multi-model review without becoming a multi-agent runtime.

Projects can enable the Claude reviewer provider in their project overlay while preserving AgentsFlow review rules.

The provider interface gives reproducible evidence:

- review packet;
- raw provider output;
- normalized reviewer report;
- invocation metadata;
- billing/auth mode record;
- schema validation result.

Review observability evidence also records preflight status, timestamps,
elapsed times, retry/timeout status, and provider-reported usage when available.

## Guardrails

A Claude Code provider wrapper must:

- use `expected_billing_mode: subscription-local`;
- set `forbid_api_key_usage: true`;
- fail if any configured forbidden Claude API/proxy environment variable is present
  (`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`,
  `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`);
- avoid API-key-only execution paths;
- avoid uncontrolled repository access in the initial MVP design;
- validate reviewer output schema;
- record invocation metadata;
- force findings to remain `candidate-unvalidated` until main-agent relevance validation.

If the wrapper is launched from a sandboxed host that blocks subscription-local
Claude Code access, the run must stop on a config/permission blocker unless the
human changes the required review topology. The wrapper must not work around
that blocker by switching to API-key, proxy, Bedrock or Vertex routes.

## Future work

Possible future work:

- additional external providers;
- local model reviewer providers;
- provider capability discovery;
- richer schema repair/retry policies;
- optional enterprise/CI auth policy as a separate explicit design decision.

API-key mode remains forbidden in the v0.2 MVP.
