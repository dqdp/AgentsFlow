# Review Agent Interaction Protocol

## Purpose

This document defines how review agents interact with the main/orchestrating
agent in AgentsFlow workflows.

It refines the Review Control Model with a concrete loop protocol, blocking
finding definitions, default exit criteria, and a structured relevance-validation
decision matrix.

## Non-negotiable rules

### Rule 1: Review agents run after verification and remain read-only

Review agents consume verification evidence. They do not produce it by running
checks themselves.

They must not:

- run tests;
- run verification scripts;
- modify files;
- create patches;
- update contracts;
- update evidence;
- silently accept missing evidence.

### Rule 2: Review findings are candidate findings until relevance validation

A review-agent finding is a candidate finding, not authoritative truth.

A candidate finding becomes an accepted issue only after the main/orchestrating
agent validates it against the contract, artifact/diff, gate report, evidence,
accepted decisions, workflow profile, scope, and non-goals.

### Rule 3: Reviewers start from fresh context

Review agents start from zero conversation context. They must not receive a
forked main-agent/orchestrator conversation. The orchestrator prepares an explicit
review packet with referenced artifacts; that packet is the reviewer input.

Primary review gates run at least two reviewers. Collision-control also uses two
fresh-context control reviewers. When the orchestrator rejects or downgrades one
or more blocker-level candidate findings in a review cycle, it records one
collision batch and sends that focused packet to those two control reviewers.

## Review loop overview

```text
implementation / artifact creation
  ↓
verification_gate
  - runs tests and deterministic checks
  - produces gate report and evidence bundle
  ↓
review_agents
  - read-only independent evaluation
  - produce candidate findings
  ↓
fusion_stage, if enabled
  - groups findings, preserves candidate blockers, records disagreement
  ↓
main_agent_relevance_validation
  - validates each acceptance-affecting finding
  - applies the decision matrix
  ↓
loop decision
  - exit if no validated blocking findings remain
  - otherwise revise / re-verify / re-review according to workflow policy
```

## Finding lifecycle

```text
candidate-unvalidated
  ↓
validated status:
  accepted-relevant
  rejected-irrelevant
  needs-more-evidence
  duplicate
  human-decision-required
```

A candidate finding must keep its source reviewer, severity, evidence references,
and validation status throughout the workflow.

## Blocking finding definitions

AgentsFlow distinguishes **candidate blocking findings** from **validated blocking
findings**.

### Candidate blocking finding

A candidate blocking finding is a reviewer/fusion finding that could block
acceptance if it is validated as relevant.

By default, a finding is a candidate blocker when either:

- it is marked `P0` or `P1`; or
- it reports missing required evidence for a mandatory gate/check; or
- it reports a plausible violation of contract, accepted ADR, explicit boundary,
  safety rule, or workflow non-negotiable; or
- it identifies that the artifact cannot be reviewed because required input is
  absent, malformed, stale, or contradictory.

Candidate blockers must not be removed by majority vote or silently ignored.

### Validated blocking finding

A validated blocking finding is a candidate finding that the main/orchestrating
agent validates as acceptance-blocking.

By default, a finding is a validated blocker when:

```text
validation_status in {accepted-relevant, needs-more-evidence, human-decision-required}
AND severity in {P0, P1}
```

Workflow profiles may tighten or relax this default, but must do so explicitly.

### Default severity meaning

| Severity | Default meaning | Blocking by default? |
|---|---|---|
| P0 | Critical issue: unsafe, destructive, security/privacy breach, data loss, legal/compliance issue, impossible-to-review artifact, or violation that invalidates the workflow result. | Yes |
| P1 | Major issue: contract violation, accepted decision/ADR violation, scope boundary violation, missing required evidence, failed required gate, regression risk that invalidates acceptance, or ambiguous acceptance criteria that prevents safe implementation. | Yes |
| P2 | Important concern: should be fixed or tracked, but does not by itself invalidate acceptance. | No |
| P3 | Minor issue, polish, small inconsistency, optional improvement. | No |
| NOTE | Observation or suggestion. | No |

### Missing evidence rule

Missing evidence for a mandatory workflow check is blocking by default, even if no
reviewer claims the implementation is wrong.

The correct status is usually:

```text
needs-more-evidence
```

not `pass`.

For implementation workflows, an absent captured failing run (red) for a required
scenario is itself a missing-mandatory-evidence condition (ADR-0017): a green-only
evidence bundle is an evidence gap, not a pass.

## Default loop exit criterion

The default AgentsFlow exit criterion for review cycles is:

```text
Exit when the latest relevance-validation pass contains no validated blocking
findings and no mandatory evidence gaps.
```

More explicitly, repeated review agents are not rerun when all of the following
are true:

1. The required verification gate has passed or produced an accepted
   pass-with-notes result.
2. Every P0/P1 candidate finding has a recorded relevance-validation status.
3. No finding remains with a blocking status:
   - `accepted-relevant` with P0/P1 severity;
   - `needs-more-evidence` for mandatory evidence;
   - `human-decision-required` for acceptance-affecting issues.
4. The fusion report, if enabled, has no unresolved candidate blockers.
5. The workflow-specific exit policy does not require another review round.

Non-blocking P2/P3/NOTE findings may be recorded as backlog, notes, or follow-up
work without triggering another review cycle.

## Rerun policy

Review agents should be rerun only when review input materially changes.

Default rerun triggers:

- accepted P0/P1 blocker was fixed or mitigated;
- missing mandatory evidence was produced;
- task contract or accepted scope changed;
- verification gate was rerun and produced materially different evidence;
- implementation/artifact changed in a way that affects previous findings;
- human/orchestrator requests a new review cycle;
- workflow profile explicitly requires a second independent pass.

Default non-triggers:

- only P2/P3 notes remain and any fixes are non-material;
- purely editorial changes to reports;
- duplicate finding consolidation;
- main agent rejects a candidate blocker as irrelevant with evidence-based reason;
- fusion rewording without new findings.

### Materiality classification after fixes

After any fix made in response to review, the main/orchestrating agent must
classify the fix before deciding whether to rerun reviewers. The severity of the
original finding and the materiality of the fix are separate decisions: a P2
finding can still lead to a material fix if the fix changes what future
reviewers or validators must judge.

The fix is **material** when it changes any review input that can affect
acceptance:

- task contract, scope, non-goals, acceptance criteria or behavior bindings;
- workflow, gate, review-cycle, reviewer, evidence-probe or collision-control
  policy;
- schemas, validators, deterministic checks or test fixtures used as contract
  evidence;
- project overlay, workflow binding, gate binding, authority policy or evidence
  storage policy;
- verification gate results, mandatory evidence or the evidence bundle;
- examples or docs that are presented as authoritative evidence for the current
  workflow.

A material fix requires the relevant verification/checks to be refreshed and the
review-cycle policy to be applied to the updated input. If the change fixes an
accepted P0/P1 blocker, adds mandatory evidence, changes the contract, or changes
the reviewed artifact in an acceptance-affecting way, reviewers are rerun.
Material rerun triggers take precedence over `do_not_rerun_on` entries.

The fix is **non-material** when it only changes editorial wording, report
formatting, duplicate grouping, non-authoritative notes, or non-source-of-truth
documentation without changing contracts, schemas, validators, gates, evidence,
bindings, reviewed behavior or examples used as evidence. Non-material fixes do
not rerun reviewers by default.

The classification must be recorded in the finding-validation or review-cycle
report. This prevents both failure modes: rerunning reviewers after every
nonblocking cleanup, and silently accepting a nonblocking cleanup that changed a
contract-bearing artifact.

Exception: if one or more blocker-level candidate findings are rejected or
downgraded by the main/orchestrating agent and the workflow records a collision,
it launches two fresh-context control reviewers focused on the collision batch
and the orchestrator collision reason. This is not a replacement for the primary
review gate, and it is batched per review cycle rather than per finding.

`max_review_cycles` is a project policy or workflow-binding decision. Upstream
workflow definitions may declare that the value is required, but they should not
pretend that a single hardcoded integer is universal for every concrete project.

## Main-agent relevance-validation procedure

The main/orchestrating agent validates findings with a structured procedure.
The goal is not to “argue with reviewers”, but to prevent false positives and
context-insensitive findings from becoming mandatory work.

### Inputs

For each finding, the main agent must inspect the available relevant inputs:

- task contract or reviewed artifact brief;
- diff/artifact under review;
- verification gate report;
- evidence bundle and command logs;
- relevant ADRs and accepted decisions;
- workflow profile, strictness, review topology;
- scope, non-goals, and explicit exclusions;
- prior validated findings, if any.

### Procedure

1. **Normalize** the finding.
   - Assign or preserve a stable finding id.
   - Preserve source reviewer, severity, claim, evidence references, and requested action.

2. **Check grounding.**
   - Is the finding tied to a concrete contract clause, diff location, artifact section,
     gate output, log entry, ADR, or missing evidence?
   - If not grounded, mark `needs-more-evidence` or `rejected-irrelevant` depending on severity and plausibility.

3. **Check scope relevance.**
   - Is the finding inside the task/workflow scope?
   - Is it explicitly excluded by non-goals?
   - Is it a preference/taste issue rather than a contract/evidence issue?

4. **Check factual correctness.**
   - Does the cited evidence actually support the finding?
   - Does the finding contradict accepted decisions or current artifacts?

5. **Check acceptance impact.**
   - Would accepting the artifact violate the contract, mandatory gate, ADR, safety rule,
     scope boundary, or required evidence policy?

6. **Classify validation status.**
   - Choose exactly one validation status.
   - Record the reason and evidence checked.

7. **Determine loop action.**
   - `fix-or-revise`
   - `rerun-verification-gate`
   - `rerun-review-agents`
   - `record-nonblocking-followup`
   - `escalate-human`
   - `exit-review-cycle`

## Decision matrix

| Condition | Validation status | Blocking? | Default action |
|---|---|---:|---|
| Finding is supported by contract/evidence and severity is P0/P1 | accepted-relevant | Yes | Fix/revise, then rerun verification gate and relevant review cycle. |
| Finding is supported by contract/evidence but severity is P2/P3/NOTE | accepted-relevant | No | Record follow-up or fix if cheap; no review rerun by default. |
| Finding may be valid but required evidence is missing | needs-more-evidence | Yes if mandatory evidence or P0/P1; otherwise workflow-defined | Run verification gate/checks; rerun review only if evidence materially changes. |
| Finding concerns an explicit non-goal or out-of-scope preference | rejected-irrelevant | No | Record reason; no rerun. |
| Finding is factually contradicted by contract/diff/evidence | rejected-irrelevant | No | Record contradiction; no rerun. |
| Finding duplicates an already validated issue | duplicate | Inherits original | Link to original; no rerun. |
| Finding conflicts with accepted ADR or requires changing an accepted decision | human-decision-required | Yes until resolved | Escalate to human / ADR workflow. |
| Reviewers disagree on a P0/P1 issue and evidence is insufficient | needs-more-evidence or human-decision-required | Yes | Produce/refresh evidence or escalate. |
| Fusion surfaces a candidate blocker from one reviewer only | candidate-unvalidated, then one validation status from the lifecycle | Depends on validation | Majority cannot erase it; validate explicitly. |

## Final review-cycle decision states

| State | Meaning |
|---|---|
| pass | No validated blockers; no mandatory evidence gaps. |
| pass-with-notes | No validated blockers; non-blocking findings remain. |
| needs-changes | At least one accepted relevant blocker requires revision. |
| needs-verification-evidence | Missing mandatory evidence blocks acceptance. |
| human-decision-required | A relevant issue requires human/ADR decision. |
| blocked | Workflow cannot proceed due to P0/P1 blocker, failed gate, or invalid evidence. |

## Workflow binding

Each workflow may define:

```yaml
review_cycle:
  default_exit_when: no_validated_blocking_findings
  max_review_cycles_required: true
  max_review_cycles_source: project_policy_or_workflow_binding
  rerun_review_on:
    - accepted_blocker_fixed
    - mandatory_evidence_added
    - contract_changed
    - material_artifact_change
  do_not_rerun_on:
    - nonblocking_findings_with_non_material_fixes_only
    - duplicate_consolidation
    - irrelevant_findings_rejected_with_reason
  blocking_default:
    severities:
      - P0
      - P1
    missing_mandatory_evidence_blocks: true
```

Workflows can override this policy, but the override must be explicit and visible
in `workflow.yaml`.

## Relationship to fusion

Fusion groups and prioritizes candidate findings. It does not validate relevance.

Fusion must preserve candidate blockers and hand them to the main/orchestrating
agent for validation. Fusion cannot convert a candidate finding into accepted truth.

## Relationship to future implementation agents

Implementation agents may later be introduced as a separate actor class with edit
and execution permissions. They must receive only validated accepted issues or
explicitly human-approved work items as mandatory changes.

They must not treat unvalidated reviewer findings as implementation requirements.

## Tool-enabled review exceptions

Review agents are read-only by default. If a workflow needs a tool-enabled review,
the permission must be explicit in one of these places:

- the workflow review configuration;
- the reviewer manifest;
- the reviewer prompt.

The permission must state the tool, purpose, scope, and whether it can read or
write. Write access is not allowed for review agents in the current core model.

Tool observations made by a reviewer remain candidate findings. They do not become
authoritative verification evidence unless a verification gate reproduces or
accepts the evidence through its own gate report.

## Fusion boundary

Fusion does not launch reviewers or verification gates by default. Fusion may
recommend another review pass or additional verification as a decision-support
item. The main/orchestrating agent decides whether to invoke another review cycle
according to the workflow's review-cycle policy.
