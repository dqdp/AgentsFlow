# Verification Gate Report

Run: `2026-06-21-pr-merge-readiness`
Workflow: `big-feature-contract-first`
Target feature: `pr-merge-readiness`
Phase: `verification_gate`
Result: `pass`

## Checks

| Check | Command | Result |
|---|---|---|
| Red-capture targeted tests | `.venv/bin/python -m pytest tests/test_pr_merge_readiness.py -q` before implementation | failed as expected, 10 failed |
| Post-review raw persistence red test | `.venv/bin/python -m pytest tests/test_pr_merge_readiness.py::test_live_external_output_not_persisted_blocks_readiness -q` before fix | failed as expected |
| Post-review authority/evidence red tests | `.venv/bin/python -m pytest tests/test_pr_merge_readiness.py::test_redacted_live_external_output_requires_redacted_artifact tests/test_pr_merge_readiness.py::test_redacted_live_external_output_does_not_require_raw_provider_artifact tests/test_pr_merge_readiness.py::test_fixture_report_is_not_real_merge_readiness tests/test_pr_merge_readiness.py::test_unsupported_collision_control_conclusion_does_not_clear_rejected_blocker tests/test_pr_merge_readiness.py::test_collision_control_report_before_prompt_preparation_does_not_clear_rejected_blocker -q` before fix | failed as expected |
| Post-review raw policy and review-set red tests | `.venv/bin/python -m pytest tests/test_pr_merge_readiness.py::test_redacted_live_external_output_rejects_persisted_raw_provider_artifact tests/test_pr_merge_readiness.py::test_invalid_claude_provider_config_blocks_readiness tests/test_scripts_smoke.py::test_review_prompt_contract_binds_external_invocation_to_current_artifacts -q` before fix | failed as expected |
| Post-review raw source and human replay red tests | `.venv/bin/python -m pytest tests/test_pr_merge_readiness.py -q -k "normalization_raw_source or material_change_and_report_hash"` before fix | failed as expected, 3 failed |
| Targeted green tests | `.venv/bin/python -m pytest tests/test_pr_merge_readiness.py -q` | passed, 65 passed |
| Review-set runner/preparation/wrapper smoke tests | `.venv/bin/python -m pytest tests/test_scripts_smoke.py -q` | passed, 152 passed |
| Repository validation | `.venv/bin/python scripts/validate_repo.py --root .` | passed |
| Full pytest | `.venv/bin/python -m pytest -q` | passed, 217 passed |
| Make check | `make check` | passed |
| External reviewer mock smoke | `.venv/bin/python scripts/reviewers/run_external_reviewer.py --provider claude-code --config examples/external-reviewers/claude-code/claude-code.yaml --input examples/external-reviewers/claude-code/review-packet.architecture.json --mock-response examples/external-reviewers/claude-code/mock-raw-output.json --output /tmp/reviewer-report.pr-merge-readiness-smoke.json` | passed |
| Diff whitespace | `git diff --check` | passed |

## Scenario Coverage

- `PRM-BHV-001`: complete evidence and human decision can produce accepted merge-ready status.
- `PRM-BHV-002`: green evidence without human decision remains `awaiting_human_decision`.
- `PRM-BHV-003`: missing evidence blocks readiness.
- `PRM-BHV-004`: mock, omitted, or mock-invocation Claude evidence is not live Claude evidence.
- `PRM-BHV-005`: redacted sensitive raw output requires a redaction reason,
  required live external evidence cannot be accepted with `raw_output.persistence:
  not_persisted`, non-sensitive raw persistence requires matching raw
  output path/hash, and redacted, summary or pointer persistence requires a
  concrete artifact path/hash and no persisted raw provider output path or
  normalization source path.
- `PRM-BHV-006`: accepted or needs-more-evidence P0/P1 findings block readiness; rejected or downgraded P0/P1 candidate findings require complete collision-control.
- `PRM-BHV-007`: stale, stale-bound, malformed, mixed-timezone or missing-context review evidence is blocked.
- `PRM-BHV-008`: self-application bootstrap cannot claim cyclic self-proof, and
  reports marked as non-real fixture evidence cannot compute real merge
  readiness.
- `PRM-BHV-009`: failed checks and failed or blocked reviews block readiness.
- `PRM-BHV-010`: accepted human decisions require exactly one schema-valid matching human-authored final merge decision record for the exact evaluated report artifact, current material change and report hash.
- `PRM-BHV-011`: required review topology entries cannot be omitted, underdeclared, `required_live`-misdeclared or role-misbound.
- `PRM-BHV-012`: schema-valid reviewer reports are parsed and P0/P1 source findings must enter candidate finding triage with reviewer/source identity, without lower-severity, duplicate, or local-id collision bypass.
- `PRM-BHV-013`: Claude invocation metadata must be bound to the claimed review role, packet, prompt, prompt contract, role contract, rubric, schema, output paths, output hashes, wrapper, provider config and forbidden-env guardrail evidence; plan-mode metadata is blocked.
- `PRM-BHV-014`: collision-control cannot be satisfied by arbitrary existing files, unrelated valid reports, stale control reports or self-declared control reports without a schema-valid collision-control prompt contract; control reports must be structured reviewer evidence tied to the collision batch and disputed finding.
- Review-set runner behavior: external reviewers still start asynchronously before internal reports are awaited, timeout preserves completed peers, generated packets are schema-valid before external wrapper use, stale embedded packet snapshots are rejected before dispatch, predeclared invocation-set evidence is created before runner execution, `run-artifacts/agentsflow/runs` review artifacts are scanned, Claude string verification requests normalize into schema-compatible objects, internal reviewer concrete model labels can satisfy declared model families, internal reviewer reports must carry full current review context (`run_id`, material change, packet path and reviewer instance), and long external/internal waits now emit progress heartbeat lines on stderr.
- External reviewer wrapper behavior: `normalization.preserve_raw_output: false`
  keeps deterministic normalization and invocation hashes but does not persist
  raw provider output as a run artifact.
- Review-set evidence behavior: completed Claude review-set evidence may omit a
  raw provider output path when raw persistence is intentionally disabled, while
  non-empty raw paths remain hash-bound.

## Notes

This gate did not run a live Claude review. The external reviewer smoke used the
existing mock response and is recorded only as CI-safe wrapper evidence. Live
Claude review belongs to the following development review gate.
