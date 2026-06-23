# Contract: Finding Boundary Trace Hardening

Status: Accepted lightweight self-application slice
Workflow: big-feature-contract-first
Effective Strictness: L2
Review Topology: homogeneous-plus-focused

## Intent

Add a small reusable Boundary Trace rule to AgentsFlow finding validation and
fusion guidance so accepted P0/P1 findings and new review-gate invariants are
checked across the boundary layers where they can be lost.

The rule must prevent the failure mode observed in the previous hardening slice:
fixing docs wording while missing downstream boundaries such as reviewer output
schema, external normalization, evaluator consumption and contract evidence.

## Non-goals

- Do not create a new workflow.
- Do not create a new mandatory artifact type.
- Do not add a heavyweight Markdown parser or new validator for trace tables.
- Do not require Boundary Trace for every P2/P3, NOTE, editorial fix or ordinary
  documentation cleanup.
- Do not infer severity from a boundary label.
- Do not redesign PR merge readiness, external reviewer providers or review-set
  runtime behavior.

## Fixed Decisions

- Boundary Trace is a triggered section inside finding validation/fusion, not a
  parallel source of truth.
- The main/orchestrating agent owns trace validation. Reviewers may suggest
  affected boundaries, but reviewer suggestions remain candidate input.
- Severity still comes only from a concrete acceptance-break path: grounded
  blocker path, acceptance impact, or mandatory evidence gap.
- Trace rows should reference existing artifacts and tests rather than duplicate
  their contents.

## Trigger Conditions

Boundary Trace is required when any of these are true:

- a P0/P1 finding is accepted as relevant;
- a mandatory evidence gap is accepted or produced;
- a review/finding/gate invariant is added or materially changed;
- schema, prompt rendering, reviewer output, external normalization, evaluator,
  provider, artifact storage or generated evidence behavior changes;
- a reviewer reports a plausible boundary-loss path.

Boundary Trace is optional and normally omitted when only P2/P3/NOTE findings,
non-material wording changes, duplicate consolidation or editorial report cleanup
remain.

## Boundary Labels

Use only these lightweight labels unless a run records a justified local
extension:

- `docs-rule`
- `reviewer-output`
- `schema`
- `prompt-rendering`
- `external-normalization`
- `artifact-storage`
- `evaluator`
- `contract-evidence`
- `generated-artifacts`
- `human-decision`

The label identifies where to look. It is not severity.

## Acceptance Criteria

- Finding validation template contains a triggered `Boundary Trace` section with
  labels, trigger conditions and an explicit "boundary impact is not severity"
  rule.
- Fusion template and fusion skill preserve suspected boundary impact for
  orchestrator validation but do not make reviewers authoritative.
- Review agent protocol documents the trigger-based rule without making it a new
  workflow or universal requirement.
- Review/fusion model references the reusable block without duplicating the full
  table.
- The v0.2 MVP contract has a bound executable smoke check for the rule.
- Existing repository validation and full pytest pass.

## Allowed Paths

- `docs/review-agent-interaction-protocol.md`
- `docs/review-fusion-model.md`
- `templates/finding-validation-report.md`
- `templates/fusion-report.md`
- `templates/review-prompts/base.md`
- `skills/fusion-synthesis/SKILL.md`
- `docs/contracts/agentsflow-v0.2-mvp.contract.md`
- `docs/contracts/agentsflow-v0.2-mvp.bindings.yaml`
- `tests/test_scripts_smoke.py`
- `run-artifacts/agentsflow/runs/2026-06-23-boundary-trace-finding-validation/**`

## Forbidden Without Approval

- New workflow directories.
- New schemas for Boundary Trace.
- New deterministic validator modules.
- Broad changes to PR merge readiness evaluator or external reviewer wrappers.
- Claude/live external review in this slice.

## Verification Plan

- Red: targeted smoke test for Boundary Trace wording and trigger constraints
  fails before docs/templates/skill implementation.
- Green: targeted smoke test passes.
- Green: `.venv/bin/python scripts/validate_repo.py --root .`
- Green: `.venv/bin/python -m pytest -q`
- Green: `git diff --check`
- Review: two Codex generalist baseline reviewers plus one focused
  process-semantics reviewer, read-only and fresh-context.
