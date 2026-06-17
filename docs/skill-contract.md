# Skill Contract

A skill is a reusable agent capability.

Each skill has two files:

```text
skills/<skill-name>/
  SKILL.md    # human/agent-readable procedure
  skill.yaml  # machine-readable interface
```

## `SKILL.md`

`SKILL.md` should describe:

- purpose;
- when to use;
- required inputs;
- expected outputs;
- step-by-step procedure;
- quality bar;
- anti-patterns;
- handoff to other skills/scripts.

## `skill.yaml`

`skill.yaml` should describe the interface:

```yaml
name: bdd-scenario-design
type: skill
version: 0.1
inputs:
  - intent
  - existing_contract
  - domain_pack
outputs:
  - behavioral_scenarios
  - forbidden_behavior
  - ambiguity_notes
depends_on:
  - contract-authoring
compatible_workflows:
  - new-project-spec-first
```

## Design principles

- Skills should be small enough to reuse.
- Skills should not run deterministic checks directly; they should delegate to scripts.
- Skills should produce artifacts that can be reviewed.
- Skills should state uncertainty instead of hiding it.
- Skills should not duplicate large parts of workflows.

## Skill categories

| Category | Examples |
|---|---|
| Specification | problem framing, contract authoring, BDD scenario design |
| Verification | impact map builder, evidence reporting |
| Review | architecture reviewer, verification reviewer, adversarial reviewer |
| Synthesis | fusion synthesis, ADR drafting |
| Regression | regression capture, failure pattern extraction |
