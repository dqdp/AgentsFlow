# Contract: AgentsFlow v0.2 MVP Behavior

Status: Active
Workflow: repository-validation
Domain Pack: coding-agent
Strictness: L2
Review Topology: homogeneous-dual

## Intent

Make the v0.2 MVP invariants readable as behavior, not only as Python
validators, JSON Schemas and prose docs.

## Non-goals

- Do not introduce a new runtime.
- Do not replace JSON Schema or deterministic validators.
- Do not make BDD scenarios executable gates by themselves.
- Do not broaden v0.2 beyond the accepted MVP boundary.

## Fixed Decisions

- BDD/Gherkin scenarios describe behavior; behavior bindings map scenarios to
  executable checks.
- Verification gates, wrapper smoke tests and validators remain the enforcement
  layer.
- External reviewer provider scope is Claude Code CLI only in v0.2.
- Primary review gates require at least two fresh-context reviewers.
- Repo examples may be fixtures, but must not claim stronger evidence than they
  provide.

## Assumptions

- The repository validator is run from the repository root.
- Pytest is available in the repository virtual environment.
- The e2e minimal Python project is the primary v0.2 example.

## Boundaries

### Allowed Paths

- `docs/contracts/**`
- `tests/**`
- existing validator, schema, template and workflow files when a scenario needs
  enforcement coverage

### Forbidden Paths Without Approval

- unrelated examples or workflow semantics
- external provider scope beyond Claude Code CLI

### Forbidden Behavior

- Do not treat a Gherkin scenario as an executable gate without a binding.
- Do not weaken an existing validator to make a scenario pass.
- Do not add future-work scenarios as required acceptance behavior.

## Behavioral Scenarios

Feature: AgentsFlow v0.2 MVP contract layer

  Scenario: Live external reviewer requires run-scope prompt contract
    Given an external reviewer invocation would call a live provider
    And the review prompt contract has artifact_scope "example"
    When the external reviewer wrapper validates the invocation
    Then the wrapper must fail before invoking the provider
    And the failure must explain that live reviews require artifact_scope "run"

  Scenario: Homogeneous dual review requires shared prompt and packet hashes
    Given a homogeneous-dual review prompt contract
    When a rendered prompt omits shared_prompt_content_hash or shared_packet_content_hash
    Then the prompt contract validation must fail
    And a run-scope contract must require concrete sha256 shared hashes

  Scenario: Project gate binding must match the upstream gate id
    Given a workflow requires verification_gate
    When a project binding key verification_gate extends a different upstream gate id
    Then project binding validation must fail
    And the failure must identify the mismatched upstream gate id

  Scenario: MVP review phase requires top-level review policy
    Given an MVP workflow contains a phase with kind review
    When the workflow omits the top-level review policy
    Then repository validation must reject the workflow
    And the workflow must declare reviewer count, prompt policy and fresh-context policy

  Scenario: Primary e2e run metadata and reviewer reports are schema-valid
    Given the primary minimal-python-project e2e run
    When repository validation checks workflow run metadata and reviewer reports
    Then run.yaml must satisfy workflow-run.schema.json
    And reviewer report JSON files must satisfy reviewer-report.schema.json

  Scenario: Homogeneous plus focused keeps baseline reviewers unfocused
    Given a homogeneous-plus-focused review packet for generalist-a or generalist-b
    When the packet has no focus_zone
    Then review-packet schema validation must still pass
    And focused non-baseline reviewers must still require focus_zone

  Scenario: Prepare-workflow target is limited to MVP user workflows
    Given a project intake declares intent_mode "prepare-workflow"
    When target_workflow is missing, project-initialization or a non-MVP reference workflow
    Then intake validation must fail
    And schema validation must accept only the v0.2 MVP user workflow ids

  Scenario: Prepare-workflow missing context or design forks use a run-level decision packet
    Given project-initialization runs in prepare-workflow mode
    When target workflow gate, review, evidence or authority context is missing
    And a material scope, ADR, risk, contract, gate, review, evidence, authority or workflow-design fork may be discovered
    Then the workflow may require target_workflow_context_decision_packet conditionally
    And it must not normalize that run-level packet into project-operating-decisions.yaml
    And unresolved blocking-material design decisions must block target workflow readiness

  Scenario: Existing-project initialization records documentation disposition
    Given project-initialization runs in adoption-onboarding, prepare-workflow or legacy-cleanup mode
    When current project documentation or Markdown implementation history exists
    Then the workflow must record project-documentation-disposition.yaml
    And prepare-workflow must use that artifact as run-level target workflow context
    And initialization must not rewrite or delete project documentation without human approval

  Scenario: Big-feature plan gate is strictness-aware
    Given a big-feature-contract-first project binding declares strictness L2
    When the binding omits plan_gate
    Then project binding validation must pass
    Given the same workflow binding declares strictness L3 or L4
    When the binding omits plan_gate
    Then project binding validation must fail

  Scenario: Evidence probe reports are evidence-only
    Given an evidence-probe-report artifact
    When the report includes finding_decision, acceptance_decision or unbound instruments
    Then schema or repository validation must reject it
    And a valid probe report must keep may_decide_findings false

  Scenario: Collision control uses one batch and two control reviewers
    Given a collision-control review packet or prompt contract
    When collision_control is missing or control_reviewer_count is not 2
    Then schema validation must fail
    And valid collision context must include the disputed finding batch and orchestrator collision reason

  Scenario: Review cycle caps are optional project policy or workflow binding
    Given an upstream workflow review_cycle policy
    When the workflow hardcodes max_review_cycles or requires a project value
    Then repository validation must fail
    And project workflow bindings may omit max_review_cycles to leave review cycles unlimited by count
    And a provided max_review_cycles value must be at least 3

  Scenario: Reviewer fresh-context is protocol-level in v0.2
    Given a primary review gate
    When the workflow declares fresh-context and no-fork reviewer policy
    Then v0.2 validators must check the declared artifact policy
    And the implementation must not claim machine proof that reviewer processes received no hidden context

  Scenario: Workflow run phase guard rejects future-phase artifacts
    Given a workflow run declares current_phase "raw_scan"
    And the phase guard allows only raw-scan outputs
    When the run artifact ledger includes task.contract.md
    Then workflow run validation must fail
    And the failure must identify the current phase and disallowed artifact

## Verification Binding

| Scenario | Verification |
|---|---|
| Live external reviewer requires run-scope prompt contract | `pytest tests/test_scripts_smoke.py::test_external_reviewer_wrapper_rejects_live_example_scope` |
| Homogeneous dual review requires shared prompt and packet hashes | `pytest tests/test_scripts_smoke.py::test_review_prompt_contract_rejects_missing_shared_hash` |
| Project gate binding must match the upstream gate id | `pytest tests/test_scripts_smoke.py::test_project_binding_rejects_wrong_upstream_gate_id` |
| MVP review phase requires top-level review policy | `pytest tests/test_scripts_smoke.py::test_mvp_review_phase_requires_top_level_review_policy` |
| Primary e2e run metadata and reviewer reports are schema-valid | `pytest tests/test_scripts_smoke.py::test_primary_e2e_workflow_run_artifacts_schema_pass` |
| Homogeneous plus focused keeps baseline reviewers unfocused | `pytest tests/test_scripts_smoke.py::test_review_packet_schema_allows_plus_focused_baseline_without_focus_zone` |
| Prepare-workflow target is limited to MVP user workflows | `pytest tests/test_scripts_smoke.py::test_project_intake_prepare_workflow_requires_target_workflow`; `pytest tests/test_scripts_smoke.py::test_project_intake_schema_restricts_prepare_workflow_target` |
| Prepare-workflow missing context or design forks use a run-level decision packet | `pytest tests/test_scripts_smoke.py::test_project_initialization_intent_mode_policy_prevents_discovery_full_onboarding_requirement`; `pytest tests/test_scripts_smoke.py::test_target_workflow_readiness_gate_blocks_unresolved_material_design_decisions` |
| Existing-project initialization records documentation disposition | `pytest tests/test_scripts_smoke.py::test_project_documentation_disposition_schema_passes`; `pytest tests/test_scripts_smoke.py::test_project_initialization_requires_documentation_disposition_decision`; `pytest tests/test_scripts_smoke.py::test_target_workflow_readiness_gate_requires_documentation_disposition` |
| Big-feature plan gate is strictness-aware | `pytest tests/test_scripts_smoke.py::test_project_binding_requires_strictness_applicable_gates`; `pytest tests/test_scripts_smoke.py::test_project_binding_does_not_require_higher_strictness_gate_for_l2` |
| Evidence probe reports are evidence-only | `pytest tests/test_scripts_smoke.py::test_evidence_probe_report_schema_rejects_decision_fields_and_unbound_sources` |
| Collision control uses one batch and two control reviewers | `pytest tests/test_scripts_smoke.py::test_collision_control_review_packet_requires_non_null_batch`; `pytest tests/test_scripts_smoke.py::test_collision_control_prompt_contract_requires_non_null_batch` |
| Review cycle caps are optional project policy or workflow binding | `pytest tests/test_scripts_smoke.py::test_upstream_review_cycle_rejects_hardcoded_max_cycles`; `pytest tests/test_scripts_smoke.py::test_workflow_binding_rejects_too_low_max_review_cycles` |
| Reviewer fresh-context is protocol-level in v0.2 | Manual evidence: `docs/review-agent-interaction-protocol.md`, `docs/review-prompt-contract.md`, `schemas/review-prompt-contract.schema.json` |
| Workflow run phase guard rejects future-phase artifacts | `pytest tests/test_scripts_smoke.py::test_workflow_run_phase_guard_rejects_future_phase_artifact`; `pytest tests/test_scripts_smoke.py::test_workflow_run_phase_guard_rejects_unlisted_artifact_without_explicit_forbidden`; `pytest tests/test_scripts_smoke.py::test_workflow_run_phase_guard_checks_phase_evidence_and_status_artifacts`; `pytest tests/test_scripts_smoke.py::test_workflow_run_phase_guard_rejects_list_shaped_phase_evidence`; `pytest tests/test_scripts_smoke.py::test_workflow_run_phase_guard_rejects_draft_artifact_as_evidence_or_output`; `pytest tests/test_scripts_smoke.py::test_workflow_run_phase_guard_rejects_allowed_and_draft_overlap`; `pytest tests/test_scripts_smoke.py::test_workflow_run_phase_guard_uses_top_level_draft_slot`; `pytest tests/test_scripts_smoke.py::test_workflow_run_phase_guard_checks_review_and_evidence_phase_status_keys`; `pytest tests/test_scripts_smoke.py::test_workflow_run_phase_guard_rejects_malformed_artifacts_root_paths`; `pytest tests/test_scripts_smoke.py::test_repo_validation_checks_top_level_workflow_run_phase_guard`; `pytest tests/test_scripts_smoke.py::test_workflow_run_phase_guard_allows_current_phase_artifacts` |

## Evidence Required

The acceptance proof must include:

- `contract_lint.py` on this contract;
- `gherkin_lint.py` on this contract;
- `bdd_binding_check.py` on the binding manifest;
- pytest results for the bound checks;
- repository validation result.

## Open Questions

- Whether v0.3 should generate binding manifests from contract scenarios or keep
  manual bindings as the source of truth.

## Hidden Regression Candidates

- A required scenario is added without a binding.
- A binding names a test that no longer exists.
- A validator accepts a fixture that claims stronger evidence than it contains.
