# Process Retrospective

Run: `2026-06-21-pr-merge-readiness`
Workflow used: `big-feature-contract-first`
Target: `pr-merge-readiness` utility workflow
Date: `2026-06-22`

## Summary

The workflow produced a useful and well-tested `pr-merge-readiness` slice, but
the process was heavier than ideal. The largest process issue was not a lack of
review rigor. It was the tendency to classify evidence-quality and packet-hygiene
issues as blocker-grade too early, before the orchestrating agent validated
whether they created a real false-readiness path.

The review system did its job by surfacing real risks. The orchestration process
needs sharper severity calibration so that candidate P0/P1 findings do not
automatically become work-expanding rerun triggers.

## What Worked

- Contract-first development helped keep the utility workflow narrow.
- Red/green tests were effective for turning real reviewer findings into
  deterministic checks.
- Live Claude review added useful independent pressure, especially around
  evidence traceability and stale packet cues.
- The mixed-provider gate proved that external and internal reports can be
  normalized and fused.
- The main-agent validation step prevented a candidate P1 from forcing an
  unnecessary rerun.
- The validator caught the attempted post-review `run.yaml` rewrite as a
  hash-bound evidence mismatch, which protected review integrity.

## What Was Suboptimal

### 1. Candidate Blockers Were Too Easy To Create

Some findings were classified as P1 because they touched a high-risk surface
such as evidence freshness or authority boundaries. That is too coarse.

A finding should become blocker-grade only when it shows at least one of:

- a concrete false-readiness path;
- a missing mandatory evidence artifact;
- a violated human-owned decision boundary;
- a sensitive data exposure path;
- an implementation defect that can produce an accepted result when it should
  block;
- a review/fusion path that can drop or hide a source P0/P1.

Risk-surface membership alone is not enough.

### 2. Packet Hygiene And Implementation Correctness Were Blurred

The stale `v14`/`v16` cues in the active v17 packet were real defects. They
were not equivalent to a failed implementation gate after reviewers detected
them and the structured material identifiers remained current.

The process should distinguish:

- source behavior defect;
- evidence artifact defect;
- review-packet hygiene defect;
- reviewer prompt clarity defect;
- audit metadata clarity issue.

Only the first two commonly justify blocker severity. The others can be blocker
severity only when they cause incorrect gate acceptance or make the review
non-replayable.

### 3. Review Rerun Pressure Was Too High

The process initially drifted toward "fix every relevant review finding and
rerun." That is not the intended gate rule.

The better rule is:

```text
validated P0/P1 fixed or material reviewed artifact changed -> rerun
no validated P0/P1 and no material post-review change -> pass with notes
```

This prevents review gates from becoming open-ended polish loops.

### 4. Hash-Bound Artifacts Need A Post-Review Closure Channel

`run.yaml` being part of the reviewed packet made retroactive status cleanup
invalid. That is correct, but the process needs an explicit closure artifact so
the orchestrator is not tempted to rewrite hash-bound inputs.

For future runs, final closure should be recorded in a post-review artifact such
as `final-decision-summary.md`, while reviewed packet inputs remain immutable.

### 5. Review Prompts Need Stronger Severity Calibration

Reviewers were correctly adversarial, but the prompt should make severity
thresholds more explicit:

- P0/P1 requires a demonstrated blocking path or mandatory evidence gap.
- P2 is appropriate for real traceability, packet-hygiene or audit clarity gaps
  that do not create false readiness.
- Reviewers may label a finding `candidate-P1`, but must state the exact
  condition that would make it truly blocking.
- The orchestrator validates severity before any rerun decision.

## Severity Calibration Rule Proposal

Use this blocker test during finding validation:

```text
A finding is P0/P1 only if accepting the artifact without fixing it would create
an incorrect, unsafe, unreplayable or unauthorized workflow outcome under the
current contract.
```

If the answer is "it is confusing", "it is stale wording", "it should be cleaner"
or "it weakens traceability but does not change acceptance", the default severity
should be P2/P3 unless the finding also proves a false-readiness path.

## Recommended Methodology Follow-Up

These are process improvements, not blockers for this run:

1. Add a reviewer severity-calibration paragraph to review prompt templates.
2. Add a finding-validation checklist that separates risk surface, proven path,
   materiality and rerun requirement.
3. Add a standard post-review closure artifact so hash-bound inputs are not
   rewritten after review.
4. Clarify that packet-hygiene defects are blocker-grade only when they make the
   review materially stale, non-replayable or misleading enough to invalidate
   reviewer conclusions.
5. Make "candidate P1" a first-class fusion status distinct from "validated P1".

## Process Verdict

The workflow was effective but not yet optimal.

It produced strong evidence and useful hardening, but the gate mechanics created
too much gravitational pull toward blocker escalation and rerun. The correct
direction is not weaker review; it is stricter validation of blocker severity
and a cleaner separation between candidate findings, validated findings,
follow-up backlog and rerun triggers.
