# External Reviewer Provider Model

AgentsFlow may use external model providers as read-only reviewer providers. In
v0.2 this is a project-bound capability, not a generic provider runtime.

## Supported Provider

The v0.2 MVP provider is Claude Code CLI:

- provider id: `claude-code`;
- billing/auth mode: subscription-local Claude Code CLI only;
- API-key usage: forbidden;
- Codex launch requirement: `execution.sandbox_mode: require_escalated`;
- permission mode: `default`;
- model/effort: `opus` / `max`;
- reviewer authority: read-only candidate findings only.

Wrappers must fail if configured forbidden Claude API/proxy environment routes
are present:

```text
ANTHROPIC_API_KEY
ANTHROPIC_AUTH_TOKEN
ANTHROPIC_BASE_URL
CLAUDE_CODE_USE_BEDROCK
CLAUDE_CODE_USE_VERTEX
```

## Wrapper

External review evidence must be produced through the project-bound helper:

```bash
scripts/reviewers/run_external_review_lite.py
```

Do not call `claude` directly for workflow evidence. The helper records the
review input boundary, provider config hash, normalized report, and invocation
metadata together.

Example:

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
included.

## Context Boundary

External review uses a lite review bundle:

- `external-review-lite-request.json`;
- generated branch diff;
- explicit included artifact snapshots;
- optional staged/unstaged tracked diffs;
- hash records for referenced artifacts;
- generated prompt file;
- normalized reviewer report;
- `external-review-lite-invocation.json`.

The reviewer starts from fresh context and must use only the generated review
bundle and referenced artifacts. This is an evidence and policy boundary, not an
operating-system sandbox claim.

The wrapper invokes Claude Code with file prompt transport and `--tools Read`.
The reviewer must not modify files, run tests, execute scripts, produce
patches, or update evidence.

## Output

External reviewer output is candidate evidence, not authority.

The wrapper normalizes provider output into `schemas/reviewer-report.schema.json`
and records invocation metadata using
`schemas/external-review-lite-invocation.schema.json`.

Raw provider output is stored only when explicitly classified as non-sensitive
through provider config. Otherwise, store a redacted artifact, summary, pointer,
or omission reason.

## Review Gate Semantics

External reviewers do not replace verification gates. Their findings remain
candidate findings until the main/orchestrating agent validates relevance,
blocker path, acceptance impact, and mandatory evidence gaps.

Provider/model diversity is proved by declared reviewer requirements,
invocation metadata, and reviewer reports. It is not inferred from role names
alone.

## Non-Goals

v0.2 does not include:

- a generic multi-provider reviewer runtime;
- API-key Claude usage;
- write-enabled external reviewers;
- external reviewers running verification gates or tests;
- a separate sealed review dispatcher.
