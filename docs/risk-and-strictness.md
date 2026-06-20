# Risk and Strictness

Strictness is a workflow depth control, not the main abstraction.

The workflow defines what type of work is being done and declares its
`default_strictness`. Project bindings and workflow runs use the workflow default
unless they explicitly record a `strictness_override` with a reason.

The effective strictness controls how deep gates, review, and evidence should go
for one concrete binding or run.

## Default and Override

```text
workflow.default_strictness
  baseline depth for the workflow's normal use

binding.strictness
  optional project-level override

run.strictness
  recorded effective value for a concrete run
```

An override is appropriate only when the project risk, pilot scope, regulatory
context or task constraints differ materially from the workflow default.

## Current Compatibility Levels

| Level | Name | Typical use |
|---|---|---|
| L0 | lightweight | Small low-risk changes. |
| L1 | controlled | Scoped changes with boundaries and evidence. |
| L2 | contract | Contract-first work with BDD scenarios and impact map. |
| L3 | reviewed | Independent review agents and fusion summary. |
| L4 | critical | Adversarial review, hidden regressions, scenario simulation, human decision points. |

These `L*` labels are compatibility identifiers, not a requirement that
AgentsFlow must keep five meaningful modes forever. A future slice may collapse
the taxonomy to two or three project-facing levels, as long as workflow defaults,
effective strictness and override reasons remain explicit.

## Risk signals

Override upward when work touches:

- architecture decisions;
- memory/policy/tool permissions;
- system prompts;
- safety boundaries;
- public APIs;
- persistence or migrations;
- low-latency/hot-path code;
- authentication/authorization;
- irreversible operations.

Override downward only for bounded pilots, examples, fixtures or deliberately
reduced-scope work, and record the reason.

## Risk surfaces

Strictness answers "how much control depth?". Risk surfaces answer "which
failure modes must be named and covered?".

AgentsFlow keeps a small upstream catalog so agents use stable vocabulary across
projects. A concrete project or task selects the surfaces that are actually in
scope, and may add project-local surfaces in its `.agentsflow/` overlay when the
upstream catalog is too generic. Project-local additions must include a short
definition and required path classes; they must not silently redefine upstream
surface names.

Baseline upstream surfaces:

| Surface | Use when the work changes or depends on... |
|---|---|
| `authority_boundary` | who may decide, delegate, approve or execute an action |
| `policy_authorization` | allow/deny policy, approval gates, safety checks or routing policy |
| `context_reentry` | tool, reviewer, user or runtime observations re-entering agent context |
| `audit_persistence` | durable logs, ledgers, traces, event history or compliance records |
| `data_privacy` | sensitive user/project data, retention or disclosure boundaries |
| `secret_handling` | API keys, tokens, credentials or secret-like nested values |
| `external_io` | calls to external providers, services, CLIs or tools |
| `filesystem_access` | file reads/writes, path allowlists, generated files or destructive writes |
| `network_access` | outbound/inbound network behavior, retries, timeouts or isolation |
| `runtime_budget` | token, cost, quota, step, retry or execution budgets |
| `timeout` | operation timeouts, cancellation and post-timeout state |
| `concurrency` | races, locks, idempotency or simultaneous actors |
| `state_migration` | migrations, schema evolution or compatibility windows |
| `public_api_contract` | public protocol, API, CLI, schema or user-visible contract |
| `persistence_consistency` | read-after-write, partial writes, rollback or authoritative state |
| `human_approval` | required human decisions, overrides or acceptance of residual risk |
| `irreversible_action` | deletes, payments, external side effects or hard-to-revert actions |

Project initialization should recommend a project-level risk-surface policy, but
feature contracts still select the feature-specific subset. A surface is not
"covered" merely because it is listed; it is covered only when required path
classes are bound to checks or explicitly deferred with human-approved residual
risk.

## Required path classes

Path classes are a compact way to classify tests and evidence. They are not a
new test taxonomy; they are labels on existing behavior bindings, gate checks and
evidence rows.

Common path classes:

| Surface | Required path classes when selected |
|---|---|
| `authority_boundary` | `valid_delegation`, `malformed_request`, `direct_bypass_attempt` |
| `policy_authorization` | `allowed`, `denied`, `disabled_or_approval_required_when_applicable` |
| `context_reentry` | `success_observation_admitted`, `non_success_observation_admitted`, `untrusted_observation_rejected` |
| `audit_persistence` | `success_attempt_persisted`, `denied_attempt_persisted`, `rejected_attempt_persisted`, `timeout_attempt_persisted`, `downstream_failure_after_attempt_persisted` |
| `secret_handling` | `top_level_secret_redacted`, `nested_mapping_secret_redacted`, `nested_list_secret_redacted` |
| `runtime_budget` | `budget_available`, `budget_exhausted_before_execution`, `budget_exhausted_after_execution_before_finalization` |
| `timeout` | `operation_completes_before_timeout`, `operation_timeout`, `post_timeout_safe_response` |
| `external_io` | `provider_success`, `provider_denial_or_error`, `provider_timeout`, `side_effect_recorded_or_blocked` |
| `filesystem_access` | `allowed_path`, `forbidden_path`, `path_traversal_or_escape_attempt`, `write_failure_no_partial_authoritative_state` |
| `network_access` | `allowed_endpoint`, `denied_endpoint`, `network_failure`, `retry_or_no_retry_policy_observed` |
| `persistence_consistency` | `write_success_visible`, `write_failure_no_partial_authoritative_state`, `read_after_write_consistency` |
| `human_approval` | `approval_present`, `approval_missing_blocks`, `override_recorded_with_authority` |
| `irreversible_action` | `precondition_met`, `precondition_missing_blocks`, `attempt_persisted_before_or_with_side_effect`, `rollback_or_compensation_defined_when_possible` |

For surfaces not listed above, the task contract must define the path classes in
plain language. The definition should stay small: enough to drive tests and
review, not an exhaustive hazard analysis.

## Failure Path Matrix

A Failure Path Matrix is the feature-local table that turns selected surfaces
into concrete coverage obligations. It is required when a selected risk surface
has denial, failure, timeout, rejection, persistence or authority semantics that
could otherwise be missed by happy-path tests.

Recommended columns:

| Column | Meaning |
|---|---|
| `id` | stable row id, for example `FPM-001` |
| `risk_surface` | selected surface from the project or upstream catalog |
| `path_class` | required path class being covered or explicitly deferred |
| `trigger` | concrete input, state, event or failure that exercises the path |
| `expected_authority` | actor or policy allowed to decide the result |
| `expected_context_or_state` | context/state mutation that must or must not happen |
| `expected_audit_or_persistence` | durable record requirement when applicable |
| `must_not_happen` | forbidden bypass, leak, partial write, silent success or stale evidence |
| `evidence_binding` | behavior binding, gate check, manual evidence or approved deferral |

For example, `audit_persistence` should not be represented only by "success
action is logged". A serious feature usually also needs denied, rejected,
timeout, and downstream-failure-after-attempt rows, because those are the paths
where evidence is easiest to lose.

## Evidence classification

Behavior bindings, gate reports and evidence reports may classify each check by:

```yaml
risk_surfaces:
  - audit_persistence
path_class: denied_attempt_persisted
evidence_class: test
```

`evidence_class` should be one of the existing gate/check categories such as
`test`, `script`, `manual_evidence`, `trace_assertion`, `log_assertion`,
`static_analysis`, `dynamic_analysis`, `security_scan` or `external_tool`.

The classification lets reviewers and humans see whether the hard paths were
covered without inventing a parallel test-management system.

## Review topology from risk surfaces

The default primary review topology remains `homogeneous-dual`. A workflow or
project binding should select a focused or heterogeneous topology only when the
selected risk surfaces justify different reviewer attention.

Escalate from `homogeneous-dual` to focused or heterogeneous review when a task
selects high-control surfaces such as:

```text
authority_boundary
policy_authorization
audit_persistence
secret_handling
data_privacy
external_io
filesystem_access
network_access
runtime_budget
timeout
persistence_consistency
human_approval
irreversible_action
```

Keep the escalation minimal. Prefer adding one focused reviewer or one explicit
heterogeneous role set that maps to existing `profiles/reviewer_roles/` contracts
instead of creating new reviewer categories. The review packet must include the
selected risk surfaces, Failure Path Matrix, known validated blockers, and latest
green evidence references.

## Evidence freshness and material changes

Verification and review evidence is fresh only relative to the latest material
change. A material change is any change to:

- task contract or scope;
- selected risk surfaces or Failure Path Matrix;
- behavior bindings;
- workflow, gate, review or authority policy;
- implementation that affects a bound behavior or selected risk surface;
- mandatory evidence, gate output or reviewer packet content;
- schema, validator or project overlay used as evidence.

After a material change, the run must record a new `material_change_id`, refresh
the relevant green verification evidence, and run review again when the review
packet or validated blocker state materially changed. Non-material editorial
changes may be recorded without rerunning gates or review.

## Structured command evidence

Raw logs are useful but not enough as the only evidence contract. Command
evidence should record structured fields:

```yaml
command:
cwd:
started_at:
finished_at:
exit_code:
result: pass # pass | fail | skip | blocked
output_summary:
artifact_paths: []
raw_log_path: null
```

Projects may choose whether to persist raw logs by default, but the structured
summary is mandatory for evidence that supports a gate decision.

## Audit and persistence precision

When a selected surface includes audit or persistence, the task contract should
state:

- what event or attempt is recorded;
- when it is recorded relative to the action or side effect;
- which actor or authority is recorded;
- which correlation id or run id links it to evidence;
- which fields must be redacted or omitted;
- whether failures, denials, timeouts and downstream failures are recorded;
- what read-back or consistency proof is required.

This precision keeps audit requirements testable instead of relying on vague
"log it" language.

## Anti-overload rule

Do not ask the human to choose a heavy profile as routine setup. The workflow
default should already encode normal risk. Heavy overrides should be justified by
specific project or task evidence.

## Test-framed implementation is not strictness-scaled

The red-before/green-after discipline (ADR-0017) is not an L3/L4-only behavior. It
applies whenever a workflow has a `kind: implementation` phase, independent of the
effective strictness.
