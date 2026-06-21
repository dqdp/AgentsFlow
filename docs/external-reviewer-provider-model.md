# External Reviewer Provider Model

AgentsFlow may use external model providers as **reviewer providers**. In v0.2 this is a project-bound capability, not a top-level runtime abstraction.

The initial MVP provider is **Claude Code CLI**, invoked from another harness such as Codex as an independent read-only reviewer.

## Core decision

External model reviewers must be invoked only through explicit project-bound wrappers.

A wrapper receives a bounded **review packet** and returns a normalized `reviewer-report.json` that conforms to the AgentsFlow reviewer-report schema.

External reviewers:

- are read-only by default;
- start from fresh zero conversation context;
- must not receive a forked main-agent/orchestrator conversation;
- receive review packets rather than unrestricted repository authority;
- do not run verification gates;
- do not run tests in v0.2;
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
- fail if any of these environment variables are present:
  `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`,
  `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`;
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

## Review-set assignment layer

Provider config is not the review topology. A review gate first declares its
reviewer instances and roles in the review prompt contract, then optionally
binds those instances to providers through `reviewer_assignments`.

For v0.2 this binding is intentionally small:

- `reviewer_set` declares reviewer ids and role contracts;
- `provider_policy` declares whether external reviewers and model diversity are
  allowed or required;
- `reviewer_assignments` maps each reviewer id to a provider, model family and
  output paths;
- `run_review_set.py` dispatches external assignments through
  `run_external_reviewer.py` and verifies that internal reports already exist.
- completed runs store `review_invocation_set` evidence linking assignments to
  normalized reports, raw external output and invocation metadata.
- mock responses are smoke-test evidence only; completed review gates require
  external invocation metadata with `execution_mode: real`.
- completed external evidence must be bound to the current packet, prompt,
  contract, role contract, rubric, output schema, raw provider output and
  normalized reviewer report hashes, with `exit_code: 0`.

This keeps Claude Code as one provider behind the existing wrapper while
allowing a single review gate to mix internal Codex reports and external Claude
reports. Adding another provider should add a provider adapter and config
schema support, not a parallel review workflow.

In practice, artifact assembly should be mostly deterministic: a script can
collect paths, hashes, diff summaries, green-gate evidence and prompt-contract
boilerplate. Model reviewers should return structured findings and summaries;
they should not be responsible for inventing file paths or evidence hashes.

Example assignment shape:

```yaml
provider_policy:
  allow_external_reviewers: true
  require_model_diversity: true
  min_distinct_provider_model_families: 2
  unsupported_provider_behavior: config_blocker

reviewer_assignments:
  - reviewer: generalist-a
    provider: internal-agent
    model_family: codex
    packet_path: Docs/agentsflow/runs/<run-id>/review-packet.generalist-a.json
    report_path: Docs/agentsflow/runs/<run-id>/reviewer-report.codex-generalist-a.json
  - reviewer: generalist-b
    provider: claude-code
    model_family: opus
    provider_config: .agentsflow/external-reviewers/claude-code.yaml
    packet_path: Docs/agentsflow/runs/<run-id>/review-packet.generalist-b.json
    report_path: Docs/agentsflow/runs/<run-id>/reviewer-report.claude-generalist-b.json
    raw_output_path: Docs/agentsflow/runs/<run-id>/reviewer-report.claude-generalist-b.raw.json
    invocation_metadata_path: Docs/agentsflow/runs/<run-id>/reviewer-invocation.claude-generalist-b.json
```

## Review packet

The main/orchestrating agent prepares a bounded review packet. The external reviewer should review the packet, not freely re-orchestrate the project.

A review packet should contain:

- AgentsFlow version;
- workflow and run id;
- reviewer role and review goal;
- context policy: `start_mode: fresh_context` and `fork_conversation_context: false`;
- review prompt contract reference;
- resolved reviewer role contract reference;
- task contract or reviewed artifact;
- plan, diff summary or target artifact summary;
- changed files, if applicable;
- verification gate report, if applicable;
- evidence summary;
- accepted ADRs and project rules;
- project agent instructions such as `AGENTS.md`, when present;
- forbidden actions;
- output schema reference.

AgentsFlow v0.2 does not require a provider-specific instruction file such as
`CLAUDE.md`. External providers should receive the same bounded project rules as
other reviewers through explicit review-packet artifacts. If a project already
has `AGENTS.md`, the orchestrating agent may include it directly in the packet
or reference it with a recorded hash. A provider-specific instruction file, when
present, is just another declared packet artifact and must not silently override
the run's review prompt contract.

## Claude adapter responsibilities

The Claude adapter must:

1. load provider config;
2. load and validate review packet;
3. verify subscription-local mode and reject API-key usage;
4. render the provider prompt;
5. invoke Claude Code CLI in non-interactive print mode;
6. capture raw output, requested model/effort, provider-reported model usage and process metadata;
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
