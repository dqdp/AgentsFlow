# Claude Code External Reviewer Example

This example shows the MVP project-bound adapter shape for using Claude Code CLI as an external reviewer provider.

Important policy:

- Claude external review is in v0.2 MVP scope.
- API-key based Claude usage is forbidden for the v0.2 MVP.
- The adapter is intended for local subscription-based Claude Code CLI usage only.
- The wrapper must fail if configured forbidden Claude API/proxy environment
  variables are present in the process environment or Claude settings files.
- The v0.2 default reviewer invocation uses Claude Code `--model opus --effort max`.
- Claude output remains candidate findings and must be validated by the main/orchestrating agent.
- The reviewer receives a bounded review packet and must not modify files or run tests.

Files:

- `claude-code.yaml` — provider configuration.
- `review-packet.architecture.json` — sample input packet.
- `mock-raw-output.json` — sample provider output used for smoke tests without calling Claude.
- `reviewer-invocation.claude-architecture.json` — sample invocation metadata.

Example smoke invocation:

```bash
python3 scripts/reviewers/run_external_reviewer.py \
  --provider claude-code \
  --config examples/external-reviewers/claude-code/claude-code.yaml \
  --input examples/external-reviewers/claude-code/review-packet.architecture.json \
  --mock-response examples/external-reviewers/claude-code/mock-raw-output.json \
  --output /tmp/reviewer-report.claude-architecture.json
```
