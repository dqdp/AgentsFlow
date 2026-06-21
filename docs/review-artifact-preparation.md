# Review Artifact Preparation

## Status

Accepted for the provider-assigned review gate slice.

## Purpose

Review artifact preparation is the deterministic step that turns declared review
policy into concrete reviewer inputs. It sits before reviewer invocation:

```text
review prompt contract draft
-> deterministic artifact preparation
-> prepared review packets and rendered prompts
-> structured preparation evidence
-> review invocation set
```

The preparation step does not decide which reviewers are needed, which files are
important, or whether a finding is valid. Those decisions remain workflow,
project-binding, run or main-agent decisions. The script only materializes and
hashes declared inputs.

## Required Evidence

A completed preparation artifact records:

- the review prompt contract path and current hash;
- the material change id when the run has one;
- the worktree snapshot used for preparation;
- dirty worktree paths that were explicitly included or explicitly excluded;
- input artifacts and their hashes;
- generated review packet paths and hashes;
- generated rendered prompt paths and hashes;
- reviewer assignments copied from the contract;
- the predeclared review invocation set output path.

Run-scope provider-assigned review gates must reference this preparation
evidence through:

```yaml
inputs:
  artifact_preparation_report: Docs/agentsflow/runs/<run-id>/prepared-review-artifacts.json
  review_invocation_set: Docs/agentsflow/runs/<run-id>/review-invocation-set.json
```

`inputs.evidence_report` remains available for ordinary verification evidence.
It is not the review invocation set.

`run_review_set.py` validates this preparation artifact before dispatch and the
completed invocation set records both `artifact_preparation_report` and
`artifact_preparation_report_hash`. Validators compare the recorded hash to the
current preparation file so a later mutation cannot silently satisfy the gate.
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

Repository validation can prove that current packets, prompts and invocation-set
paths match the preparation evidence. It cannot prove that every semantically
important file was selected unless that selection is encoded in project-bound
policy, explicit includes or workflow evidence.
