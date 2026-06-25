# External Reviewer Scripts

This directory contains the MVP external reviewer wrapper.

## v0.2 MVP provider

`run_external_reviewer.py` supports the first MVP provider:

```text
provider: claude-code
mode: subscription-local Claude Code CLI only
API-key usage: forbidden
```

The wrapper:

- loads provider config;
- validates subscription-local-only policy;
- fails if configured forbidden Claude API/proxy environment variables are present in the process environment or Claude settings files;
- invokes Claude Code with the v0.2 default `--model opus --effort max` unless the config already resolves to those defaults;
- requires `execution.sandbox_mode: require_escalated` when launched from Codex
  so Claude Code can access subscription-local auth/keychain state;
- requires `execution.permission_mode: default`; Claude Code plan mode is not
  used for reviewer gates because the wrapper must receive schema-bound JSON on
  stdout, not a Claude-managed plan artifact;
- invokes Claude Code with `--tools ""` so the reviewer is packet-bound and
  cannot read files outside the prepared review packet;
- loads a review packet;
- invokes the provider or a mock response for smoke testing;
- normalizes raw provider output into `reviewer-report.json`;
- stores raw output and invocation metadata, including requested model/effort,
  provider-reported model usage and normalization trace when available.

Reviewer prompts require one schema-valid reviewer-report JSON object. The
wrapper may deterministically normalize schema-adjacent structured Claude output
when it contains `summary`, a `findings` array and reviewer context or provider
identity that can be reconciled with the review packet. A successful gate still
requires a normalized `reviewer-report.json`: if a provider returns Markdown/text
that the wrapper cannot auto-normalize, the raw output is evidence for explicit
orchestrator normalization or a rerun, not completed gate evidence. Failed
provider invocations are stored as schema-valid invocation metadata with a
`failure_stage` and `failure_message`, but they never count as completed
external review evidence.
The reviewer report records the normalization source path/hash. The normalized
report output hash is stored in invocation metadata, not inside the report.

## Review-set runner

`run_review_set.py` reads a `review-prompt-contract.yaml` with
`reviewer_assignments`.

It is a thin gate dispatcher, not a general multi-provider runtime:

- internal assignments must already have a normalized reviewer report artifact;
- `claude-code` assignments are invoked through `run_external_reviewer.py`;
- external assignments are started asynchronously before the runner waits for
  their results, so two Claude reviewers in one set are dispatched without
  serial blocking;
- `--internal-report-wait-seconds` may be used when internal read-only
  reviewers are launched alongside external providers and their report-present
  artifacts may appear shortly after dispatch;
- assignment coverage and provider/model diversity policy are checked before
  dispatch;
- the runner writes a review invocation set evidence JSON summarizing provider,
  model family, report paths and invocation metadata.

The review prompt contract is the dispatch plan. The invocation set is the
completed-run evidence that repo validation can use to prove assigned reviewers
actually produced normalized reports.
The runner records `runner_scheduling: external-first-async` in invocation-set
evidence for this scheduling mode.
For assignment-enabled gates, `inputs.review_invocation_set` must be declared
in the contract before dispatch and `run_review_set.py --output` must match
that path. `prepare_review_set_artifacts.py` may be used before dispatch to
materialize packets, prompts and dirty-worktree accounting, but the dispatcher
does not require that optional preparation artifact.
Mock responses are for smoke tests only. External reviewer evidence used to
close a run must carry `execution_mode: real`.
Completed external evidence must also have `exit_code: 0` and invocation hashes
that match the current review packet, rendered prompt, prompt contract, role
contract, rubric, output schema, raw provider output and normalized reviewer
report.
When model diversity is required, completed diversity is derived from evidence:
internal reports must declare `reviewer.model`, and Claude assignments use
`requested_model` plus provider-reported model usage from invocation metadata.

Example mixed-provider smoke:

```bash
python3 scripts/reviewers/run_review_set.py \
  --contract Docs/agentsflow/runs/<run-id>/review-prompt-contract.yaml \
  --output Docs/agentsflow/runs/<run-id>/review-invocation-set.json
```

## Smoke test without Claude

```bash
python3 scripts/reviewers/run_external_reviewer.py \
  --provider claude-code \
  --config examples/external-reviewers/claude-code/claude-code.yaml \
  --input examples/external-reviewers/claude-code/review-packet.architecture.json \
  --mock-response examples/external-reviewers/claude-code/mock-raw-output.json \
  --output /tmp/reviewer-report.claude-architecture.json
```

## Non-goals

This is not a general multi-provider runtime, not a CI/enterprise API-key integration, and not a write-enabled reviewer.
