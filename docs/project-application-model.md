# AgentsFlow Project Application Model

## Status

Accepted in v0.1.9.

## Purpose

This document defines how AgentsFlow is applied to a concrete software project without mixing three different concerns:

```text
AgentsFlow upstream      — pinned workflow kit and reference methodology
Project overlay/binding  — project-specific configuration and execution mapping
Workflow run             — task-specific artifacts, evidence and decisions
```

The goal is to prevent AgentsFlow usage from becoming an unstructured folder of prompts, scripts, evidence and project-specific conventions.

## Installation and pinning policy

For the first stage, AgentsFlow supports only:

```text
1. Git submodule
2. CMake FetchContent / FetchPackage-style dependency
```

CLI/package distribution is explicitly deferred.

## Recommended layout

```text
my-project/
  AGENTS.md

  .agentsflow/
    agentsflow.lock.yaml          # pinned upstream version/commit/source
    project.yaml                  # project-level AgentsFlow config
    project-operating-decisions.yaml # human-owned gate/review/evidence decisions from agent-led interview
    upstream/                     # pinned AgentsFlow dependency; read-only during normal work

    workflows/                    # project bindings for upstream workflows
      big-feature-contract-first.binding.yaml

    gates/                        # project-bound executable gate manifests
      plan_gate.yaml
      verification_gate.yaml

    scripts/                      # project-specific deterministic runners/checks
      run_plan_gate.sh
      run_verification_gate.sh
      collect_evidence.sh
      check_boundaries.py

    profiles/
      default.yaml
      high-risk.yaml

    packs/
      project-pack.md

  Docs/
    adr/
    agentsflow/
      runs/                       # concrete workflow runs
```

## Three modification classes

### A. AgentsFlow upstream upgrade

Rare. Updating `.agentsflow/upstream` or `agentsflow.lock.yaml` is a process change and should go through a review workflow.

### B. Project overlay change

Medium frequency. Examples: adding a new static analyzer, changing the verification gate, changing review topology, or changing evidence storage.

Changes to `project-operating-decisions.yaml` are policy changes, not ordinary run
artifacts. They should be made through the same agent-led decision interview
style used during initialization: the agent asks focused questions, summarizes
the decision, records provenance/status, and then updates the structured
artifact.

### C. Workflow run

Frequent. A feature, bugfix, review, or project specification task creates a
run directory under `Docs/agentsflow/runs/` in ordinary target projects.

When AgentsFlow applies itself to this repository, self-application run history
uses `run-artifacts/agentsflow/runs/` instead. The repository's lowercase
`docs/` directory is methodology source; using `run-artifacts/` avoids ambiguity
and case-insensitive filesystem collisions with project-style `Docs/` history.

Workflow-run human interaction uses `human-questions.yaml` and
`human-decisions.yaml` as run artifacts. They are not long-lived policy files by
themselves. Long-lived operating policy is normalized into
`.agentsflow/project-operating-decisions.yaml` only when the workflow or project
policy says the decision should persist beyond the current run.

For `prepare-workflow` initialization, the project does not have to prove that a
full onboarding workflow already ran. It must provide enough operating context
for the target workflow: project or draft binding, verification gate policy,
review policy, evidence/run artifact location and any human-owned authority
decisions that affect the workflow. If preparation reveals a material design
fork that affects scope, ADR alignment, risk posture, contracts, gates, review,
evidence, authority or workflow-design, the run records it as a human-mediated
target-workflow decision checkpoint before the binding/readiness artifacts are
treated as ready.

## Operational rules

```text
1. Upstream is immutable during normal feature/bugfix/review workflows.
2. Project-specific commands and tools live in the project overlay, not upstream.
3. Task-specific contracts, plans, reports and evidence live in workflow run directories.
4. Long-lived accepted decisions are promoted to normal project docs/ADRs.
5. Draft overlays and active-instruction maps are not active policy until human approval.
6. No silent upstream drift: every project records the pinned AgentsFlow version/commit.
```

## Relationship to project binding

The project overlay binds universal AgentsFlow workflows and gate contracts to a
concrete repository. `.agentsflow/project.yaml` uses the flat canonical manifest
shape from `docs/project-binding-model.md`; upstream source/pinning details live
in `.agentsflow/agentsflow.lock.yaml`.

See `docs/project-binding-model.md`.
