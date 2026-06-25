# ADR-0016: External Reviewer Provider Interface

Status: Accepted

Date: 2026-06-17

## Context

AgentsFlow supports independent review agents and fusion. To increase model diversity, a workflow orchestrated by one harness, such as Codex, may call another model or harness, such as Claude Code CLI, as an external reviewer.

A direct ad-hoc command such as `claude -p "review this diff"` is too loose. It does not define what context was passed, what permissions were granted, what output format is required, what billing mode was used, or how findings become part of AgentsFlow review/fusion.

## Decision

AgentsFlow defines an **External Reviewer Provider Interface**.

External model reviewers are invoked only through explicit project-bound
wrappers. A wrapper receives either a structured review packet or a lite review
request with referenced artifacts, and must return a normalized reviewer report.

### 2026-06-25 simplification amendment

External reviewer context uses one v0.2 mode:

- `lite` is the ordinary standalone external-review helper. The run records a
  small review request plus referenced artifacts and hashes. The reviewer
  receives a declared review bundle and must cite only that bundle. This is not
  a hard filesystem sandbox. The review context boundary is mandatory; embedding
  every byte of context into the packet is not.

Earlier strict packet-bound wrapper and invocation-set designs are not part of
the v0.2 implementation. If a future workflow needs sealed, redacted or
clean-room provider context, it should introduce that as a separate accepted
slice with its own concrete use case instead of keeping a parallel unused review
path in the MVP.

For the v0.2 MVP:

- Claude Code CLI is implemented as the first external reviewer provider.
- Only local subscription-based Claude Code CLI usage is allowed.
- API-key based Claude usage is forbidden.
- Provider wrappers must fail fast if API-key usage is detected.
- External reviewer findings are candidate findings and require main-agent relevance validation.
- External reviewers do not replace verification gates.
- External reviewers do not modify files or run tests by default.
- The implementation is minimal: one provider, one lite helper for standalone
  review, one normalized reviewer-report output format, and stored invocation
  metadata. Lite mode must not be simulated by ad hoc direct provider calls.

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

## Future work

Possible future work:

- additional external providers;
- local model reviewer providers;
- provider capability discovery;
- richer schema repair/retry policies;
- optional enterprise/CI auth policy as a separate explicit design decision.

API-key mode remains forbidden in the v0.2 MVP.

## Proposed Follow-Up

ADR-0021 should clarify review observability and external-provider evidence:

- provider preflight/config blockers are separate from substantive review
  cycles;
- if an external reviewer is required by topology, provider unavailability or
  preflight failure blocks the workflow and must not silently fall back to
  internal-only review;
- Codex-launched live Claude Code reviewer runs use project-bound wrappers with
  escalated sandbox access for subscription-local authentication;
- raw provider output is stored only when classified as non-sensitive, otherwise
  the run stores redacted output, summary, pointer or omission reason;
- token and cost evidence is normalized only when provider-reported.
