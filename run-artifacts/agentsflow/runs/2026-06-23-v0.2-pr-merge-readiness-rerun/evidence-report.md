# Evidence Report: v0.2 PR Merge Readiness Rerun

Status: `blocked-after-review`

## Scope

- Base branch: `main`
- Base commit: `aa4374a`
- Target branch: `v0.2-prehandoff-design`
- Target content head: `8a2c197`
- Commit range: `main..8a2c197`
- Current run artifacts are acceptance evidence and are not methodology source.
- This run is blocked and must not be used as PR acceptance evidence. It is
  retained as bounded diagnostic evidence for the follow-up fix committed as
  `6277b92`.

## Structured Command Evidence

Structured command evidence is recorded in
`evidence/command-evidence.json`.

| Command | Result | Durable evidence |
|---|---|---|
| `.venv/bin/python scripts/validate_repo.py --root .` | pass | `evidence/command-outputs/validate-repo.txt` |
| `.venv/bin/python -m pytest -q` | pass, 226 tests | `evidence/command-outputs/pytest.txt` |
| `git diff --check main..HEAD` | pass | `evidence/command-outputs/diff-check-main-head.txt` |
| external reviewer wrapper mock smoke | pass | `evidence/command-outputs/mock-claude-reviewer-report.json` and invocation metadata |

## External Reviewer Smoke Evidence

- Mock normalized report:
  `evidence/command-outputs/mock-claude-reviewer-report.json`
- Invocation metadata:
  `evidence/command-outputs/mock-claude-reviewer-report.invocation.json`
- Raw mock provider output:
  `evidence/command-outputs/mock-claude-reviewer-report.raw.json`
- This proves wrapper/provider normalization path only. It is not a substitute
  for live Claude review in the provider-mirrored review phase.

## Fix Evidence

- The previous range whitespace failure is fixed: `git diff --check main..HEAD`
  exits `0`.
- Failed external reviewer invocation metadata is now schema-valid evidence, but
  failed invocations are not counted as completed external review evidence.
- External reviewer prompts now require exactly one schema-valid
  reviewer-report JSON object, with no prose outside JSON.

## Evidence Freshness

- Deterministic evidence was collected after target content head `8a2c197`.
- The working tree was clean before this fresh run's artifacts were created.

## Review Outcome

- Provider-mirrored review did not complete for target content head `8a2c197`.
- The three internal Codex reviewers produced candidate P1 findings.
- The three live Claude invocations completed but failed provider-output
  processing because the wrapper could not normalize schema-adjacent structured
  output into reviewer-report JSON.
- External invocation metadata from that blocked attempt is archived under
  `evidence/stale-external-invocations/8a2c197/`; raw Claude output remains
  ignored diagnostic material.
