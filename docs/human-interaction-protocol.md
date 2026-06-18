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
      allowed: true
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
```

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
legacy_adoption_mode_decision
operating_decisions_interview
human_approval
```

Only `operating_decisions_interview` and `human_approval` are always human-owned
decision points for normal existing-project onboarding. `read_project_intake` and
`legacy_adoption_mode_decision` are conditional: they pause when required context
is missing or when legacy agent/process artifacts create human-owned decisions.

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
