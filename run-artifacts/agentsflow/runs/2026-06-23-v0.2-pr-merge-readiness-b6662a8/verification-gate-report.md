# Verification Gate Report

- Run id: `2026-06-23-v0.2-pr-merge-readiness-b6662a8`
- Material change id: `b6662a8`
- Target content head: `b6662a8c052448bacd4b1312d457f8a75a424a97`
- `.venv/bin/python scripts/validate_repo.py --root .` -> passed
- `.venv/bin/python -m pytest -q` -> `235 passed`
- `git diff --check main..HEAD` -> passed
- `git status --short` -> clean before this run artifact directory was created

The final gate is rerun because commit `b6662a8` was created after the
previous PR readiness evidence for `daed76c`.

## Evidence Refresh

Structured command evidence was refreshed after reviewer candidate `ARCH-P1-002`; `evidence/command-evidence.json` now records cwd, started_at, finished_at, exit_code, result, output_summary, artifact_paths and raw_log_path for the gate-supporting commands.
