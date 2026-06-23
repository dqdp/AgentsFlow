# Hygiene Slice Report

Run: `2026-06-21-pr-merge-readiness`
Material change: `pr-merge-readiness-hygiene-v18`
Date: `2026-06-22`

## Scope

This is a narrow source-noise cleanup after the accepted
`pr-merge-readiness` development result and before commit.

The slice does not change the accepted workflow design. It focuses on reducing
maintainability noise and improving blocker-label precision in the readiness
evaluator and review artifact preparation path.

## Changes

- Extracted reusable human-decision artifact matching from
  `scripts/repo_validation/pr_merge_readiness.py`.
- Extracted live raw-output persistence validation from the main
  `evaluate_pr_merge_readiness_report` body.
- Extracted final readiness state classification from the evaluator body.
- Fixed raw-output hash triage order so a missing raw hash reports
  `external_review_invocation_missing_raw_output_hash` instead of a generic hash
  mismatch.
- Added a regression test for missing raw-output hash labeling.
- Treated `review_packet_path` as a homogeneous-dual packet envelope field in
  review artifact preparation and validation.
- Regenerated the review packet/preparation artifacts for a short two-Codex
  hygiene review gate.

## Verification

| Check | Result |
|---|---|
| `.venv/bin/python -m pytest tests/test_pr_merge_readiness.py -q` | `66 passed` |
| `.venv/bin/python scripts/validate_repo.py --root .` | passed |
| `.venv/bin/python -m pytest tests/test_scripts_smoke.py -q` | `152 passed` |
| `.venv/bin/python -m pytest -q` | `218 passed` |
| `make check` | passed |
| `git diff --check` | passed |

## Review Plan

Run a short Codex-only homogeneous-dual review gate:

- `hygiene-codex-generalist-a`
- `hygiene-codex-generalist-b`

Reviewers are read-only and must not run tests or modify files. Their findings
remain candidate findings until main-agent validation.
