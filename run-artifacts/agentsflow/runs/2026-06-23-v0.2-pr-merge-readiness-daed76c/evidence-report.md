# Evidence Report: v0.2 PR Merge Readiness

Status: `passed-deterministic-evidence`

## Scope

- Base branch: `main`
- Base commit: `aa4374a`
- Target branch: `v0.2-prehandoff-design`
- Target content head: `daed76c`
- Commit range: `main..daed76c`
- Current run artifacts are acceptance evidence and are not methodology source.

## Structured Command Evidence

Structured command evidence is recorded in `evidence/command-evidence.json`.

| Command | Result | Durable evidence |
|---|---|---|
| `.venv/bin/python scripts/validate_repo.py --root .` | pass | `evidence/command-outputs/validate-repo.txt` |
| `.venv/bin/python -m pytest -q` | pass, 228 tests | `evidence/command-outputs/pytest.txt` |
| `git diff --check main..HEAD` | pass | `evidence/command-outputs/diff-check-main-head.txt` |
| external reviewer wrapper mock smoke | pass | `evidence/command-outputs/mock-claude-reviewer-report.json` and invocation metadata |

## External Reviewer Smoke Evidence

- Mock normalized report: `evidence/command-outputs/mock-claude-reviewer-report.json`
- Invocation metadata: `evidence/command-outputs/mock-claude-reviewer-report.invocation.json`
- Raw mock provider output: `evidence/command-outputs/mock-claude-reviewer-report.raw.json`
- This proves wrapper/provider normalization path only. It is not a substitute
  for live Claude review in the provider-mirrored review phase.

## Live Provider-Mirrored Review Evidence

- Invocation set: `review-invocation-set.json`
- Invocation set status: `completed`
- Provider/model families: `internal-agent/codex`, `claude-code/opus`
- Live Claude reviewers:
  - `verification-claude`
  - `architecture-claude`
  - `adversarial-claude`
- All Claude invocations used `execution_mode: real`, requested model `opus`,
  requested effort `max` and exit code `0`.

Raw Claude provider output is not committed as run evidence. The closing external
reviewer invocations used project-bound config
`normalization.preserve_raw_output: false`; committed summary artifacts are
stored at:

- `evidence/raw/verification-claude.summary.md`
- `evidence/raw/architecture-claude.summary.md`
- `evidence/raw/adversarial-claude.summary.md`

## Evidence Freshness

- Deterministic evidence was collected after target content head `daed76c`.
- The working tree was clean before this fresh run's artifacts were created.
