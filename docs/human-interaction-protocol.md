# Human Interaction Protocol

## Status

Accepted for v0.2.

## Purpose

AgentsFlow workflows may require human decisions. In v0.2 this is not a runtime
or UI feature. It is a workflow protocol for the main/orchestrating agent.

The human explicitly starts a workflow. The main/orchestrating agent drives the
workflow phases, performs normal repository work, and may pause only at declared
human decision points or blocking clarifications.

## Core rule

```text
Human interaction is mediated by the main/orchestrating agent.
Review agents do not ask the human questions directly.
```

## Human-mediated gates

A `human_mediated_gate` is a workflow control point where the human makes or
confirms the exit decision after the main/orchestrating agent has synthesized the
relevant evidence, reviewer outputs, options and consequences.

It is different from:

```text
deterministic_gate
  A runner evaluates declared checks/evidence and emits a gate report.

review_gate
  Review agents emit candidate findings and the main agent validates relevance.
```

The human does not manually fill YAML. The main/orchestrating agent asks the
decision question in dialogue, then records the normalized result in
`human-decisions.yaml` and updates affected artifacts.

For example, a pre-red-capture plan decision may be modeled as:

```text
technical_plan -> deterministic plan_gate -> plan review reports
-> main-agent synthesis -> human_mediated_gate decision -> red_capture
```

The exact phase shape must be declared by the workflow or project binding. A
phase-transition checker must not infer this gate from conversation alone.

Review agents may produce:

```text
- candidate findings;
- risks;
- recommended gates;
- decision options;
- questions_for_human.
```

The main/orchestrating agent synthesizes those inputs into a decision prompt,
asks the human, records the answer, and resumes the workflow.

## Workflow states

Use these run states for human interaction:

```text
running
paused_waiting_for_human
resumed
completed
blocked
```

`paused_waiting_for_human` means the workflow is intentionally stopped at a
declared decision point. The agent must not silently choose a confirmed human
answer while paused.

## When the agent may ask

The main/orchestrating agent may ask the human only when:

```text
- required intake is missing or the invocation mode is unclear;
- analysis is blocked by missing human-owned context;
- a declared human-owned decision is required;
- a material design fork affects scope, ADR alignment, risk posture, contract,
  gate, review, evidence, authority or workflow-design for the active workflow;
- final approval is required.
```

Otherwise the agent should continue autonomously: read files, run allowed
scripts, structure inventory, launch read-only review agents, draft artifacts and
run validators.

## Question artifact

Questions are recorded in `human-questions.yaml` under the workflow run directory.
Each question is a decision prompt, not a request to fill YAML.

Required shape:

```yaml
version: 1
run_id: "YYYY-MM-DD-task-slug"
questions:
  - decision_id: review_policy.model_diversity
    phase_id: operating_decisions_interview
    status: open
    classification: blocking-material
    grouping: operating-decisions
    question: Should review use different models or harnesses when available?
    basis:
      observed:
        - Existing project has no external reviewer policy.
      reviewer_recommendations:
        - Verification reviewer recommends independent review for high-risk work.
    options:
      - id: same-model
        label: Same model is allowed
        impact: Lower setup complexity.
      - id: diverse-models
        label: Prefer different model/harness
        impact: More independence; requires provider setup.
      - id: unresolved
        label: Leave unresolved
        impact: Overlay remains draft-only.
    default:
      id: same-model
      allowed: false
    answer_required: true
    affected_artifacts:
      - project-operating-decisions.yaml
      - .agentsflow/project.yaml
```

## Decision artifact

Human answers are recorded in `human-decisions.yaml` under the workflow run
directory.

Required shape:

```yaml
version: 1
run_id: "YYYY-MM-DD-task-slug"
decisions:
  - decision_id: review_policy.model_diversity
    phase_id: operating_decisions_interview
    question_ref: review_policy.model_diversity
    answer: diverse-models
    status: confirmed
    answered_by: human
    classification: blocking-material
    rationale: "Use model diversity for high-risk reviews."
    affected_artifacts:
      - project-operating-decisions.yaml
```

Allowed decision statuses:

```text
confirmed
defaulted
unresolved
rejected
superseded
explicitly_deferred_with_constraints
```

`explicitly_deferred_with_constraints` requires a `deferral_constraints` object
with at least one stated constraint. It is the only allowed resume path for a
blocking-material decision that is intentionally deferred instead of resolved.

## Resume rule

After the human answers, the main/orchestrating agent:

```text
1. records the answer in `human-decisions.yaml`;
2. updates the target normalized artifact, if applicable;
3. marks unresolved items explicitly when the answer is incomplete;
4. resumes from the paused phase;
5. does not re-run earlier phases unless the answer invalidates their inputs.
```

## Project initialization

`project-initialization` declares these human-pause phases:

```text
read_project_intake
documentation_disposition_decision
legacy_adoption_mode_decision
operating_decisions_interview
target_workflow_context_decision_packet
human_approval
```

Only `operating_decisions_interview` and `human_approval` are always human-owned
decision points for normal existing-project onboarding. `read_project_intake` and
`legacy_adoption_mode_decision` are conditional: they pause when required context
is missing or when legacy agent/process artifacts create human-owned decisions.
`documentation_disposition_decision` is conditional for existing-project modes:
it classifies current documentation and Markdown implementation history before
legacy adoption, target-workflow readiness, or overlay drafting. It must not
delete, rewrite or silently de-authorize existing documentation without explicit
human approval. It must also ask the human to choose the documentation legacy
adoption mode. The agent may recommend `preserve-as-is`,
`knowledge-extraction`, `rewrite-migration` or `archive-delete`, but it must not
select the mode without human confirmation; this decision is not defaultable by
the agent. If the human accepts the agent's recommendation, the workflow records
that as an answered human decision. When `knowledge-extraction` is selected, the
agent must also record the human-confirmed extraction depth as `light`,
`standard` or `deep`.
`target_workflow_context_decision_packet` is conditional for `prepare-workflow`:
it captures missing target-workflow gate, review, evidence or authority context,
plus material scope, ADR, risk, contract, gate, review, evidence, authority or
workflow-design forks discovered during target-workflow preparation, as a
run-level decision packet. It does not normalize those answers into
`project-operating-decisions.yaml` unless the human explicitly chooses onboarding
or persistent policy activation.

### Human-mediated design decision checkpoints

A material design fork is a human-mediated checkpoint, not an informal side
conversation and not a review-agent gate. The main/orchestrating agent pauses,
groups the decision options, records questions in `human-questions.yaml`, records
answers in `human-decisions.yaml`, updates the affected run artifacts, and then
resumes the workflow.

The checkpoint may exit only when:

```text
- blocking-material decisions are confirmed or explicitly deferred with stated constraints;
- decision packet and preflight run artifacts are updated;
- unresolved nonblocking questions are recorded as defaults, limitations or follow-ups;
- no unresolved design decision blocks the next workflow gate.
```

Target workflow binding/readiness handoff artifacts are drafted only after
`target_workflow_readiness_gate` accepts the operating context.

## Big-feature contract-first

`big-feature-contract-first` may pause for the human only when the main agent
records one of these conditions:

```text
unresolved blocking-material question
material design fork affecting scope, ADR alignment, risk posture, contract,
gate, review, evidence or authority
scope or task-contract amendment
accepted decision or ADR conflict
exhausted review cycles
final human acceptance required by project policy
```

Open questions in `task.contract.md` are classified as:

```text
blocking-material
nonblocking-follow-up
nonblocking-known-limitation
out-of-scope
```

Only `blocking-material` questions pause the workflow by default. Nonblocking
questions must show the proposed default or follow-up handling in the grouped
decision packet, and unanswered nonblocking questions are recorded as defaulted,
known limitations or follow-ups rather than silently disappearing.

The grouped decision packet is still a dialogue with the agent, not a request for
the human to edit YAML. The main agent asks the grouped questions, records
answers in `human-decisions.yaml`, updates the task contract or run artifacts,
and resumes from the paused phase.

## Non-goals

This protocol does not introduce:

```text
- a UI;
- a database;
- a long-running service;
- automatic reminders;
- autonomous monitoring;
- review-agent-to-human conversations.
```
