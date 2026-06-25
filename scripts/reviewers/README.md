# External Reviewer Scripts

This directory contains the v0.2 MVP external reviewer helper.

## Supported Path

Use `run_external_review_lite.py` for Claude Code external review. The helper:

- builds an `external-review-lite-request.json` review bundle;
- records branch diff and explicitly included artifacts with hashes;
- optionally records staged and unstaged tracked diffs for pre-commit review;
- invokes Claude Code through the project-bound provider config;
- requires subscription-local Claude Code CLI usage;
- forbids Claude API/proxy environment routes;
- uses `execution.sandbox_mode: require_escalated`;
- uses Claude Code `--tools Read` with file prompt transport;
- normalizes provider output into `reviewer-report.json`;
- writes `external-review-lite-invocation.json` metadata.

Do not call `claude` directly for workflow evidence. Use the wrapper so the
review request, artifact hashes, normalized report, and invocation metadata are
recorded together.

## Example

```bash
python3 scripts/reviewers/run_external_review_lite.py \
  --provider claude-code \
  --config .agentsflow/external-reviewers/claude-code.yaml \
  --output-dir Docs/agentsflow/runs/<run-id>/external-review-lite \
  --goal "Review this branch for acceptance-impacting defects." \
  --run-id <run-id> \
  --base-ref main \
  --head-ref HEAD \
  --include AGENTS.md
```

For pre-commit review, stage intended new files first and pass
`--include-uncommitted`; untracked files must be staged before they can be
included in the bundle.

## Smoke Test Without Claude

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

## Non-Goals

This is not a generic multi-provider runtime, not a CI/enterprise API-key
integration, and not a write-enabled reviewer.
