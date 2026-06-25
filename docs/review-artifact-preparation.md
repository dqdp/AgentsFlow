# Review Artifact Preparation

## Status

Accepted for the provider-assigned review gate slice.

## Purpose

Review artifact preparation is an optional deterministic helper that turns
declared review policy into concrete reviewer inputs:

```text
review prompt contract draft
-> optional deterministic artifact preparation
-> prepared review packets and rendered prompts
-> review invocation set
```

The preparation step does not decide which reviewers are needed, which files are
important, or whether a finding is valid. Those decisions remain workflow,
project-binding, run or main-agent decisions. The script only materializes and
hashes declared inputs.

Preparation is mainly for strict provider-assigned gates. Ordinary standalone
external review can use `lite` mode: a small review request plus referenced
review-bundle artifacts and hashes. In `lite` mode the declared input boundary is
recorded, but the full diff or source context does not have to be embedded in the
review packet. Use `scripts/reviewers/run_external_review_lite.py` for this path.

## Preparation Evidence

A completed preparation artifact can record:

- the review prompt contract path and current hash;
- the material change id when the run has one;
- the worktree snapshot used for preparation;
- dirty worktree paths that were explicitly included or explicitly excluded;
- input artifacts and their hashes;
- generated review packet paths and hashes;
- generated rendered prompt paths and hashes;
- reviewer assignments copied from the contract;
- the predeclared review invocation set output path.

Run-scope provider-assigned review gates must predeclare invocation evidence:

```yaml
inputs:
  review_invocation_set: Docs/agentsflow/runs/<run-id>/review-invocation-set.json
```

`inputs.evidence_report` remains available for ordinary verification evidence.
It is not the review invocation set.

`run_review_set.py` is a dispatcher for a declared review prompt contract. Before
dispatch it checks assignment coverage and output-path aliasing; after dispatch
it records invocation-set evidence for repository validation. Full prompt
contract, reviewer report and invocation metadata validation remains the
responsibility of repository validation and the external reviewer wrapper. The
runner does not require a separate preparation artifact before dispatch. Projects
may still use `prepare_review_set_artifacts.py` when they want deterministic
packet/prompt materialization and dirty-worktree accounting.
External reviewer collection is bounded by `--external-reviewer-timeout-seconds`
(default 900). If one external reviewer hangs, the runner records the timeout and
preserves any peer external reviewer evidence that completed before the gate
fails closed.

## Dirty Worktree Policy

Preparation is fail-closed by default. Modified or untracked worktree paths must
be either:

- included as declared input artifacts; or
- excluded with an explicit reason recorded in preparation evidence.

This prevents a reviewer packet from silently omitting files that were present
when the review gate was prepared.

## AGENTS.md Handling

AgentsFlow does not require a provider-specific `CLAUDE.md`. If project agent
instructions are part of reviewer context, `AGENTS.md` is included as an
ordinary declared input artifact and hashed in the preparation evidence.

## Validation Boundary

Repository validation can prove that current packets, prompts, invocation-set
paths and reviewer outputs are structurally consistent. Preparation evidence can
add dirty-worktree and input-hash accounting, but it is not required for every
review dispatch.

Embedded file snapshots are checked by the preparation script when a current
review packet is materialized. Historical committed run artifacts are evidence
for their recorded material change, not a claim that embedded snapshots match
future repository HEAD.
