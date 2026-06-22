# Technical Plan

## Goal

Implement `pr-merge-readiness` as a v0.2 utility workflow with a minimal
executable contract: workflow definition, readiness report schema/template,
example artifacts, validator coverage, documentation integration and
provider-mirrored heterogeneous review-gate design for target PR-readiness runs.

## Grounding Evidence

- `docs/plans/v0.2-next-slices.md` records accepted name, status, first-slice
  shape, Claude evidence policy and self-application storage policy.
- `docs/project-binding-model.md` and ADR-0013 define methodology source,
  project overlay and run artifact separation.
- ADR-0016 and `docs/external-reviewer-provider-model.md` constrain external
  reviewer evidence.
- `profiles/review_topologies/heterogeneous-variable.yaml` and existing reviewer
  roles support the selected topic-pair review model.
- `big-feature-contract-first` requires human `contract_acceptance` before
  red-capture.

## Affected Areas

- `workflows/pr-merge-readiness/workflow.yaml`
- `schemas/pr-merge-readiness-report.schema.json`
- `templates/pr-merge-readiness-report.*`
- `examples/pr-merge-readiness/**`
- `scripts/repo_validation/**`
- `tests/test_pr_merge_readiness.py`
- `docs/pr-merge-readiness.md`
- `README.md`, `docs/workflow-model.md`,
  `docs/mvp-ready-workflow-standard.md`

## Proposed Steps

1. After `contract_acceptance`, add red-capture tests for readiness-report
   semantics and run them before implementation.
2. Implement the report schema and validation helper.
3. Add template and example artifacts covering complete evidence, missing
   evidence, human approval, mock-vs-live Claude, raw redaction, stale review,
   blocker collision-control and self-application guard.
4. Add repo-validation hooks for the schema/example and any explicit
   self-application run-artifact validation.
5. Add `workflows/pr-merge-readiness/workflow.yaml` as a v0.2 utility workflow.
6. Encode target workflow review assignment policy as `heterogeneous-variable` with three
   provider-mirrored topic pairs: verification/evidence, architecture/process
   and adversarial/authority.
7. Update documentation without promoting the utility to a primary application
   workflow.
8. Run green verification and prepare the proportional BFCF development review
   packet: Codex generalist, Claude generalist when available, and a Codex
   adversarial-authority specialist for the riskiest authority layer. Do not
   automatically launch the target workflow's six-reviewer PR-readiness gate
   for this development run.

## Scope Boundaries

Allowed:

- Add the new utility workflow, schema, template, example, focused tests and
  documentation listed in the contract.
- Add narrowly scoped validator support for `pr-merge-readiness`.
- Encode provider-mirrored topic assignments in the workflow/binding artifacts.
- Use a separate proportional development review gate for this BFCF run: two
  generalists plus one Codex adversarial-authority specialist.

Forbidden without approval:

- Changing `project-initialization` semantics.
- Changing `big-feature-contract-first` semantics during this run.
- Rewriting external reviewer wrapper/provider code.
- Adding GitHub/GitLab mutation, release automation or generic CI provider
  abstraction.
- Using `Docs/agentsflow/runs/` for this self-application run.
- Adding new reviewer roles when existing `verification`, `architecture` and
  `adversarial` roles cover the review themes.

Approved scope amendment:

- The human approved minimal `big-feature-contract-first` hardening during
  `contract_acceptance`: design acceptance must use a decision inventory and
  per-decision option/tradeoff review before asking for acceptance. This
  amendment is limited to the BFCF `contract_acceptance` contract,
  `decision-contracting` skill/template, supporting docs, validator logic and
  regression test.
- The human approved minimal hardening of the existing reusable review/fusion
  layer during `contract_acceptance`: the post-review pipeline should be a
  shared gate-control block, not duplicated inside `pr-merge-readiness`. This
  amendment is limited to `docs/review-fusion-model.md`,
  `skills/fusion-synthesis/**`, `templates/fusion-report.md`,
  `templates/finding-validation-report.md` and regression tests, while
  preserving automatic gate versus human-in-the-loop authority boundaries.

## Tests / Checks to Add or Run

- Red: `.venv/bin/python -m pytest tests/test_pr_merge_readiness.py -q`
- Green: `.venv/bin/python scripts/validate_repo.py --root .`
- Green: `.venv/bin/python -m pytest -q`
- Green: `make check`
- Green: external reviewer mock smoke through
  `scripts/reviewers/run_external_reviewer.py`
- Green: `git diff --check main`

## Risks

- Overbuilding into a release platform. Mitigation: schema/report only, no PR
  mutation.
- Confusing self-application run artifacts with methodology docs. Mitigation:
  `run-artifacts/agentsflow/runs/**` and artifact role labels.
- Confusing mock Claude evidence with live review. Mitigation: explicit schema
  fields and validator tests.
- Review cost from six reviewers. Mitigation: the mirrored topic-pair gate is a
  target `pr-merge-readiness` policy, not the default review gate for developing
  this workflow. The BFCF development run uses a proportional
  homogeneous-plus-focused review gate with two generalists and one Codex
  authority specialist unless green evidence or human decision requires further
  escalation.

## Rollback Plan

Remove `workflows/pr-merge-readiness/`, schema/template/example, focused
validator hooks/tests and docs updates. Historical run artifacts remain under
`run-artifacts/agentsflow/runs/` and are not methodology source.

## Open Questions

None blocking. Field names and validator strictness are implementation details
inside the accepted contract and will be red-captured before implementation.
