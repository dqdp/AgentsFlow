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
      bugfix-regression-capture.binding.yaml
      review-only-fusion.binding.yaml
      new-project-spec-first.binding.yaml

    gates/                        # project-bound executable gate manifests
      plan_gate.yaml
      verification_gate.yaml
      regression_gate.yaml
      evidence_gate.yaml
      spec_review_gate.yaml

    scripts/                      # project-specific deterministic runners/checks
      run_plan_gate.sh
      run_verification_gate.sh
      run_regression_gate.sh
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

Frequent. A feature, bugfix, review, or project specification task creates a run directory under `Docs/agentsflow/runs/`.

## Operational rules

```text
1. Upstream is immutable during normal feature/bugfix/review workflows.
2. Project-specific commands and tools live in the project overlay, not upstream.
3. Task-specific contracts, plans, reports and evidence live in workflow run directories.
4. Long-lived accepted decisions are promoted to normal project docs/ADRs.
5. No silent upstream drift: every project records the pinned AgentsFlow version/commit.
```

## Relationship to project binding

The project overlay binds universal AgentsFlow workflows and gate contracts to a
concrete repository. `.agentsflow/project.yaml` uses the flat canonical manifest
shape from `docs/project-binding-model.md`; upstream source/pinning details live
in `.agentsflow/agentsflow.lock.yaml`.

See `docs/project-binding-model.md`.
