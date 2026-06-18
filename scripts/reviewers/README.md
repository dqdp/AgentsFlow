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
- fails if configured forbidden Claude API/proxy environment variables are present;
- loads a review packet;
- invokes the provider or a mock response for smoke testing;
- normalizes raw provider output into `reviewer-report.json`;
- stores raw output and invocation metadata.

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
