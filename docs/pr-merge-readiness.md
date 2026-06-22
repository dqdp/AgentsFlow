# PR Merge Readiness

`pr-merge-readiness` is a v0.2 utility workflow for deciding whether a branch is
ready to open, accept or merge as a pull request.

It is not a release platform and does not mutate Git hosts. It composes existing
AgentsFlow evidence, review, fusion, finding-validation and human-decision
artifacts into a branch-scoped readiness report.

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
- human merge decision status.

Accepted merge-ready status requires a recorded human decision. Green checks and
review evidence alone produce `awaiting_human_decision`, not acceptance.
An accepted human decision must point to a human-authored decision record with a
matching `run_id`, `decision_id`, `answered_by: human`, `status: confirmed` and
accepted answer. For `merge.acceptance`, the decision record must also bind the
accepted artifact by `material_change_id` and the exact readiness report
`report_hash`. An in-band `{status: accepted}` field is not sufficient.

The readiness evaluator treats these surfaces as blocking:

- any deterministic check whose `status` is not `pass`;
- any review whose `status` is not `pass` or `pass-with-notes`;
- malformed or stale review timestamps;
- review packets whose `run_id` or `material_change_id` do not match the
  evaluated readiness report;
- omitted provider-mirrored target review topology entries;
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
- self-application reports that claim the bootstrap run proves itself.

## Review Model

The target review topology is `heterogeneous-variable` with provider-mirrored
topic pairs:

| Topic | Role | Providers |
|---|---|---|
| `verification-evidence` | `verification` | `internal-agent`, `claude-code` |
| `architecture-process` | `architecture` | `internal-agent`, `claude-code` |
| `adversarial-authority` | `adversarial` | `internal-agent`, `claude-code` |

The mirrored pair shape is a target workflow policy. A workflow used to develop
`pr-merge-readiness` may choose a smaller development review gate when its own
contract records that decision.

## Report Validation

Readiness reports use:

```text
schemas/pr-merge-readiness-report.schema.json
templates/pr-merge-readiness-report.json
```

The deterministic repository validator checks example readiness reports through
`scripts/repo_validation/pr_merge_readiness.py`.

The human merge decision is content-bound, not only path-bound. The
`human-decisions.yaml#merge.acceptance` record must reference the evaluated
readiness report, the current `material_change_id` and the report's SHA-256 hash
using `report_hash: sha256:<64-hex-digest>`.

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
