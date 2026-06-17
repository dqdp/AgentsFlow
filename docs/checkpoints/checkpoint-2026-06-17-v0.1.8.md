# Checkpoint: AgentsFlow v0.1.8

## Newly accepted decisions

### Behavior Binding Rule

BDD/Gherkin scenarios are behavior specifications, not executable gates. Required
acceptance scenarios must be bound to executable checks through `*.bindings.yaml`.
Gate runners consume binding manifests and report execution/evidence.

### MVP-ready workflow standard

AgentsFlow v0.2 MVP focuses on four workflows:

```text
big-feature-contract-first
bugfix-regression-capture
review-only-fusion
new-project-spec-first
```

MVP-ready workflows must have validated manifests, explicit phases, gate
contracts, project-binding requirements, required templates, review policy where
applicable, behavior bindings where required, and validation coverage.

### Project Binding / Overlay Model

AgentsFlow upstream defines universal workflow/gate contracts and generic
validators. Project overlays bind upstream workflow requirements to concrete
repository paths, commands, deterministic runners, instruments and evidence
sources. Workflow runs contain task-specific artifacts and evidence.

### Gate contract vs project-bound executable gate

The Gate Executability Rule is refined:

```text
A gate is not executable for a real workflow run until it is bound to a deterministic project-level runner.
```

Upstream gate manifests are gate contracts/templates. Project overlays provide
project-bound executable gates.

## Updated repository areas

- `docs/behavior-binding-model.md`
- `docs/mvp-ready-workflow-standard.md`
- `docs/project-binding-model.md`
- `docs/gate-executability-model.md`
- `docs/adr/ADR-0011-behavior-binding-rule.md`
- `docs/adr/ADR-0012-project-bound-executable-gates.md`
- `templates/behavior-bindings.yaml`
- `templates/project.yaml`
- `templates/workflow.binding.yaml`
- `schemas/behavior-binding.schema.json`
- `schemas/project-binding.schema.json`
- `schemas/workflow-binding.schema.json`
- `scripts/bdd_binding_check.py`
- `scripts/validate_project_binding.py`
- `examples/project-overlay/`

## Remaining open questions

- Exact v0.2 shape of the four MVP workflows.
- How much native Spec/Plan functionality belongs in v0.2 vs later.
- Concrete packaging for Codex/Claude Code/OpenCode/Cline usage.
- Whether to add a thin CLI facade or keep scripts as separate entrypoints.
- Multi-model diversity policy for review/fusion execution.
