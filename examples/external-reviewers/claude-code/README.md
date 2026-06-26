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
- The reviewer receives a bounded lite review bundle and must not modify files or run tests.

Files:

- `claude-code.yaml` — provider configuration.
- `mock-raw-output.json` — sample provider output used for smoke tests without calling Claude.

Example smoke invocation:

```bash
python3 scripts/reviewers/run_external_review_lite.py \
  --provider claude-code \
  --config examples/external-reviewers/claude-code/claude-code.yaml \
  --output-dir /tmp/external-review-lite \
  --goal "Smoke-test external reviewer normalization." \
  --run-id external-reviewer-smoke \
  --base-ref HEAD \
  --head-ref HEAD \
  --include-uncommitted \
  --mock-response examples/external-reviewers/claude-code/mock-raw-output.json \
  --replace-output-dir
```
