# Verification Gate Report

- Run id: `2026-06-23-pr-readiness-github-publication-focused-review-rerun`
- Material change id: `github-publication-result-url-boundary-0d705e5055e2`
- `.venv/bin/python -m pytest tests/test_pr_merge_readiness.py -q` -> `79 passed`
- `.venv/bin/python scripts/validate_repo.py --root .` -> passed
- `.venv/bin/python -m pytest -q` -> `235 passed`
- `git diff --check main..HEAD` -> passed
- Previous focused review findings were addressed by moving `github.publication`
  to readiness intake, making GitHub publication an automated post-acceptance
  action, allowing final accepted readiness to be computed from an external
  hash-bound human decision record without mutating the reviewed report, and
  requiring URL-backed `github-publication-result.json` evidence for reports
  that claim GitHub publication was already published.
