# PR Merge Readiness

`pr-merge-readiness` is a lightweight v0.2 utility workflow / gate recipe for
deciding whether a branch is ready to open, accept or merge as a pull request.

It is not a release platform and does not merge branches or change branch state.
It also does not own a separate review-gate implementation: reviewer topology,
provider assignment, fusion and finding validation belong to the source workflow,
project binding or explicit review gate. For PR acceptance, review-gate evidence
is still mandatory. This workflow composes the produced AgentsFlow evidence,
review, finding-validation and human-decision artifacts into a branch-scoped
readiness report, then relies on the deterministic evaluator to compute
readiness.

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
- GitHub PR summary-comment publication evidence;
- human merge decision status.

Accepted merge-ready status requires fresh required review-gate evidence and a
recorded human decision. Green checks without review evidence are blocked;
green checks plus review evidence alone produce `awaiting_human_decision`, not
acceptance.
An accepted human decision must point to a human-authored decision record with a
matching `run_id`, `decision_id`, `answered_by: human`, `status: confirmed` and
accepted answer. For `merge.acceptance`, the decision record must also bind the
accepted artifact by `material_change_id` and the exact readiness report
`report_hash`. An in-band `{status: accepted}` field is not sufficient.

The readiness summary must be published back to the GitHub PR before the run can
enter `awaiting_human_decision`. Publication evidence is part of the readiness
proof: green checks and clean review evidence without the PR comment remain
blocked as missing evidence.

The readiness evaluator treats these surfaces as blocking:

- any deterministic check whose `status` is not `pass`;
- any review whose `status` is not `pass` or `pass-with-notes`;
- malformed or stale review timestamps;
- review packets whose `run_id` or `material_change_id` do not match the
  evaluated readiness report;
- missing or mismatched hash-bound review requirements source;
- omitted declared required review entries;
- missing live Claude invocation evidence for a Claude-backed review;
- mock or failed external reviewer invocation metadata when live Claude evidence
  is required;
- live Claude invocation hashes that do not match the declared review input,
  output schema or normalized report;
- accepted or `needs-more-evidence` validated P0/P1 findings with a grounded
  blocker path, or mandatory evidence gaps;
- P0/P1 source findings represented as lower-severity or duplicate candidate
  findings without blocker-path calibration;
- rejected or downgraded plausible blocker-path candidate findings without
  completed collision-control evidence from two control reviewers that explicitly
  address the same collision batch and disputed finding, support the orchestrator
  disposition, bind the source reviewer report by path and SHA-256 hash, and are
  fresh after the latest material change;
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
- missing, requested, skipped, failed or malformed GitHub PR summary-comment
  publication evidence;
- self-application reports that claim the bootstrap run proves itself.

## Review Evidence

`pr-merge-readiness` consumes review evidence produced by the source workflow,
project binding or an explicit review gate. It does not remove review gates from
PR acceptance; it keeps their execution separate from the final readiness
evaluator. The evidence producer owns reviewer count, topology, provider
assignment, fusion and finding validation.

The readiness report must bind `review_requirements.required_reviews` to a
source artifact using `review_requirements.source.path` and
`review_requirements.source.artifact_hash`. That source artifact is the
normalized review-requirements output of the source workflow, project binding or
explicit review gate. The evaluator compares the report's declared required
reviews with that source artifact before it evaluates reviewer packet/report
evidence.

Readiness records PR facts, deterministic check evidence, reviewer packet/report
references, finding validation and the final readiness report. Internal
reviewers are bound by schema-valid reviewer reports, current review context and
fresh timestamps. Claude-backed reviewers are bound by normalized reviewer
reports and live lite invocation metadata.

## Report Validation

Readiness reports use:

```text
schemas/pr-merge-readiness-report.schema.json
templates/pr-merge-readiness-report.json
```

The deterministic repository validator checks curated example readiness reports
and must be invoked with the concrete run report for real PR readiness gates:

```bash
python3 scripts/validate_repo.py --root . --pr-merge-readiness-report <path>
```

The final human merge decision is content-bound, not only path-bound. The
`human-decisions.yaml#merge.acceptance` record must use
`phase_id: final_human_merge_decision` and reference the evaluated readiness
report, the current `material_change_id` and the report's SHA-256 hash using
`report_hash: sha256:<64-hex-digest>`. Non-binding preliminary discussion is not
sufficient for accepted merge-ready status. A report may have been generated
before that decision was recorded; the evaluator computes the final state from
the report plus the external hash-bound human decision record.

Before `awaiting_human_decision`, the default publication mode is a single PR
summary comment:

```yaml
publication_mode: summary_comment
required_for_merge_readiness: true
target: pull_request
pr: 123
tool: gh
action: pr comment
body_path: github-publication.md
body_hash: sha256:<64-hex-digest>
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

`github-publication-result.json` records the publication result:

```json
{
  "provider": "github",
  "tool": "gh",
  "action": "pr comment",
  "status": "published",
  "pr": 123,
  "url": "https://github.com/org/repo/pull/123#issuecomment-...",
  "body_path": "github-publication.md",
  "body_hash": "sha256:<64-hex-digest>"
}
```

The readiness evaluator requires this default evidence shape before
`awaiting_human_decision`. The report's branch repository and PR number,
publication PR number, result PR number, GitHub issue-comment URL and body hash
must match. Any other publication state blocks merge readiness as missing
publication evidence.

Each review packet must be anchored to the evaluated readiness report: packet
`run_id` must match report `run_id`, and packet `material_change_id` must match
report `material_change_id`. Review packets must also retain valid references
to their verification gate report, role contract and output schema. Internal
reviewer reports must carry matching `review_context` for the same run, material
change, packet path and reviewer id.
Collision-control reports must also be bound to their control review packet and
the same evaluated run/material change before they can clear a rejected or
downgraded blocker.

The evaluator is intentionally small. It checks declared artifacts and computes
the readiness state from the report. It validates review and external-provider
evidence directly from the report references. It does not run CI, launch
reviewers, run fusion, validate findings from scratch, call GitHub/GitLab or
perform merges.

Reports marked with `fixture.not_real_readiness_evidence: true` are schema and
evaluator fixtures only. The evaluator returns `incomplete` for them rather than
real merge readiness.

## Self-Application Boundary

When AgentsFlow applies this workflow to itself, the report must not claim
cyclic self-proof. A bootstrap run may produce and validate the workflow, but the
first real use of `pr-merge-readiness` is a later acceptance or merge readiness
run over an already implemented slice.
