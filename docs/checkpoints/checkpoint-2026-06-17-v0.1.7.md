# Checkpoint: AgentsFlow v0.1.7

Date: 2026-06-17

## New accepted decision

### Gate Executability Rule

Every concrete gate included in an AgentsFlow workflow must have a deterministic
runner entrypoint.

BDD scenarios, contracts and prose specifications can define what should be
checked, but they are not executable gates by themselves.

## Repository changes

Added:

- `docs/gate-executability-model.md`
- `docs/adr/ADR-0010-gate-executability-rule.md`
- `gates/*.yaml`
- `scripts/gates/run_gate.py`
- `scripts/gates/run_<gate-id>.py` wrappers

Updated:

- `schemas/gate.schema.json`
- `schemas/workflow.schema.json`
- `schemas/workflow-phase.schema.json`
- `scripts/validate_repo.py`
- workflow manifests with concrete gate references where applicable

## Core rule

```text
Every gate must be executable.
Not every gate must be fully automatable.
```

If a gate requires manual evidence, the runner returns `needs_human_decision`
rather than allowing a model to mark the gate as passed.

## Remaining open questions

- BDD binding format and scenario coverage validation.
- MVP cut for v0.2.
- Multi-model fusion policy details.
- Whether to promote gate runners from skeleton wrappers to real orchestrators in v0.2.
