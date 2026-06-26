# Review Control Model

## Purpose

This document defines the common control model for verification gates, review agents,
and fusion stages.

The model is intentionally flexible: each workflow decides how many gates and
reviewers it needs. The project core defines only the shared interfaces and
non-negotiable safety rules.

## Core rules

### Rule 1: Review agents run after verification and remain read-only

**Review agents are read-only evaluators and must run only after a verification gate.**

A review agent does not execute tests, run scripts, mutate files, generate patches,
update contracts, or repair evidence. It inspects already-produced artifacts and
returns a structured review report.

The verification gate is responsible for executing workflow-defined verification
instruments and collecting evidence. Instruments may include tests, deterministic
scripts, BDD runners, static/dynamic analysis, debuggers, profilers, fuzzers,
network traffic analysis, benchmarks, security scanners, custom domain tools and
manual evidence checks.


### Rule 2: Review findings are candidate findings until relevance validation

**Review-agent findings are not authoritative truth.**

A review agent produces candidate findings, hypotheses, risks, and requests for
additional verification. Those findings become accepted issues only after the
main/orchestrating agent validates their relevance against:

- the task contract;
- the artifact or diff under review;
- the verification gate report;
- the evidence bundle and logs;
- relevant ADRs and accepted decisions;
- the selected workflow, profile, and non-goals.

This rule prevents review agents from becoming unquestioned authorities. It also
protects the workflow from false positives, irrelevant objections, duplicate
findings, and reviewer-specific taste being treated as blockers.

The main/orchestrating agent may classify each reviewer finding as:

```text
accepted-relevant
rejected-irrelevant
needs-more-evidence
duplicate
human-decision-required
```

A P0/P1 candidate finding must not be silently discarded. If the
main/orchestrating agent rejects or downgrades a plausible blocker, it must record
the reason and the evidence used for that relevance decision.



### Rule 3: Concrete gates are executable through deterministic runners

**Every concrete gate included in a workflow must have a deterministic runner entrypoint.**

BDD scenarios, contracts, ADRs and Markdown specifications can define what must be
checked, but they are not executable gates by themselves. A concrete gate must point
to a gate manifest and runner that produce structured evidence and a gate report.

The detailed model is defined in `docs/gate-executability-model.md`.

```text
implementation or artifact creation
  ↓
verification gate
  - runs tests
  - runs deterministic scripts
  - runs contract/boundary/impact/evidence checks
  - produces verification report and evidence bundle
  ↓
read-only review agents
  - inspect contract, diff/artifact, logs, verification report, evidence
  - classify issues
  - request additional verification only as a finding, not by running it
  ↓
fusion / decision support
  - synthesizes reviewer reports
  - preserves candidate blocking issues
  - emits recommended decision summary
  ↓
main-agent relevance validation / final triage
  - validates whether findings are relevant to the actual task
  - accepts, rejects, deduplicates, or escalates findings
  - records reasons for rejecting/downgrading plausible blockers
```



## Interaction protocol summary

The detailed review-agent interaction protocol is defined in
`docs/review-agent-interaction-protocol.md`.

In summary:

- reviewer findings start as `candidate-unvalidated`;
- P0/P1 candidate findings and mandatory evidence gaps must be preserved;
- the main/orchestrating agent validates findings with a structured decision matrix;
- the default review-cycle exit criterion is
  `no_validated_blockers_or_mandatory_evidence_gaps`;
- repeated review agents are not rerun when only non-blocking findings remain;
- workflows may override review-cycle policy explicitly in `workflow.yaml`.

### Default blocking rule

A finding blocks acceptance by default when it has been validated as relevant and
its validated severity is P0/P1 with a grounded blocker path, or when mandatory
verification evidence is missing.

Validated P0/P1 severity requires all four fields below:

- violated requirement: contract, accepted decision, ADR, gate policy, safety
  rule, authority boundary or mandatory evidence requirement;
- concrete evidence: reviewed artifact, diff, report, log or recorded evidence
  reference;
- blocker path: the violated requirement and how the artifact can violate
  acceptance if unchanged;
- acceptance consequence: why the workflow cannot accept the artifact before the
  issue is fixed or the requirement is explicitly changed.

A candidate finding that lacks any of those fields is not a validated P0/P1 by
default. It may be `needs-more-evidence`, downgraded to P2/P3/NOTE, classified as
a contract gap, or rejected with reason. Risk-surface or Failure Path Matrix
membership alone is never a blocker path.

Candidate blockers must be explicitly validated, rejected with reason, marked as
duplicate, escalated, or resolved by additional evidence.

### Remediation triage before fix loops

Validated findings do not automatically authorize adding new workflow machinery.
Before starting a fix-loop, the main/orchestrating agent records the remediation
layer in the existing finding-validation or review-cycle report.

Use this order by default:

1. remove responsibility that belongs to another layer;
2. fail closed and require proof from the owning workflow or evidence producer;
3. use an existing contract, field or evidence reference;
4. add a small local check;
5. add a new schema field, artifact class or mechanism only with explicit
   rationale for why simpler remediations are insufficient.

If a finding exposes a wrong-layer responsibility, the preferred fix is to reduce
or move that responsibility, not to make the current evaluator or workflow prove
more of the system.

### Default exit rule

The default exit rule is:

```text
Exit the review cycle when there are no validated blocking findings and no
mandatory evidence gaps.
```

## Core vs workflow responsibilities

**Core defines contracts. Workflow defines composition.**

The project core defines the shared interfaces and invariants:

```text
Gate = workflow control point with explicit exit criteria and authority mode.
Reviewer = independent read-only evaluator.
Fusion = synthesis of reviewer outputs.
Evidence = artifact proving what was checked.
Topology = configuration of the review process.
Blocking issue = issue that cannot be overridden by majority vote.
```

Gate authority mode must be explicit when it affects workflow behavior:

```text
deterministic_gate = runner/check evidence -> gate report
review_gate = reviewer reports -> main-agent relevance validation
human_mediated_gate = evidence/review synthesis -> recorded human decision
```

The project core does **not** decide that every task must use review, full gates,
or fusion. Those choices belong to workflows and profiles. When a primary review
gate is enabled, the core requires at least two reviewers. Collision-control is
not a one-reviewer shortcut: after the main/orchestrating agent rejects or
downgrades one or more plausible blocker-path candidate findings in a review
cycle, it records one collision batch and sends that batch to two fresh-context
control reviewers.

A workflow decides:

- how many reviewers to run;
- which reviewer roles to use;
- which gates are mandatory or optional;
- which gate authority modes are used;
- whether fusion is required;
- what counts as pass/fail/needs-human-decision;
- which checks belong inside the verification gate.

Workflow definitions may reference the shared policy instead of duplicating it:

```yaml
review:
  control_policy: standard-review-control
review_cycle:
  policy: standard-review-control
  materiality_classification_source:
    - finding-validation-report.md
    - review-cycle-report.md
```

Under the standard policy, post-review materiality is recorded in the run's
finding-validation or review-cycle report. Workflow YAML should not repeat the
full materiality trigger list, blocker defaults or validation-required list
unless the workflow intentionally overrides the shared policy and records the
override reason.

The core only requires that:

- every concrete gate has a manifest, deterministic runner, explicit inputs, instruments, required evidence, outputs, result states and pass policy;
- every review agent returns a structured report;
- review agents are read-only and run after the verification gate;
- review agents start from fresh zero conversation context and never inherit a forked main-agent/orchestrator context;
- primary review gates use at least two reviewers;
- review-agent findings are candidate findings until validated for relevance;
- fusion preserves P0/P1 candidate issues and does not erase blockers by majority vote;
- the main/orchestrating agent validates relevance before findings become accepted issues;
- missing evidence is surfaced rather than silently accepted.

## Review topology interface

Review topology is workflow/profile metadata. Common topology names are:

- `none`;
- `homogeneous-dual`;
- `homogeneous-plus-focused`;
- `heterogeneous-variable`;
- `collision-control` for rejected or downgraded plausible blocker-path
  collision batches only, not as a primary gate.

A topology declares reviewer roles, independence requirements, whether fusion is
required, and blocking policy. See `schemas/review-topology.schema.json`.

`single-reviewer` is not a valid primary review topology in v0.2. Collision
control is modeled as a focused two-reviewer batch in the review-cycle policy,
not as the normal gate topology.

Heterogeneous role names are not free-form hints. A role id such as `adversarial`
must resolve to a role definition in `profiles/reviewer_roles/`. The role
definition explains the primary focus, required reports and forbidden actions.
Focus zones may overlap, and every reviewer must still report any plausible P0/P1
blocker noticed outside its primary focus.

### Risk-driven topology selection

The default primary review topology remains `homogeneous-dual`: two independent
generalist reviewers using the same prompt, same packet, same rubric and same
output schema. A workflow, project binding or task contract should select
`homogeneous-plus-focused` or `heterogeneous-variable` only when the selected
risk surfaces justify extra focused attention.

Risk-driven escalation is recorded as metadata, not inferred silently:

```yaml
review:
  topology: heterogeneous-variable
  topology_source: risk_surface_profile
  selected_risk_surfaces:
    - authority_boundary
    - audit_persistence
  escalation_reason: "Authority and audit failure paths need architecture, verification and adversarial focus."
```

The review packet for each reviewer must include:

- selected risk surfaces;
- Failure Path Matrix or a pointer to it;
- behavior bindings classified by risk surface/path class;
- latest green gate evidence after the latest material change;
- known validated blockers and their status.

Reviewers treat the packet's existing `focus_zone`, `risk_surface_profile`,
`failure_path_matrix`, `changed_files`, `verification_gate_report`,
`evidence_freshness`, and `known_blockers` as relevance inputs. These fields are
the review map; workflows should not add a parallel focus-map field unless an
accepted design change removes or replaces the existing inputs.

This keeps risk-driven review grounded in the contract and evidence instead of
turning role selection into reviewer preference.

### Supplemental human-requested review

After a green gate and primary review/fusion, the human may request supplemental
review. Supplemental review is allowed, but it must be recorded as a separate
review request with:

- requester and reason;
- reviewed artifact or diff;
- reviewer count, role set and context policy;
- whether the review can affect acceptance;
- the exact evidence packet supplied.

Supplemental findings are still candidate findings. They reopen the fix loop
only when the main/orchestrating agent validates a P0/P1 finding or mandatory
evidence gap. If no P0/P1 finding is validated and no material artifact change
occurs afterward, the workflow must not run another primary review gate merely
because supplemental review happened.

### Evidence freshness

Reviewers should inspect evidence produced after the latest material change. A
review packet should therefore identify the current `material_change_id`, the
latest green verification gate for that change, and whether reviewer inputs were
prepared after that gate.

If a task contract, behavior binding, selected risk surface, Failure Path Matrix,
gate policy, implementation behavior or mandatory evidence changes materially
after review, the prior review is stale for the affected scope. The run records
the invalidation reason and refreshes verification and review according to the
workflow's review-cycle policy.

A closure-only review may confirm that previously validated findings were fixed,
but it is not an acceptance review gate after a material change. The next
acceptance-capable review must inspect the full current review packet and must
ask reviewers both to confirm closure of prior findings and to look for new
P0/P1 blockers across the changed scope.

## Actor classes


### Main/orchestrating agent

The main/orchestrating agent coordinates the workflow and owns final triage of
reviewer findings. It is not allowed to pretend that reviewer findings are facts
without checking relevance.

It must:

- compare each finding against the contract, diff/artifact, evidence, workflow,
  ADRs, and non-goals;
- validate P0/P1 findings with the four-part blocker rule above;
- classify late accepted blockers as `contract_gap`, `verification_gap`,
  `review_packet_gap`, `material_fix_regression`, `valid_late_discovery`,
  `false_positive` or `process_hygiene_nonblocking`;
- preserve plausible blockers until they are accepted, rejected with reason, or
  escalated to a human;
- avoid implementing reviewer suggestions blindly;
- record relevance-validation decisions in the final evidence or decision report.

It may:

- accept a finding as relevant;
- reject a finding as irrelevant with a concrete reason;
- deduplicate overlapping findings;
- request another verification gate run;
- escalate disputed findings to a human.

It must not:

- silently drop P0/P1 candidate findings;
- treat reviewer taste as a requirement;
- forward unvalidated findings to an implementation agent as mandatory changes.

### Verification gate

A verification gate is an executable control point.

It may:

- run tests;
- run deterministic scripts;
- validate contracts and manifests;
- inspect git diff and changed files;
- run boundary checks;
- run impact-map checks;
- run evidence validation;
- collect logs and command outputs;
- produce a gate report and evidence bundle.

It must not:

- silently weaken tests;
- silently ignore failed required checks;
- turn uncertain verification into a pass;
- hide skipped checks.

### Review agent

A review agent is a read-only evaluator.

It may inspect:

- task contract;
- relevant ADRs/specifications;
- diff or artifact under review;
- verification gate report;
- test results and logs produced by the gate;
- evidence report;
- prior reviewer reports only when explicitly included in a control-review or
  fusion packet.

It starts from fresh zero conversation context. It must not receive a forked
conversation from the main/orchestrating agent.

It must not:

- run tests;
- call verification scripts;
- modify files;
- generate patches;
- update contracts;
- update evidence;
- silently accept missing evidence;
- claim verification was performed unless the gate report contains it.

A review agent may recommend additional checks, but the recommendation must be
returned as a finding such as `needs-additional-verification`. The workflow or a
human may then decide whether to re-run the verification gate.

### Fusion stage

Fusion is a read-only synthesis stage over review reports and gate artifacts. It
produces decision support, not authoritative truth. Fusion may group, compare,
and prioritize reviewer findings, but those findings still require relevance
validation by the main/orchestrating agent before they become accepted issues.

It must:

- identify consensus;
- identify disagreements;
- preserve P0/P1 candidate issues;
- classify candidate blocking and non-blocking findings;
- identify human-decision items;
- produce a recommended decision summary;
- mark findings as candidate/unvalidated unless relevance validation has occurred.

It must not:

- run tests;
- modify artifacts;
- erase a candidate blocking issue by majority vote;
- convert missing evidence into pass;
- claim that a reviewer finding is accepted truth without relevance validation.

### Implementation agent

Implementation agents are a separate future actor class.

They may eventually be allowed to edit files, run tests, call tools, and iterate on
implementation. Those permissions are explicitly **not** inherited by review agents.

Until an implementation-agent protocol is introduced, all `reviewer-*` skills are
read-only by definition.

## Gate interface

A gate should declare:

```yaml
name: verification_gate
kind: gate
inputs:
  - contract
  - diff_or_artifact
  - impact_map
  - selected_profile
checks:
  - contract_lint
  - gherkin_lint
  - boundary_check
  - impact_map_check
  - evidence_validate
  - workflow_required_tests
outputs:
  - gate_report
  - evidence_bundle
  - command_log
result_states:
  - pass
  - pass_with_notes
  - fail
  - needs_human_decision
  - blocked
```

## Review-agent interface

A review agent should declare:

```yaml
name: reviewer-verification
kind: review_agent
mode: read_only
runs_after:
  - verification_gate
allowed_inputs:
  - contract
  - diff_or_artifact
  - gate_report
  - evidence_bundle
  - logs
context_policy:
  start_mode: fresh_context
  fork_conversation_context: false
forbidden_actions:
  - run_tests
  - run_scripts
  - modify_files
  - create_patch
outputs:
  - reviewer_report
  - candidate_findings
finding_lifecycle:
  initial_status: candidate-unvalidated
  requires_relevance_validation_by: main_orchestrating_agent
```

## Workflow binding

Each workflow decides:

- whether a verification gate is required;
- which tests/scripts are included in the gate;
- which review agents run after the gate;
- whether reviewers run independently or sequentially;
- whether fusion is required;
- what result states block acceptance.

The common rules remain unchanged:

- **review agents consume verification evidence; they do not produce it by running
  checks themselves.**
- **review-agent findings are candidate findings until the main/orchestrating
  agent validates their relevance.**

## v0.1.6 actor-model clarifications

### Planning Agent is reserved, not default

Current AgentsFlow workflows treat planning as a tight human + main/orchestrating-agent
collaboration. `Planning Agent` is a reserved optional future role, similar to
`Implementation Agent`; it is not the default owner of planning phases.

### Verification Gate supports arbitrary declared instruments

A verification gate is not limited to tests and simple scripts. It may run any
workflow-declared verification instruments, including static analysis, dynamic
analysis, debuggers, trace/log/network analysis tools, profilers, fuzzers,
security scanners, performance benchmarks, and domain-specific tools.

The gate's job is to produce evidence, not taste-based review.

### Review-agent tool exceptions

Review agents are read-only by default. A reviewer may use tools only when the
workflow, reviewer manifest, or reviewer prompt explicitly grants that permission.
Tool-enabled review is exceptional, scoped, and still produces candidate findings.
It does not replace verification-gate evidence.

### Fusion is synthesis, not orchestration

Fusion Agent is read-only synthesis by default. It consumes reviewer reports,
finding-validation reports, gate reports, evidence, and workflow context. It does
not launch reviewers, run gates, run tests, or modify artifacts unless a future
workflow explicitly introduces a separate `fusion-as-orchestrator` mode.

Fusion may recommend additional review or verification, but the main/orchestrating
agent remains responsible for invoking it.
