# Evidence Report

Run: `2026-06-21-pr-merge-readiness`
Workflow: `big-feature-contract-first`
Target feature: `pr-merge-readiness`

## Changed Areas

- Added `pr-merge-readiness` utility workflow manifest.
- Added readiness report schema, template and complete example.
- Added deterministic readiness report evaluator and repository validation hook.
- Added focused red/green tests for readiness semantics, including failed
  check/review statuses, live external invocation metadata, blocker finding
  statuses, collision-control completeness, human decision record matching,
  required review topology, reviewer-report source finding intake and Claude
  invocation role/packet/prompt/schema/path/hash binding.
- Added `run_review_set.py` external-reviewer heartbeat progress output on stderr
  so long Claude invocations expose dispatch/running/completion state without
  streaming provider stdout.
- Added prepared review-packet schema validation coverage so missing required
  packet fields are caught before live external reviewer invocation.
- Added role-binding checks for required provider-mirrored PR review topics:
  `required_reviews[].role`, review `role_contract_path`, reviewer-report
  `reviewer.role` and Claude invocation `reviewer_role` must align.
- Added `run-artifacts/agentsflow/runs` review-artifact scanning so
  self-application run packets/contracts are validated like documented
  `Docs/agentsflow/runs` artifacts.
- Added collision-control prompt-contract provenance checks and predeclared
  invocation-set preparation evidence for review-set runs.
- Tightened collision-control readiness evidence so prompt contracts must be
  schema-valid and both prompt/control report timestamps must not predate the
  latest material change.
- Tightened accepted human decision matching so it must target the exact
  evaluated readiness report artifact, not only a basename, and duplicate or
  superseded merge decisions fail closed.
- Tightened required Claude review evidence so `required_live` misdeclaration
  blocks accepted readiness.
- Bound live Claude invocation metadata to wrapper identity, provider config
  hash and the forbidden API/proxy environment baseline.
- Aligned PR-readiness rubric hash validation with prompt-contract rubric hashes
  emitted by the external reviewer wrapper.
- Added stale embedded file snapshot detection to review artifact preparation.
- Allowed concrete internal model labels, such as `gpt-5-codex`, to satisfy the
  declared `codex` model family in review-set evidence.
- Normalized string `requests_for_additional_verification` values from Claude
  reviewer output into schema-compatible request objects.
- Closed evaluator fail-open paths for unmapped blockers and mixed-timezone
  review timestamps.
- Added reviewer-report `review_context` binding so internal reviewer reports
  must prove the current run/material change/review packet/reviewer instance,
  preventing stale reports with matching reviewer ids from satisfying a gate.
- Tightened that binding after development review so `run_id` and
  `reviewer_instance_id` are enforced, not merely documented.
- Anchored pr-merge-readiness review packets to the evaluated readiness report
  `run_id` and `material_change_id`, blocking stale packet/report pairs that are
  internally consistent but belong to another readiness run or material change.
- Closed the post-review audit persistence blocker where required live external
  evidence could declare `raw_output.persistence: not_persisted` and still
  compute `accepted_merge_ready`.
- Closed follow-on authority/evidence blockers where collision-control could
  clear rejected/downgraded P0/P1 findings without a supporting control
  conclusion, where control reports could predate the collision-control prompt,
  where redacted live Claude output could be accepted without a concrete
  artifact path/hash, where redacted live Claude evidence incorrectly required
  raw provider output persistence, and where fixture reports could compute real
  readiness.
- Closed the accepted-decision consistency blocker where the external reviewer
  wrapper always persisted raw provider output despite DDR-007; provider configs
  now declare `normalization.preserve_raw_output`, the safe template default is
  false, and the wrapper can normalize without writing raw output.
- Closed follow-on raw-policy and review-set integration blockers where
  redacted/summary/pointer evidence could still accept a persisted raw provider
  output path, completed review-set validation still required a raw provider
  output file despite `preserve_raw_output: false`, and live Claude readiness
  evidence hash-bound but did not policy-validate the provider config.
- Closed follow-on raw-source and human-decision replay blockers where
  redacted/summary/pointer evidence could still preserve raw output through
  invocation or reviewer-report `normalization.source_path`, and where a prior
  human merge decision could be replayed after material report changes.
- Migrated the canonical `pr-merge-readiness` example and reviewer invocation
  template to redacted raw-output metadata without persisted raw paths.
- Updated v0.2 documentation to classify `pr-merge-readiness` as a utility workflow.
- Added `pr-merge-readiness` compatibility to existing evidence/reviewer/fusion skills used by the workflow.

## Verification

| Command | Result |
|---|---|
| `.venv/bin/python -m pytest tests/test_pr_merge_readiness.py -q` | passed, 65 passed |
| `.venv/bin/python -m pytest tests/test_scripts_smoke.py -q` | passed, 152 passed |
| `.venv/bin/python scripts/validate_repo.py --root .` | passed |
| `.venv/bin/python -m pytest -q` | passed, 217 passed |
| `make check` | passed |
| `.venv/bin/python scripts/reviewers/run_external_reviewer.py --provider claude-code --config examples/external-reviewers/claude-code/claude-code.yaml --input examples/external-reviewers/claude-code/review-packet.architecture.json --mock-response examples/external-reviewers/claude-code/mock-raw-output.json --output /tmp/reviewer-report.pr-merge-readiness-smoke.json` | passed |
| `git diff --check` | passed |

## Failure Path Matrix Coverage

| FPM row | Binding | Status |
|---|---|---|
| `PRM-FPM-001` | `PRM-BHV-001` | covered |
| `PRM-FPM-002` | `PRM-BHV-002` | covered |
| `PRM-FPM-003` | `PRM-BHV-003` | covered |
| `PRM-FPM-004` | `PRM-BHV-004` | covered |
| `PRM-FPM-005` | `PRM-BHV-005` | covered |
| `PRM-FPM-006` | `PRM-BHV-006` | covered |
| `PRM-FPM-007` | `PRM-BHV-007` | covered |
| `PRM-FPM-008` | `PRM-BHV-008` | covered |
| `PRM-FPM-009` | `PRM-BHV-009` | covered |
| `PRM-FPM-010` | `PRM-BHV-010` | covered |
| `PRM-FPM-011` | `PRM-BHV-011` | covered |
| `PRM-FPM-012` | `PRM-BHV-012` | covered |
| `PRM-FPM-013` | `PRM-BHV-013` | covered |
| `PRM-FPM-014` | `PRM-BHV-014` | covered |

## Boundary Check

No PR mutation, release-management runtime, CI-provider abstraction, API-key
Claude usage or external reviewer provider rewrite was added.

## Known Limitations

- The readiness evaluator validates recorded report artifacts; it does not run
  CI, launch reviewers or merge branches.
- The example contains fixture evidence. Live Claude evidence is required only
  for real local readiness runs that request it.
