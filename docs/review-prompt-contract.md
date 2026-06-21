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
- at least one review subject: `task_contract`, `reviewed_artifact`, or
  `reviewed_artifacts`;
- verification gate report and evidence report when applicable;
- structured review artifact preparation evidence when provider assignments are
  used for a run-scope gate;
- project agent instructions such as `AGENTS.md`, when they are part of the
  reviewer context;
- reviewer-report output schema;
- reviewer set with instance ids, role ids and role contract paths;
- optional provider policy and reviewer assignments;
- prompt components and rendered prompt hashes.

The contract does not require `CLAUDE.md` or any other provider-specific
instruction file. Provider-specific guidance may be included only as an explicit
artifact in the same packet/contract mechanism; it is not a parallel source of
review authority.

## Provider Assignments

Reviewer composition and reviewer provider selection are separate concerns.
The review profile defines which reviewer instances exist and what role
contracts they use. Optional `reviewer_assignments` bind those instances to a
provider and model family for a concrete gate run.

Each assignment records:

- reviewer instance id from `reviewer_set`;
- provider, for example `internal-agent` or `claude-code`;
- model family or harness label, for example `codex` or `opus`;
- review packet path;
- normalized reviewer-report JSON output path;
- provider config, raw output and invocation metadata paths for external
  providers.

Primary-gate and collision-control reviewer-report gate evidence is a
schema-bound JSON artifact regardless of provider. A reviewer may produce raw
Markdown or chat text, but the main/orchestrating agent must normalize that
content into `schemas/reviewer-report.schema.json` before it can satisfy
`reviewer_assignments[].report_path`. The raw Markdown/text may be retained as
a sidecar or source transcript; it is not itself reviewer-report gate evidence.
When a normalized report is derived from a raw source, the report should record
`normalization.method`, `source_path`, `source_hash`, `schema_validation` and
`normalized_by`. The normalized report must not contain its own `output_hash`;
that hash belongs in invocation metadata or another external evidence artifact
to avoid self-referential hashes.

`provider_policy.require_model_diversity: true` means the assignments must
prove at least `min_distinct_provider_model_families` distinct
`provider/model_family` pairs with completed evidence. The policy is not
satisfied by role names alone: two heterogeneous roles on the same harness are
not model diversity, and two providers without normalized reports are not
completed review evidence. Completed diversity proof is evidence-derived:
internal reports must declare `reviewer.model`, and Claude Code invocations
must record the requested model in invocation metadata. Claude Code invocation
metadata must also show a provider-reported model name matching the assigned
family. Internal-agent model evidence remains a local harness declaration in
v0.2; use an external provider assignment when the project requires stronger
provider-independent model proof.

The v0.2 supported external provider is `claude-code`. Unsupported providers
are configuration blockers.

`reviewer_assignments` are a dispatch plan before the review gate runs. A
run-scope assignment-enabled contract must predeclare two separate artifacts:

- `inputs.artifact_preparation_report`, the deterministic preparation evidence
  linking the contract, packets, rendered prompts, included context and hashes;
- `inputs.review_invocation_set`, the invocation evidence that proves which
  assignments actually completed.

`inputs.evidence_report` remains ordinary verification or project evidence. It
is not the review invocation set.

The completed invocation set proves which assignments actually completed and
links the normalized reviewer reports, raw external outputs and invocation
metadata.
External provider evidence for a completed run must have
`execution_mode: real`; mock responses are allowed for smoke tests but are not
accepted as completed review-gate evidence.
Completed external invocation metadata must also bind to the current review
artifacts: `exit_code` must be `0`, and recorded hashes for the packet, rendered
prompt, review prompt contract, role contract, rubric, output schema, raw
provider output and normalized reviewer report must match the current run
artifacts. This prevents a stale external report from satisfying a later
mixed-provider gate.
Each reviewer assignment must write to a distinct reviewer-report artifact, and
the report's `reviewer.id` must identify the assigned reviewer instance. A
single report artifact cannot satisfy multiple primary-gate reviewer slots.

## Artifact Preparation

The deterministic preparation script materializes reviewer packets and rendered
prompts from an assignment-enabled contract and a declared shared packet source.
It writes `review_artifact_preparation` evidence before reviewers are invoked.
That evidence records worktree status, explicit includes/exclusions, input
artifact hashes, generated packet hashes, rendered prompt hashes and the
predeclared invocation-set path.

Preparation is fail-closed for dirty worktrees: modified or untracked paths must
be included as input artifacts or excluded with explicit reasons. This prevents
Claude or any other reviewer provider from receiving a packet that silently
omits files present at review preparation time.

## Assembly Rules

### `homogeneous-dual`

- Exactly two reviewers.
- Both resolve to the `generalist` role contract.
- Reviewer labels such as `generalist-a` and `generalist-b` are instance ids only.
- Shared prompt content, shared review-packet content, rubric, output schema and
  role contract must be the same.
- Per-reviewer rendered prompt or packet envelopes may have different full hashes
  only for technical identity/provider routing fields such as
  `reviewer_instance_id` and `provider`.
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
- Exactly two control reviewers for each collision batch.
- Requires a recorded rejected/downgraded blocker collision batch:
  - collision batch id;
  - one or more disputed findings;
  - original severity `P0` or `P1` for each finding;
  - source reviewer report for each finding;
  - orchestrator collision reason covering the rejection or downgrade;
  - evidence references checked.
- The same batch may contain multiple disputed findings from the same review
  cycle; it must not launch reviewers per finding.
- Control reviewer outputs are still candidate/unvalidated.

## Non-Negotiable Prompt Text

Every rendered reviewer prompt must include the shared rules:

- start from fresh zero conversation context;
- do not use or assume forked orchestrator context;
- read only the review packet and referenced artifacts;
- do not run tests, execute scripts, modify files, create patches or update evidence;
- findings are candidate-unvalidated;
- report missing mandatory evidence;
- report plausible P0/P1 blockers even outside a focused role;
- prioritize substantive review quality over native output serialization;
- main/orchestrating agent validates relevance before findings affect workflow decisions.

## Validation Boundary

`schemas/review-prompt-contract.schema.json` validates structure. Repository and
wrapper validation check reference presence, reviewer membership and
profile-specific composition invariants.

Full runtime proof that an arbitrary non-wrapper reviewer process actually used
only the rendered prompt remains outside the v0.2 deterministic boundary.
