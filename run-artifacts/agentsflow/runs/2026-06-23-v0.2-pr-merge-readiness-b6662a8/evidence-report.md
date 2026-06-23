# Evidence Report

Run id: `2026-06-23-v0.2-pr-merge-readiness-b6662a8`
Material change id: `b6662a8`
Target content head: `b6662a8c052448bacd4b1312d457f8a75a424a97`
Generated at: `2026-06-23T13:06:33.763264+00:00`

## Deterministic Checks

- `.venv/bin/python scripts/validate_repo.py --root .` -> passed
- `.venv/bin/python -m pytest -q` -> `235 passed`
- `git diff --check main..HEAD` -> passed
- `git status --short` -> clean before new run artifacts were created

## GitHub Publication Readiness

- `github.publication` intake decision: `publish`
- `gh pr view --json ...` -> failed with HTTP 401; publication execution may be
  blocked until GitHub CLI authentication is restored.

## Evidence Paths

- `evidence/command-outputs/validate-repo.txt`
- `evidence/command-outputs/pytest.txt`
- `evidence/command-outputs/diff-check-main-head.txt`
- `evidence/command-outputs/gh-pr-view.txt`

## Evidence Refresh

Structured command evidence was refreshed after reviewer candidate `ARCH-P1-002`; `evidence/command-evidence.json` now records cwd, started_at, finished_at, exit_code, result, output_summary, artifact_paths and raw_log_path for the gate-supporting commands.
