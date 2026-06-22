# Red Capture Report

Run: `2026-06-21-pr-merge-readiness`
Workflow: `big-feature-contract-first`
Target feature: `pr-merge-readiness`
Phase: `red_capture`
Status: `captured`

## Command

```bash
.venv/bin/python -m pytest tests/test_pr_merge_readiness.py -q
```

## Result

Failed as expected before implementation.

Summary:

- `10 failed`
- `repo_validation.pr_merge_readiness` is missing.
- `workflows/pr-merge-readiness/workflow.yaml` is missing.
- `examples/pr-merge-readiness/complete/pr-merge-readiness-report.json` is missing.

## Covered Bindings

- `PRM-BHV-001`: complete evidence can produce an accepted merge-ready decision only with a recorded human decision.
- `PRM-BHV-002`: green evidence without a human merge decision remains `awaiting_human_decision`.
- `PRM-BHV-003`: missing required evidence blocks readiness and records missing paths.
- `PRM-BHV-004`: mock external review evidence is not treated as live Claude evidence.
- `PRM-BHV-005`: redacted sensitive raw external review output requires a redaction reason.
- `PRM-BHV-006`: rejected or downgraded P0/P1 findings require collision-control evidence.
- `PRM-BHV-007`: review packets older than material changes are stale and excluded.
- `PRM-BHV-008`: self-application bootstrap must not claim cyclic self-proof.

Additional structural expectations:

- `pr-merge-readiness` has a workflow manifest marked as a v0.2 utility workflow.
- Target workflow review policy uses provider-mirrored heterogeneous topic pairs.
- A complete example readiness report validates through the deterministic repository validator.

## Implementation Authorization

This report captures failing red evidence. The next phase may implement the
narrow accepted slice needed to make these tests pass without expanding into PR
mutation, release automation, generic CI providers or external reviewer provider
rewrites.
