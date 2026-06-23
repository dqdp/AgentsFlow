# Contract: pr-merge-readiness

Status: Implementation green after development-review blocker fixes; waiting for fresh development review rerun
Workflow: big-feature-contract-first
Domain Pack: agentic-system
Effective Strictness: L3
Development Review Topology: homogeneous-plus-focused with two generalists and one Codex authority specialist
Target Workflow Review Topology: heterogeneous-variable with provider-mirrored topic pairs
Target Workflow: pr-merge-readiness

## Intent

Create the v0.2 utility workflow `pr-merge-readiness`, used to decide whether an
AgentsFlow branch is ready to open, accept or merge as a pull request. The
workflow must be small, evidence-oriented and compatible with the existing
AgentsFlow model: workflows define process shape, project bindings define
execution details, and workflow runs contain task-specific evidence.

This task is a self-application bootstrap: AgentsFlow is both the methodology
source and the target project. The run must preserve a hard boundary between
upstream methodology source, local project overlay and concrete run artifacts.

## Operating Context Preflight

| Item | Required? | Source | Status | Blocking code / notes |
|---|---:|---|---|---|
| Project binding or accepted project policy | yes | `.agentsflow/project.yaml`, `.agentsflow/workflows/big-feature-contract-first.binding.yaml` | present | Self-application overlay is local and gitignored. |
| Verification gate binding and runner | yes | `.agentsflow/gates/verification_gate.yaml`, `.agentsflow/scripts/run_verification_gate.sh` | present | Runs repo validation, pytest, `make check` and diff whitespace checks. |
| Review policy and reviewer count | yes | workflow default plus human decision packet | present | Target `pr-merge-readiness` runs use three provider-mirrored topic pairs. This BFCF development run uses a separate proportional development review gate. |
| Evidence and run artifact location | yes | `run-artifacts/agentsflow/runs/2026-06-21-pr-merge-readiness/` | present | Single run root for the bootstrap run. |
| Red-capture applicability | implementation workflows only | BFCF and ADR-0017 | required | New validators/examples must have failing red-capture evidence before implementation. |
| Human authority / approval boundaries | yes | `human-decisions.yaml` | present | Human accepted name, status, first-slice shape, evidence policy and self-application storage policy. |
| Human final acceptance policy | policy-defined | this contract | required | PR/merge acceptance requires a recorded human decision artifact. |

## Risk Surface Profile

| Risk surface | Why selected | Required path classes | Coverage status | Review impact |
|---|---|---|---|---|
| `authority_boundary` | The workflow decides whether a PR/merge may proceed but must not replace human approval. | `valid_delegation`, `malformed_request`, `direct_bypass_attempt` | draft-bound | Provider-mirrored adversarial/authority pair. |
| `human_approval` | Merge acceptance is human-owned and must be recorded. | `approval_present`, `approval_missing`, `defer_or_reject` | draft-bound | Review must check no implicit approval path exists. |
| `audit_persistence` | Readiness decisions, checks and review evidence must be durable. | `accepted_persisted`, `rejected_persisted`, `missing_evidence_rejected` | draft-bound | Review must inspect evidence ledger shape. |
| `secret_handling` | Live Claude raw output and local paths may be sensitive, and required live raw evidence must not disappear silently. | `non_sensitive_raw_persisted`, `sensitive_raw_redacted`, `required_live_raw_not_persisted_blocks`, `mock_not_live` | draft-bound | Review must check raw evidence policy and examples. |
| `external_io` | External Claude review can be unavailable or incomplete. | `live_available`, `live_unavailable`, `mock_baseline` | draft-bound | Review must verify live/mock distinction and blocker semantics. |
| `persistence_consistency` | Report, invocation metadata and review packet references must agree. | `consistent_paths`, `stale_evidence_excluded`, `artifact_missing` | draft-bound | Review must check path consistency. |

## Target Workflow Review Model

PR merge readiness uses `heterogeneous-variable` review with provider-mirrored
topic pairs. Each topic receives the same review packet, role-specific focus and
same output schema from both provider families where available.

| Topic | Role | Providers | Primary focus |
|---|---|---|---|
| verification-evidence | verification | Codex + Claude | Tests, deterministic checks, red/green evidence, stale or missing artifacts. |
| architecture-process | architecture | Codex + Claude | Workflow boundaries, scope creep, self-application artifact separation, methodology consistency. |
| adversarial-authority | adversarial | Codex + Claude | False readiness, missing human approval, mock-vs-live Claude evidence, raw redaction, collision-control bypass. |

Fusion must preserve P0/P1 blockers and compare provider disagreements inside
each topic pair. The review gate does not use majority voting to override
blockers.

## Development Run Review Model

The six-reviewer provider-mirrored topology above belongs to future
`pr-merge-readiness` runs. It is not the default review gate for this BFCF
development run. After green verification, this run uses a proportional
development review gate: one internal Codex generalist, one external Claude
generalist when local Claude is available, and one internal Codex
adversarial-authority specialist focused on the riskiest layer: false readiness,
human-owned decisions, automatic gate versus human-mediated authority
boundaries, mock-vs-live evidence claims and P0/P1 collision-control bypass.
Additional focused reviewers may be added only if green evidence, validated
risk, or a human decision requires escalation.

## Failure Path Matrix

| ID | Risk surface | Path class | Trigger | Expected authority | Expected context/state | Expected audit/persistence | Must not happen | Evidence binding |
|---|---|---|---|---|---|---|---|---|
| PRM-FPM-001 | `authority_boundary` | `direct_bypass_attempt` | A report tries to mark a PR merge-ready without required checks. | Workflow rejects readiness; human cannot accept based on incomplete evidence. | Checks missing or failed. | Readiness report records `blocked_missing_evidence`. | Silent pass or implied approval. | `PRM-BHV-001` |
| PRM-FPM-002 | `human_approval` | `approval_missing` | All checks pass but no human merge decision is recorded. | Workflow remains `awaiting_human_decision`. | Verification/review green, decision missing. | Human decision record required before accepted status. | Auto-merge-ready status without human record. | `PRM-BHV-002` |
| PRM-FPM-003 | `audit_persistence` | `missing_evidence_rejected` | Required validator/test/review evidence path is absent. | Workflow blocks or marks evidence incomplete. | Readiness report references missing artifact. | Missing path and blocking reason recorded. | Passing readiness with dangling references. | `PRM-BHV-003` |
| PRM-FPM-004 | `external_io` | `live_unavailable` | Subscription-local Claude is unavailable. | Local readiness records blocker or explicit fallback policy; CI may use mock baseline. | External provider unavailable or timed out. | Invocation metadata or explicit unavailable record. | Claiming live Claude review from mock evidence. | `PRM-BHV-004` |
| PRM-FPM-005 | `secret_handling` | `sensitive_raw_redacted` | Live Claude output or packet contains sensitive local context, or required live raw evidence is declared `not_persisted`. | Raw output is non-sensitive, or redacted/replaced with pointer/summary artifact; `not_persisted` blocks required live evidence. | Sensitive or missing raw evidence detected or declared. | Normalized report and invocation metadata persist; non-sensitive raw has matching path/hash, while redacted/summary/pointer has reason plus artifact path/hash. | Committing sensitive raw output by default, or silently accepting missing required live raw evidence. | `PRM-BHV-005` |
| PRM-FPM-006 | `authority_boundary` | `malformed_request` | A P0/P1 candidate finding is rejected or downgraded without collision-control. | Workflow blocks until collision-control evidence exists. | Finding triage changed blocker status. | Finding validation report records control review requirement/result. | Majority vote or main-agent assertion overrides a blocker. | `PRM-BHV-006` |
| PRM-FPM-007 | `persistence_consistency` | `stale_evidence_excluded` | Review packet predates latest material change. | Workflow marks review stale and requires fresh review. | Material change after green evidence or packet preparation. | Stale evidence excluded or rerun recorded. | Using stale review as gate evidence. | `PRM-BHV-007` |
| PRM-FPM-008 | `authority_boundary` | `direct_bypass_attempt` | Bootstrap run tries to prove `pr-merge-readiness` by invoking the unfinished workflow. | Bootstrap remains BFCF-based; first full `pr-merge-readiness` use is later PR/merge acceptance. | Self-application bootstrap. | Run metadata states bootstrap limitation. | Cyclic self-proof. | `PRM-BHV-008` |
| PRM-FPM-009 | `authority_boundary` | `direct_bypass_attempt` | A report includes failed checks or blocked reviews but claims accepted readiness. | Workflow rejects readiness. | Check or review status is not pass. | Blocking reason records the failed check/review id. | Treating present files as passed evidence. | `PRM-BHV-009` |
| PRM-FPM-010 | `human_approval` | `malformed_request` | The report has `human_decision.status: accepted` without a schema-valid matching human-authored decision record. | Workflow remains blocked or awaiting human decision. | Decision path/id missing, non-human, non-matching, legacy ad-hoc, or not `status: confirmed`. | Human decision artifact is schema-validated and matched by run id, decision id, human author and accepted answer. | In-band accepted flag or legacy ad-hoc YAML substitutes for human approval. | `PRM-BHV-010` |
| PRM-FPM-011 | `authority_boundary` | `direct_bypass_attempt` | A readiness report omits or underdeclares required provider-mirrored review topology entries. | Workflow blocks accepted readiness. | `review_requirements.required_reviews` is missing, incomplete or not satisfied. | Missing required reviewer ids and undeclared required topology entries are recorded. | Empty or self-declared narrow `reviews`/`external_review_evidence` arrays pass because no row failed. | `PRM-BHV-011` |
| PRM-FPM-012 | `authority_boundary` | `malformed_request` | A referenced reviewer report contains a P0/P1 finding that is not represented in candidate finding triage with blocker-grade handling. | Workflow rejects readiness until the finding is triaged. | Source reviewer report is schema-valid and includes blocker-level finding. | Unhandled source finding id, source reviewer id, lower-severity representation or unresolved duplicate are recorded. | Reviewer P0/P1 findings are silently dropped, downgraded to P3, or hidden as duplicates before fusion/finding validation. | `PRM-BHV-012` |
| PRM-FPM-013 | `external_io` | `malformed_request` | Claude invocation metadata is stale, unsafe or not bound to the claimed review artifacts. | Workflow blocks external review readiness. | Invocation provider, role, permission mode, output format, transport, packet, prompt, prompt contract, role contract, rubric, schema, paths or hashes mismatch. | Mismatch reason and reviewer id are recorded. | `permission_mode: plan`, wrong role, wrong path or stale packet/prompt/schema hash satisfies live evidence. | `PRM-BHV-013` |
| PRM-FPM-014 | `authority_boundary` | `malformed_request` | Collision-control for a rejected/downgraded P0/P1 points at arbitrary files or unrelated reviewer reports. | Workflow blocks collision-control acceptance. | Control reports are missing, malformed, not distinct reviewer reports or not tied to the same collision batch/disputed finding. | Collision-control incompleteness or invalid control report is recorded. | Any two existing files or unrelated valid reports satisfy independent control review. | `PRM-BHV-014` |

## Non-goals

- No release platform or release-management runtime.
- No package distribution workflow.
- No generic CI provider abstraction.
- No generic multi-provider runtime beyond existing provider assignment support.
- No API-key based Claude usage.
- No automatic merge or GitHub/GitLab PR mutation.
- No broad rewrite of existing AgentsFlow workflow architecture.

## Fixed Decisions

- v0.2 supported application path remains `project-initialization.prepare-workflow -> big-feature-contract-first`.
- `pr-merge-readiness` is a v0.2 utility workflow, not a primary application workflow.
- This utility is implemented through `big-feature-contract-first`.
- First slice includes docs, schema, template, example and validator coverage.
- PR merge readiness uses heterogeneous provider-mirrored topic pairs for review:
  verification/evidence, architecture/process and adversarial/authority.
- Live Claude evidence persists normalized report and invocation metadata; raw output persists only when non-sensitive, otherwise redacted summary or pointer is recorded.
- `.agentsflow/` is a gitignored local self-project overlay for this repository.
- Self-application run artifacts live under `run-artifacts/agentsflow/runs/2026-06-21-pr-merge-readiness/` and do not become methodology source without an explicit promoted diff.

## Assumptions

- The local repository is the target project and methodology source for this bootstrap run.
- The local `.venv` is available for validation and pytest.
- Subscription-local Claude may be used later through the project-bound wrapper; mock smoke remains the CI-safe baseline.
- Existing external reviewer provider wrapper and review-set launcher are not redesigned in this slice.

## Boundaries

### Allowed Paths

- `workflows/pr-merge-readiness/**`
- `schemas/pr-merge-readiness-report.schema.json`
- `templates/pr-merge-readiness-report.*`
- `examples/pr-merge-readiness/**`
- `docs/pr-merge-readiness.md`
- `docs/workflow-model.md`
- `docs/mvp-ready-workflow-standard.md`
- `docs/review-fusion-model.md`
- `README.md`
- `AGENTS.md`
- `skills/fusion-synthesis/**`
- `skills/evidence-reporting/skill.yaml`
- `skills/reviewer-adversarial/skill.yaml`
- `skills/reviewer-architecture/skill.yaml`
- `skills/reviewer-verification/skill.yaml`
- `templates/fusion-report.md`
- `templates/finding-validation-report.md`
- `templates/reviewer-invocation.json`
- `schemas/reviewer-report.schema.json`
- `scripts/repo_validation/**`
- `scripts/validate_repo.py`
- `scripts/reviewers/README.md`
- `scripts/reviewers/prepare_review_set_artifacts.py`
- `scripts/reviewers/prompt_rendering.py`
- `scripts/reviewers/run_review_set.py`
- `scripts/reviewers/run_external_reviewer.py`
- `scripts/reviewers/providers/claude_code.py`
- `examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-prompt-contract.yaml`
- `examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-prompts/*.md`
- `tests/**`
- `run-artifacts/agentsflow/runs/2026-06-21-pr-merge-readiness/**`

### Forbidden Paths Without Approval

- `docs/adr/**`
- `workflows/project-initialization/**`
- `workflows/big-feature-contract-first/**`
- `scripts/reviewers/providers/**`, except `scripts/reviewers/providers/claude_code.py` under the approved development-review blocker fix below
- `scripts/reviewers/run_external_reviewer.py`, except under the approved development-review blocker fix below
- Any path outside `/Users/alex/AgentsFlow`

### Approved Scope Amendment

During `contract_acceptance`, the human approved a minimal methodology hardening
for `big-feature-contract-first`: design acceptance must start with an open
decision inventory and then review each blocking/material decision with options,
tradeoffs, recommendation, rationale and an exact acceptance question. This
approval covers only the related BFCF phase contract, `decision-contracting`
skill/template, documentation and validator regression. It does not authorize
changes to `project-initialization`, external reviewer providers or ADRs.

During `contract_acceptance`, the human also approved minimal hardening of the
existing reusable review/fusion layer. The post-review pipeline must remain a
shared gate-control block, not a `pr-merge-readiness`-local copy. This amendment
covers `docs/review-fusion-model.md`, `skills/fusion-synthesis/**`,
`skills/evidence-reporting/skill.yaml`, `skills/reviewer-adversarial/skill.yaml`,
`skills/reviewer-architecture/skill.yaml`, `skills/reviewer-verification/skill.yaml`,
`templates/fusion-report.md`, `templates/finding-validation-report.md` and
regression tests. It must preserve automatic gate versus human-in-the-loop
authority boundaries.

During `development_review`, the live Claude reviewer gate exposed a blocker in
the existing Claude Code provider config: `permission_mode: plan` can route the
review deliverable into Claude-managed plan artifacts instead of returning
schema-bound JSON to the wrapper. The orchestrator applied the minimal blocker
fix needed to execute the accepted mixed-provider review gate. This approved
exception covers only:

- `scripts/reviewers/run_external_reviewer.py`;
- `scripts/reviewers/providers/claude_code.py`;
- `scripts/reviewers/run_review_set.py`;
- `scripts/reviewers/prepare_review_set_artifacts.py`;
- `scripts/reviewers/prompt_rendering.py`;
- `scripts/reviewers/README.md`;
- `schemas/reviewer-report.schema.json`;
- `templates/reviewer-invocation.json`;
- the primary e2e review-prompt fixtures required after shared prompt/schema changes;
- external reviewer configs, schemas, validators, docs, examples and run
  artifacts required to bind those changes to evidence.

The exception keeps reviewers read-only, keeps API-key Claude usage forbidden,
and allows `permission_mode: default` with `tools: ""` for stdin transport. It
does not authorize a new provider, write-enabled external reviewers, API-key
usage or a generic multi-provider runtime. The corresponding human decision is
`pr_merge_readiness.development_review_external_reviewer_blocker_fix`.

### Forbidden Behavior

- Do not treat run artifacts as upstream methodology source.
- Do not store run history in `.agentsflow/`.
- Do not create `.agentsflow/upstream` for self-application.
- Do not use `Docs/agentsflow/runs/` for AgentsFlow self-application because it can collapse into lowercase `docs/` on case-insensitive filesystems.
- Do not present mock Claude evidence as live Claude evidence.
- Do not weaken existing validators or tests to make the new workflow pass.
- Do not start red-capture or implementation before human acceptance of the contract, behavior bindings, Failure Path Matrix, impact map, technical plan and provider-mirrored heterogeneous review model.

## Behavioral Scenarios

```gherkin
Feature: PR merge readiness utility

  Scenario: Complete evidence produces a merge readiness decision packet
    Given a branch, base branch, intended commit range and clean or documented worktree state
    And repository validation, tests, documentation consistency checks and review evidence are present
    When the PR merge readiness workflow evaluates the evidence
    Then it produces a readiness report with check statuses, evidence paths and residual limitations
    And it requires a human merge decision before accepted merge-ready status

  Scenario: Missing verification evidence blocks readiness
    Given a PR merge readiness report references required repository checks
    When a required check result or evidence artifact is missing
    Then the report status is blocked or incomplete
    And the missing evidence path and reason are recorded

  Scenario: Human merge approval is required after green evidence
    Given all deterministic checks and required reviews are green
    When no human merge decision record exists
    Then the workflow status remains awaiting human decision
    And it does not claim accepted merge readiness

  Scenario: Live Claude review is never confused with mock smoke evidence
    Given external Claude review is requested for local PR merge readiness
    When only mock external reviewer smoke evidence exists
    Then the report marks live Claude evidence absent or blocked according to policy
    And it does not describe mock output as a live provider invocation

  Scenario: Sensitive or missing raw external review output is handled explicitly
    Given a live external review output may contain sensitive local context
    And required live external review evidence declares raw output persistence
    When raw output persistence is evaluated
    Then normalized report and invocation metadata are persisted
    And raw output is either non-sensitive with matching path/hash, or redacted/replaced with a summary or pointer artifact with reason and hash
    And required live external evidence with `raw_output.persistence: not_persisted` blocks readiness

  Scenario: Rejected blocker-level candidate findings require collision-control
    Given a reviewer reports a P0 or P1 candidate finding
    When the orchestrating agent accepts it, marks it needs-more-evidence, rejects it, or downgrades it
    Then accepted or needs-more-evidence blockers prevent accepted readiness
    And rejected or downgraded blockers require complete collision-control evidence before the readiness gate can pass

  Scenario: Stale review evidence is excluded
    Given review packets and reports exist for a branch
    When a material change happens after packet preparation or the review timestamps are malformed
    Then the older review evidence is marked stale or excluded
    And fresh review evidence is required before final readiness

  Scenario: Self-application bootstrap avoids cyclic proof
    Given AgentsFlow is applying BFCF to create `pr-merge-readiness`
    When the bootstrap run records its evidence
    Then the run metadata marks `application_mode: self_application_bootstrap`
    And the unfinished `pr-merge-readiness` workflow is not used to prove itself ready

  Scenario: Failed checks or blocked reviews prevent accepted readiness
    Given a readiness report references required checks and reviews
    When any check has a failed, blocked, skipped, or inconclusive status
    Or any review has a failed or blocked status
    Then the workflow rejects accepted readiness
    And the blocking check or review id is recorded

  Scenario: Accepted human approval must resolve to a human-authored decision record
    Given a readiness report declares accepted human approval
    When the decision id or path is missing
    Or the referenced decision record is absent, non-human, or non-matching
    Then the workflow does not accept merge readiness
    And the missing or invalid human decision record is recorded

  Scenario: Required review topology cannot be omitted
    Given a readiness report declares required review ids, topics and providers
    When a required review row is absent or mismatched
    Then the workflow blocks accepted readiness
    And the missing or mismatched required review id is recorded

  Scenario: Reviewer P0 and P1 findings must enter candidate finding triage
    Given a referenced reviewer report is schema-valid
    And it contains a P0 or P1 candidate finding
    When the readiness report does not represent that source finding in candidate_findings
    Then the workflow rejects accepted readiness
    And records the unhandled source reviewer/finding id

  Scenario: Claude invocation metadata must be bound to the claimed review
    Given a Claude-backed review is required as live evidence
    When invocation metadata uses unsafe permission mode, mismatched role, mismatched output path, or stale output hashes
    Then the workflow blocks external review readiness
    And records the specific invocation mismatch

  Scenario: Collision-control reports must be structured reviewer evidence
    Given a P0 or P1 finding is rejected or downgraded
    When collision-control points at arbitrary existing files instead of two distinct schema-valid control reviewer reports
    Then the workflow blocks collision-control acceptance
    And records the invalid control report evidence
```

## Verification Binding

| Scenario | Risk surface | Path class | Verification |
|---|---|---|---|
| Complete evidence produces a merge readiness decision packet | `audit_persistence` | `accepted_persisted` | `PRM-BHV-001` |
| Missing verification evidence blocks readiness | `audit_persistence` | `missing_evidence_rejected` | `PRM-BHV-003` |
| Human merge approval is required after green evidence | `human_approval` | `approval_missing` | `PRM-BHV-002` |
| Live Claude review is never confused with mock smoke evidence | `external_io` | `mock_baseline` | `PRM-BHV-004` |
| Sensitive raw external review output is not committed by default | `secret_handling` | `sensitive_raw_redacted` | `PRM-BHV-005` |
| Rejected blocker-level candidate findings require collision-control | `authority_boundary` | `malformed_request` | `PRM-BHV-006` |
| Stale review evidence is excluded | `persistence_consistency` | `stale_evidence_excluded` | `PRM-BHV-007` |
| Self-application bootstrap avoids cyclic proof | `authority_boundary` | `direct_bypass_attempt` | `PRM-BHV-008` |
| Failed checks or blocked reviews prevent accepted readiness | `authority_boundary` | `direct_bypass_attempt` | `PRM-BHV-009` |
| Accepted human approval must resolve to a human-authored decision record | `human_approval` | `malformed_request` | `PRM-BHV-010` |
| Required review topology cannot be omitted | `authority_boundary` | `direct_bypass_attempt` | `PRM-BHV-011` |
| Reviewer P0 and P1 findings must enter candidate finding triage | `authority_boundary` | `malformed_request` | `PRM-BHV-012` |
| Claude invocation metadata must be bound to the claimed review | `external_io` | `malformed_request` | `PRM-BHV-013` |
| Collision-control reports must be structured reviewer evidence | `authority_boundary` | `malformed_request` | `PRM-BHV-014` |

## Audit and Persistence Contract

| Item | Decision |
|---|---|
| Event or attempt recorded | PR merge readiness evaluation, deterministic checks, review invocation set, finding validation and human decision. |
| Write timing relative to side effect | Before merge acceptance; no merge side effect is executed by the utility. |
| Denied/rejected/timeout/downstream-failure paths recorded | Yes. Missing evidence, failed checks, live Claude unavailability, stale review and rejected blockers must be recorded. |
| Correlation id / run id | `2026-06-21-pr-merge-readiness` |
| Redacted or omitted fields | Sensitive raw external-review output and local context may be redacted or replaced with a pointer/summary. |
| Read-back / consistency evidence | Validator coverage must check required paths, live/mock evidence distinction, human decision presence and stale-evidence exclusion. |

## Evidence Required

The final evidence report must include:

- changed files;
- scenario coverage;
- risk surface and Failure Path Matrix coverage;
- commands run and results;
- boundary check result;
- impact map result;
- red-capture failing evidence for new validators/examples;
- green verification evidence after implementation;
- post-implementation development review gate result, using the proportional
  BFCF development review model above;
- implemented target workflow provider-mirrored review policy artifacts;
- live Claude unavailable/blocker or fallback record when local Claude is not available;
- known limitations.

## Open Questions

| ID | Question | Classification | Default | Answer required before implementation? | Decision / status | Affected artifacts |
|---|---|---|---|---:|---|---|
| Q-001 | Is this draft contract accepted for impact mapping and technical planning? | blocking-material | changes_requested_until_human_accepts | yes | accepted | `task.contract.md`, `behavior.bindings.yaml`, `run.yaml`, `human-decisions.yaml` |
| Q-002 | Exact field set for `pr-merge-readiness-report` | nonblocking-follow-up | Agent proposes minimal schema during technical plan. | no | open for plan refinement | `schemas/pr-merge-readiness-report.schema.json`, `templates/pr-merge-readiness-report.*` |
| Q-003 | Exact validator behavior for sensitive raw Claude output redaction | nonblocking-follow-up | Agent proposes minimal deterministic checks plus explicit manual redaction reason field. | no | open for plan refinement | validator tests, schema, template |

## Grouped Decision Packet

The draft contract review was accepted for impact mapping and technical
planning after updating the review model to heterogeneous provider-mirrored topic
pairs. Red-capture remains separately blocked by the BFCF `contract_acceptance`
phase after plan gate readiness.

## Hidden Regression Candidates

- A report passes with missing human approval.
- A report passes with stale review evidence after a material change.
- A mock Claude smoke report is labeled as live Claude evidence.
- Raw live Claude output is committed despite sensitive packet classification.
- A rejected P0/P1 candidate finding bypasses collision-control.
- Required review topology is omitted and accepted because no review row failed.
- A reviewer P0/P1 finding is dropped before candidate finding triage.
- Claude invocation metadata is accepted despite unsafe permission mode, mismatched role, or stale hashes.
- Arbitrary existing files satisfy collision-control.
- A self-application run treats `run-artifacts/agentsflow/runs/**` as upstream methodology source.
