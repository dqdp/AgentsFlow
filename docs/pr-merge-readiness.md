# PR Merge Readiness

`pr-merge-readiness` is a v0.2 utility workflow for deciding whether a branch is
ready to open, accept or merge as a pull request.

It is not a release platform and does not merge branches or change branch state.
It composes existing AgentsFlow evidence, review, fusion, finding-validation and
human-decision artifacts into a branch-scoped readiness report. When explicitly
requested by the human, it may publish the readiness summary as a GitHub PR
comment and record that publication evidence.

## Scope

The workflow records:

- branch, base branch, commit range and worktree state;
- the readiness run id and current `material_change_id`;
- deterministic check evidence, such as repository validation and tests;
- review packet and reviewer report references;
- external reviewer evidence, including live-vs-mock Claude distinction;
- finding validation and collision-control evidence for rejected or downgraded
  plausible blocker-path candidate findings;
- stale review detection when material changes postdate review packets;
- human merge decision status;
- optional GitHub PR publication intent and evidence.

Accepted merge-ready status requires a recorded human decision. Green checks and
review evidence alone produce `awaiting_human_decision`, not acceptance.
An accepted human decision must point to a human-authored decision record with a
matching `run_id`, `decision_id`, `answered_by: human`, `status: confirmed` and
accepted answer. For `merge.acceptance`, the decision record must also bind the
accepted artifact by `material_change_id` and the exact readiness report
`report_hash`. An in-band `{status: accepted}` field is not sufficient.

The readiness summary may be published back to the GitHub PR after final
acceptance. This publication is optional and does not block merge readiness when
it is omitted, skipped, deferred, requested but not yet performed, failed or
unavailable.

Because the final report hash is only known near the end of the run,
`pr-merge-readiness` keeps publication outside the acceptance proof. After
review and finding validation, the run produces the readiness report, records the
final `merge.acceptance` decision with the exact `report_hash`, runs the final
readiness validation, and may then perform optional GitHub publication.

The readiness evaluator treats these surfaces as blocking:

- any deterministic check whose `status` is not `pass`;
- any review whose `status` is not `pass` or `pass-with-notes`;
- malformed or stale review timestamps;
- review packets whose `run_id` or `material_change_id` do not match the
  evaluated readiness report;
- omitted required review topology entries;
- missing live Claude invocation evidence for a Claude-backed review;
- mock or failed external reviewer invocation metadata when live Claude evidence
  is required;
- live Claude invocation hashes that do not match the current packet, prompt,
  role contract, prompt contract, rubric, output schema or normalized report;
- accepted or `needs-more-evidence` validated P0/P1 findings with a grounded
  blocker path, or mandatory evidence gaps;
- P0/P1 source findings represented as lower-severity or duplicate candidate
  findings without blocker-path calibration;
- rejected or downgraded plausible blocker-path candidate findings without
  completed collision-control evidence from two control reviewers that explicitly
  address the same collision batch and disputed finding, support the orchestrator
  disposition, and complete after the collision-control prompt is prepared;
- sensitive raw external output without redaction or non-sensitive declaration;
- required live external evidence whose raw output is declared `not_persisted`
  instead of non-sensitive raw output or a redacted/summary/pointer artifact;
- live Claude invocation metadata whose recorded raw output path or hash does
  not match the local run evidence when raw output is explicitly persisted as
  non-sensitive;
- live Claude invocation or reviewer-report normalization metadata that records
  a raw output path while the readiness report declares redacted, summary or
  pointer persistence;
- redacted, summary or pointer raw-output evidence without a concrete artifact
  path and hash;
- claimed published GitHub publication without recorded publication result
  evidence and URL;
- self-application reports that claim the bootstrap run proves itself.

## Review Model

The default review topology is `homogeneous-plus-focused`: `generalist-a`,
`generalist-b` and one explicit adversarial reviewer. Project bindings may
escalate to `heterogeneous-variable` when selected risk surfaces justify more
reviewers or provider diversity. Provider assignment belongs in the project
binding or review invocation set, not in this workflow's default reviewer list.

## Report Validation

Readiness reports use:

```text
schemas/pr-merge-readiness-report.schema.json
templates/pr-merge-readiness-report.json
```

The deterministic repository validator checks example readiness reports through
`scripts/repo_validation/pr_merge_readiness.py`.

The final human merge decision is content-bound, not only path-bound. The
`human-decisions.yaml#merge.acceptance` record must use
`phase_id: final_human_merge_decision` and reference the evaluated readiness
report, the current `material_change_id` and the report's SHA-256 hash using
`report_hash: sha256:<64-hex-digest>`. Non-binding preliminary discussion is not
sufficient for accepted merge-ready status. A report may have been generated
before that decision was recorded; the evaluator computes the final state from
the report plus the external hash-bound human decision record.

If publication runs, the default publication mode is a single PR summary
comment:

```yaml
publication_mode: summary_comment
target: pull_request
tool: gh
action: pr comment
body_path: github-publication.md
result_path: github-publication-result.json
```

`github-publication.md` contains the exact comment body. It should summarize:

- AgentsFlow PR readiness status;
- material change / commit SHA;
- deterministic verification evidence;
- review topology and provider/model evidence;
- validated P0/P1 count;
- short P2/residual-risk summary;
- human decision and publication mode;
- note that local run artifacts remain the source of truth.

It must not include raw Claude output, full reviewer reports, long command logs,
private reasoning details or unnecessary absolute local paths.

If publication runs, `github-publication-result.json` records the publication
result:

```json
{
  "provider": "github",
  "tool": "gh",
  "action": "pr comment",
  "status": "published",
  "pr": 123,
  "url": "https://github.com/org/repo/pull/123#issuecomment-...",
  "body_path": "github-publication.md"
}
```

When the report claims `github_publication.status: published`, the readiness
evaluator requires this default evidence shape. Other publication states do not
block merge readiness.

Each review packet must be anchored to the evaluated readiness report: packet
`run_id` must match report `run_id`, and packet `material_change_id` must match
report `material_change_id`. Internal reviewer reports must also carry matching
`review_context` for the same run, material change, packet path and reviewer id.

The evaluator is intentionally small. It checks declared artifacts and computes
the readiness state from the report. It validates external reviewer invocation
metadata shape for live Claude evidence, but it does not run CI, launch
reviewers, call GitHub/GitLab or perform merges.

Reports marked with `fixture.not_real_readiness_evidence: true` are schema and
evaluator fixtures only. The evaluator returns `incomplete` for them rather than
real merge readiness.

## Self-Application Boundary

When AgentsFlow applies this workflow to itself, the report must not claim
cyclic self-proof. A bootstrap run may produce and validate the workflow, but the
first real use of `pr-merge-readiness` is a later acceptance or merge readiness
run over an already implemented slice.
