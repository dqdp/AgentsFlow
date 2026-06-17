# External Reviewer Provider Model

AgentsFlow may use external model providers as **reviewer providers**. In v0.2 this is a project-bound capability, not a top-level runtime abstraction.

The initial MVP provider is **Claude Code CLI**, invoked from another harness such as Codex as an independent read-only reviewer.

## Core decision

External model reviewers must be invoked only through explicit project-bound wrappers.

A wrapper receives a bounded **review packet** and returns a normalized `reviewer-report.json` that conforms to the AgentsFlow reviewer-report schema.

External reviewers:

- are read-only by default;
- receive review packets rather than unrestricted repository authority;
- do not run verification gates;
- do not run tests unless an exceptional, explicit tool permission is granted;
- do not modify files;
- do not produce patches;
- produce candidate findings only;
- must pass main/orchestrating-agent relevance validation before their findings affect the workflow decision.

## MVP provider: Claude Code CLI

For v0.2, AgentsFlow implements a minimal Claude Code external reviewer provider:

```text
review packet
→ project-bound Claude wrapper
→ raw Claude output
→ normalized reviewer-report.json
→ reviewer invocation metadata
```

The MVP implementation target is intentionally narrow:

- provider: `claude-code` only;
- billing/auth: subscription-local Claude Code CLI only;
- API-key usage: forbidden;
- output: normalized reviewer report + raw output + invocation metadata;
- no multi-provider runtime;
- no write-enabled external reviewers;
- no CI/enterprise API-key mode.

## API-key usage policy

For the v0.2 MVP, API-key based Claude usage is **forbidden**.

Rationale:

- API-key usage can create uncontrolled or unexpectedly high cost.
- The intended first use case is a local personal workflow using an already-authenticated Claude Code CLI subscription session.
- AgentsFlow must not silently switch a review provider from subscription-local mode to API-key mode.

Provider wrappers must fail fast if API-key usage is detected.

Minimum required guardrails for Claude Code CLI wrappers:

- `expected_billing_mode: subscription-local`
- `forbid_api_key_usage: true`
- fail if `ANTHROPIC_API_KEY` is present in the environment;
- do not use API-key-only execution modes;
- record billing/auth mode in invocation metadata;
- record stdout/stderr/exit code and normalized output;
- validate output schema before passing it to finding validation or fusion.

API-key mode is not a future default. It may only be reconsidered as a separate explicit enterprise/CI design decision.

## Interface

```text
External Reviewer Provider =
  project-bound executable adapter
  that receives a review packet
  and returns normalized reviewer-report.json
```

Example command shape:

```bash
.agentsflow/scripts/reviewers/run_external_reviewer.py \
  --provider claude-code \
  --config .agentsflow/external-reviewers/claude-code.yaml \
  --input Docs/agentsflow/runs/<run-id>/review-packet.architecture.json \
  --output Docs/agentsflow/runs/<run-id>/reviewer-report.claude-architecture.json
```

## Review packet

The main/orchestrating agent prepares a bounded review packet. The external reviewer should review the packet, not freely re-orchestrate the project.

A review packet should contain:

- AgentsFlow version;
- workflow and run id;
- reviewer role and review goal;
- task contract or reviewed artifact;
- plan, diff summary or target artifact summary;
- changed files, if applicable;
- verification gate report, if applicable;
- evidence summary;
- accepted ADRs and project rules;
- forbidden actions;
- output schema reference.

## Claude adapter responsibilities

The Claude adapter must:

1. load provider config;
2. load and validate review packet;
3. verify subscription-local mode and reject API-key usage;
4. render the provider prompt;
5. invoke Claude Code CLI in non-interactive print mode;
6. capture raw output and process metadata;
7. parse and normalize `reviewer-report.json`;
8. validate schema;
9. mark findings as candidate/unvalidated;
10. store invocation metadata.

## Wrapper output artifacts

For each external review invocation, store:

```text
review-packet.<role>.json
reviewer-report.<provider>-<role>.raw.json
reviewer-report.<provider>-<role>.json
reviewer-invocation.<provider>-<role>.json
```

## Non-goals

The external reviewer provider model does not introduce:

- native Codex/Claude cross-agent messaging;
- API-key billing;
- a general agent runtime;
- verification authority;
- write-enabled external reviewers;
- direct fusion without main-agent finding validation.

## Relationship to review/fusion

External provider reports enter the same pipeline as any other reviewer report:

```text
review packet
→ external reviewer wrapper
→ candidate reviewer report
→ main-agent finding validation
→ fusion synthesis
→ final decision support
```
