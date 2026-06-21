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
- loads a review packet;
- invokes the provider or a mock response for smoke testing;
- normalizes raw provider output into `reviewer-report.json`;
- stores raw output and invocation metadata, including requested model/effort and provider-reported model usage when available.

## Review-set runner

`run_review_set.py` reads a `review-prompt-contract.yaml` with
`reviewer_assignments`.

It is a thin gate dispatcher, not a general multi-provider runtime:

- internal assignments must already have a normalized reviewer report artifact;
- `claude-code` assignments are invoked through `run_external_reviewer.py`;
- assignment coverage and provider/model diversity policy are checked before
  dispatch;
- the runner writes a review invocation set evidence JSON summarizing provider,
  model family, report paths and invocation metadata.

The review prompt contract is the dispatch plan. The invocation set is the
completed-run evidence that repo validation can use to prove assigned reviewers
actually produced normalized reports.
For assignment-enabled gates, `inputs.evidence_report` must be declared in the
contract before dispatch and `run_review_set.py --output` must match that path.
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
