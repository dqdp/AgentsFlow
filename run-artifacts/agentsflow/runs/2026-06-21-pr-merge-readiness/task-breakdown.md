# Task Breakdown

## Tasks

| ID | Task | Depends on | Parallel? | Acceptance Evidence |
|----|------|------------|-----------|---------------------|
| PRM-T1 | Add red-capture tests for readiness report semantics. | contract_acceptance | no | Failing `tests/test_pr_merge_readiness.py` red report. |
| PRM-T2 | Implement report schema, template and validator helper. | PRM-T1 | no | Green targeted tests. |
| PRM-T3 | Add example artifacts for PR merge readiness. | PRM-T2 | yes | `validate_repo` accepts example. |
| PRM-T4 | Add utility workflow definition and provider-mirrored review policy. | PRM-T2 | yes | `validate_repo` accepts workflow. |
| PRM-T5 | Add docs integration. | PRM-T3, PRM-T4 | yes | README/workflow model/MVP standard references are consistent. |
| PRM-T6 | Run green verification and prepare proportional BFCF development review packet. | PRM-T1-PRM-T5 | no | Green verification report and three-reviewer development review artifacts: Codex generalist, Claude generalist, Codex authority specialist. |

## Checkpoints

- Contract and impact map validated.
- Plan gate passed.
- Human `contract_acceptance` recorded.
- Red-capture failing evidence recorded.
- Green verification passed after implementation.
- Proportional BFCF development review gate completed.
- Target workflow provider-mirrored review policy validated.

## Verification Commands

- `.venv/bin/python scripts/validate_repo.py --root .`
- `.venv/bin/python -m pytest -q`
- `make check`
- `.venv/bin/python scripts/reviewers/run_external_reviewer.py --provider claude-code --config examples/external-reviewers/claude-code/claude-code.yaml --input examples/external-reviewers/claude-code/review-packet.architecture.json --mock-response examples/external-reviewers/claude-code/mock-raw-output.json --output /tmp/reviewer-report.pr-merge-readiness-smoke.json`
- `git diff --check main`
