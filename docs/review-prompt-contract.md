# Review Prompt Contract

## Status

Accepted for v0.2.

## Purpose

The review prompt contract is a run artifact that records how reviewer prompts
were assembled. It is not a monolithic prompt and it should not duplicate every
skill instruction. It proves that reviewer prompts came from declared reusable
parts:

- review profile;
- reviewer role contract;
- review packet;
- shared rubric and lifecycle rules;
- output schema;
- optional focus zone;
- optional collision-control context.

The default path is:

```text
Docs/agentsflow/runs/<run-id>/review-prompt-contract.yaml
```

Run artifacts should use `artifact_scope: run` and concrete SHA-256 hashes.
Templates and documentation examples may use `artifact_scope: template` or
`artifact_scope: example` with placeholder hashes.

## Required Inputs

A contract records:

- workflow, run id, phase and selected review profile;
- review packet paths, schemas and hashes;
- task contract or reviewed artifact;
- verification gate report and evidence report when applicable;
- reviewer-report output schema;
- reviewer set with instance ids, role ids and role contract paths;
- prompt components and rendered prompt hashes.

## Assembly Rules

### `homogeneous-dual`

- Exactly two reviewers.
- Both resolve to the `generalist` role contract.
- Reviewer labels such as `generalist-a` and `generalist-b` are instance ids only.
- Shared prompt content, shared review-packet content, rubric, output schema and
  role contract must be the same.
- Per-reviewer rendered prompt or packet envelopes may have different full hashes
  only for technical identity/evidence fields such as `reviewer_instance_id`.
  The contract records separate shared-content hashes to prove substantive equality.

### `homogeneous-plus-focused`

- Keep the homogeneous baseline pair.
- Add one or more focused reviewers.
- Focused reviewers must have role contracts and explicit focus zones.
- Focus zones are not ownership boundaries.
- Focused reviewers must report plausible P0/P1 blockers even outside focus.

### `heterogeneous-variable`

- Use three to eight reviewers.
- Every reviewer has an explicit role contract.
- Every reviewer has a focus zone.
- Focus zones may overlap.
- All reviewers share output schema and candidate-finding lifecycle.

### `collision-control`

- Not valid as a primary gate.
- Exactly one reviewer.
- Requires a recorded rejected-blocker collision:
  - disputed finding id;
  - original severity `P0` or `P1`;
  - source reviewer report;
  - orchestrator rejection or downgrade reason;
  - evidence references checked.
- The control reviewer output is still candidate/unvalidated.

## Non-Negotiable Prompt Text

Every rendered reviewer prompt must include the shared rules:

- start from fresh zero conversation context;
- do not use or assume forked orchestrator context;
- read only the review packet and referenced artifacts;
- do not run tests, execute scripts, modify files, create patches or update evidence;
- findings are candidate-unvalidated;
- report missing mandatory evidence;
- report plausible P0/P1 blockers even outside a focused role;
- main/orchestrating agent validates relevance before findings affect workflow decisions.

## Validation Boundary

`schemas/review-prompt-contract.schema.json` validates structure. Repository and
wrapper validation check reference presence, reviewer membership and
profile-specific composition invariants.

Full runtime proof that an arbitrary non-wrapper reviewer process actually used
only the rendered prompt remains outside the v0.2 deterministic boundary.
