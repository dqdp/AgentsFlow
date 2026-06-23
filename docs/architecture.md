# Architecture

## Layers

```text
┌───────────────────────────────────────────┐
│ Workflows                                 │
│ new-project, big-feature, hardening, etc. │
└───────────────────────────────────────────┘
                     │ compose
┌───────────────────────────────────────────┐
│ Skills                                    │
│ reasoning/procedure capabilities          │
└───────────────────────────────────────────┘
                     │ call/check
┌───────────────────────────────────────────┐
│ Scripts                                   │
│ deterministic automation and gates         │
└───────────────────────────────────────────┘
                     │ format
┌───────────────────────────────────────────┐
│ Templates / Schemas                        │
│ artifact shapes and manifest validation    │
└───────────────────────────────────────────┘
                     │ parameterize
┌───────────────────────────────────────────┐
│ Domain Packs / Profiles                    │
│ domain rules, default/effective strictness │
│ and review topology                        │
└───────────────────────────────────────────┘
```

## Data flow

```text
User intent
  ↓
Workflow selection
  ↓
Domain pack + workflow default strictness + review topology
  ↓
Contract/specification authoring
  ↓
BDD scenarios and boundaries
  ↓
Impact map and verification binding
  ↓
Red capture for implementation work (tests run against the unimplemented state, failing run captured — ADR-0017)
  ↓
Implementation or review
  ↓
Verification gate
  - runs declared verification instruments through deterministic runner entrypoints
  - produces evidence bundle and gate report
  ↓
Read-only review agents
  - inspect verification artifacts
  - do not run tests or modify files
  - produce candidate findings, not truth
  ↓
Fusion synthesis
  - preserves candidate blockers and disagreements
  ↓
Main-agent relevance validation
  - accepts/rejects/escalates findings with reasons
  ↓
Acceptance proof
```

## Artifact types

| Artifact | Purpose | Typical location |
|---|---|---|
| Workflow manifest | Declares orchestration recipe | `workflows/<name>/workflow.yaml` |
| Skill instruction | Tells agent how to perform capability | `skills/<name>/SKILL.md` |
| Skill manifest | Machine-readable skill interface | `skills/<name>/skill.yaml` |
| Script contract | Machine-readable script interface | `scripts/contracts/<name>.yaml` |
| Task contract | Contract for a concrete task/feature | target project `Docs/contracts/*.contract.md` |
| Gate manifest | Declares executable gate and runner | `gates/<gate-id>.yaml` |
| Evidence report | Completion proof | target project or task artifact |
| Domain pack | Domain rules | `packs/<domain>/PACK.md` |
| Default strictness | Workflow-owned baseline gate depth | `workflows/<name>/workflow.yaml` |
| Strictness override | Explicit project/run deviation from the workflow default | `.agentsflow/workflows/*.binding.yaml`, workflow run metadata |

## Design boundaries

- Workflows orchestrate; they do not contain all skill logic.
- Skills reason; they do not perform deterministic filesystem checks.
- Scripts check; they do not make model-judgment decisions.
- Verification gates run declared instruments through deterministic runner entrypoints and produce evidence bundles/reports.
- Reviewers inspect gate artifacts; they do not run tests, call scripts, or modify source artifacts.
- Fusion synthesizes; it does not erase blocking issues by majority vote.
- An implementation phase must be framed by red-capture and green-verify phases, so the red→green pair becomes gate evidence by construction (ADR-0017; workflow-topology enforcement is in `validate_repo.py`; run-artifact evidence-pair validation remains future work).
