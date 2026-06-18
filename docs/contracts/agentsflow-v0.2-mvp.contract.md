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

## Verification Binding

| Scenario | Verification |
|---|---|
| Live external reviewer requires run-scope prompt contract | `pytest tests/test_scripts_smoke.py::test_external_reviewer_wrapper_rejects_live_example_scope` |
| Homogeneous dual review requires shared prompt and packet hashes | `pytest tests/test_scripts_smoke.py::test_review_prompt_contract_rejects_missing_shared_hash` |
| Project gate binding must match the upstream gate id | `pytest tests/test_scripts_smoke.py::test_project_binding_rejects_wrong_upstream_gate_id` |
| MVP review phase requires top-level review policy | `pytest tests/test_scripts_smoke.py::test_mvp_review_phase_requires_top_level_review_policy` |
| Primary e2e run metadata and reviewer reports are schema-valid | `pytest tests/test_scripts_smoke.py::test_primary_e2e_workflow_run_artifacts_schema_pass` |
| Homogeneous plus focused keeps baseline reviewers unfocused | `pytest tests/test_scripts_smoke.py::test_review_packet_schema_allows_plus_focused_baseline_without_focus_zone` |

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
