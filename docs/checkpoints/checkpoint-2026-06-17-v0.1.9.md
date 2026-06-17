# Checkpoint: AgentsFlow v0.1.9

## Accepted decisions added in this checkpoint

### Project application / pinning

AgentsFlow is applied to a project as a pinned upstream dependency plus a project-specific overlay.

First-stage supported dependency modes:

```text
- Git submodule
- CMake FetchContent / FetchPackage-style dependency
```

CLI/package distribution is deferred.

### Project initialization / onboarding

AgentsFlow requires a dedicated initialization workflow for concrete projects.

Initialization starts with a project intake / research assignment. The assignment may be open-ended for unknown project discovery or directed by known human goals.

Initialization must analyze code, tests, documentation, ADRs, agent instructions, process artifacts and implementation history recorded in Markdown files.

### Inventory model

Project initialization separates:

```text
machine-observed raw facts
model-produced structured inventory
expert assessments
human-confirmed decisions
```

Model-produced fields must include provenance, confidence and human-confirmation markers when appropriate.

### Researcher/expert agents

Researcher/expert agents receive the project intake assignment and produce candidate findings/recommendations, not authoritative truth.

## New files

- `docs/project-application-model.md`
- `docs/project-initialization-model.md`
- `docs/adr/ADR-0013-agentsflow-project-application-model.md`
- `docs/adr/ADR-0014-project-initialization-and-research-assignment.md`
- `workflows/project-initialization/`
- `templates/agentsflow.lock.yaml`
- `templates/project-intake.yaml`
- `templates/project-raw-scan.json`
- `templates/project-inventory.json`
- `templates/project-assessment.json`
- `templates/initialization-report.md`
- `templates/workflow-run.yaml`
- `schemas/project-intake.schema.json`
- `schemas/project-raw-scan.schema.json`
- `schemas/project-inventory.schema.json`
- `schemas/project-assessment.schema.json`
- `schemas/workflow-run.schema.json`
- `scripts/project_raw_scan.py`
- `scripts/validate_project_intake.py`
- `scripts/validate_project_inventory.py`
- `examples/project-initialization/`
