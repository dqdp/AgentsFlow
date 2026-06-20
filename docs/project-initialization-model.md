# Project Initialization / Onboarding Model

## Status

Accepted in v0.1.9, refined in v0.1.10, and extended in v0.2 with a
conversational human operating-decisions interview.

## Purpose

Project initialization is a mode-gated application workflow for understanding a
project, onboarding it, preparing one target workflow, cleaning up legacy agent
instructions, or assessing domain risk. It must not assume that the agent already
understands the project. It creates or activates project overlay artifacts only
in intent modes that require binding or policy activation.

Initialization separates:

```text
machine-observed facts
model-produced structured inventory
expert assessments
human operating decisions
human-confirmed decisions
```

## Core rules

```text
No project analysis without an explicit research assignment.
Unknown project does not mean empty assignment.
No inferred metadata without provenance and confidence.
No domain assumption without evidence and confirmation status.
No persistent project-bound gate or review policy activation before the human
operating decisions interview.
No project overlay without human approval.
No `prepare-workflow` initialization without a declared target workflow.
No code-only scan when documentation/history exist.
No review-agent-to-human questioning; human interaction is mediated by the main agent.
```

`prepare-workflow` may use existing project policy/workflow binding evidence, or
record missing target-workflow gate/review/evidence/authority context and
material target-workflow design decisions in the run-level
`target_workflow_context_decision_packet`. That packet is not a substitute for
persistent `project-operating-decisions.yaml` unless the human explicitly chooses
onboarding or policy activation.

## Input artifact: project intake / research assignment

Initialization starts with an explicit assignment, stored as `project-intake.yaml` or `project-intake.md`.

The assignment may be:

```text
standard exploratory
  Used for unknown-project discovery. This is not empty: it uses the standard research assignment template and gives the user a chance to provide context before scanning.

directed
  Used when the human knows project goals, intended direction, fixed decisions, or preferred AgentsFlow workflows.

problem-driven / migration-driven / risk-driven
  Used when initialization has a narrower purpose.
```

The canonical standard exploratory template is:

```text
templates/research-assignment.unknown-project.md
```

The assignment is passed to researcher agents and expert assessment agents. It gives them context, known goals, constraints, domain assumptions, and analysis focus.

Every initialization run must record an `intent_mode`. When `intent_mode` is
`prepare-workflow`, the intake must also record `target_workflow` so that the
agent can bind the scan, assessment and human decision prompts to the concrete
workflow being prepared.

The project intake is not the same thing as project operating decisions. Intake
answers what should be studied and why. Operating decisions answer how AgentsFlow
should run in the concrete project after the inventory and candidate assessment
exist.

## Preflight user opportunity

Even in unknown-project discovery, the user must have a chance to provide context. The initialization workflow should ask, or record that it asked, questions such as:

```text
- What do you want to understand or improve in this project?
- Is this your project or an external/unknown project?
- Is there a known direction of development, migration, refactor, or process improvement?
- Are there known constraints, accepted decisions, risks, or non-goals?
- Are there domain-specific concerns that may not be fully documented in the repository?
```

If the user provides no additional context, the workflow proceeds with the standard exploratory assignment.

## Required analysis scope

Initialization must analyze more than code when those artifacts exist:

```text
- source code and tests;
- build/package/config files;
- README and project documentation;
- ADRs and architecture notes;
- AGENTS.md / CLAUDE.md / Cursor rules / Codex instructions;
- implementation history recorded in Markdown files;
- migration notes, runbooks, changelogs, postmortems, task reports;
- CI, scripts and existing process artifacts;
- domain-specific docs, protocols, APIs and operational rules.
```

Implementation history in Markdown is especially important because agentic projects often store real decisions, constraints, unfinished migrations and known problems in planning or task-report documents.

## Domain identification and domain expertise

Project initialization must explicitly identify the apparent project domain or domains.

For every domain classification, the inventory must separate:

```text
observed evidence
model inference
confidence
requires_human_confirmation
```

Domain identification is model-inferred unless directly stated by the user or by project documentation. It must not be treated as authoritative until confirmed when it affects workflow bindings, gates, domain packs, review roles, or accepted decisions.

Initialization must ask or record domain-expertise questions for the user:

```text
- What domain is this project in?
- Are you a domain expert for this project?
- Should your domain knowledge be treated as authoritative for initialization decisions?
- Are there domain-specific constraints, regulations, safety concerns, latency requirements, financial risks, privacy requirements, operational rules, or compliance obligations that the repository may not fully document?
- Are there domain terms, abbreviations, protocols, exchanges, APIs, devices, business rules, or workflows that the agent must not reinterpret without confirmation?
- Should AgentsFlow use an existing domain pack for this project or create a project-specific domain pack?
- Are there accepted domain decisions that should be treated as fixed constraints?
```

## Intent modes

Initialization uses an explicit intent mode rather than relying on one implicit
onboarding path.

| Intent mode | Purpose | Required target workflow? | Output rule |
|---|---|---:|---|
| `unknown-discovery` | Understand an unknown or weakly understood project. | no | Raw scan, inventory, domain questions, triad assessment and operating-decision questions. |
| `adoption-onboarding` | Prepare an existing project to use AgentsFlow generally. | no | Draft overlay, operating decisions, legacy adoption decision and active instruction map. |
| `prepare-workflow` | Prepare one concrete AgentsFlow workflow for a project that may already be partly initialized or may have used AgentsFlow from the start. | yes | Workflow binding draft, gate/evidence readiness, task preflight findings and missing decision packet for the target workflow. |
| `legacy-cleanup` | Resolve existing agent/process instruction conflicts before normal workflow use. | no | Legacy inventory, adoption decision, migration/quarantine plan and draft active instruction map. |
| `risk-domain-assessment` | Deepen domain, compliance, safety or operational risk understanding before choosing gates/review topology. | optional | Domain/risk assessment, human domain-expertise questions and gate/review recommendations. |

`unknown-discovery` is not an empty assignment. It uses the standard exploratory
research assignment and emphasizes observed facts, inferred judgments, domain
assumptions, unknowns, and questions for humans.

`adoption-onboarding` is used when the project owner provides known goals and
intended direction. The analysis must take those inputs into account; for
example, assessing readiness for specific AgentsFlow workflows or gate policies.

`prepare-workflow` does not require that the repository previously completed a
full project-initialization run. It requires enough project context for the
target workflow to execute safely: project binding or draft binding, gate policy,
review policy, evidence location and any human-owned decisions that affect the
target workflow.

## Data layers

### Layer 1: raw scan

A generic scanner collects observable repository facts where possible:

```text
file tree, config files, candidate build systems, CI files, docs roots, source/test roots, scripts, AGENTS.md-like files, git status.
```

Output: `project-raw-scan.json`.

### Layer 2: structured inventory

The main/orchestrating agent uses raw scan evidence plus selected project documents to fill `project-inventory.json` according to schema.

The format is deterministic. The truth of some fields may still be model-inferred.

Every non-trivial field should include:

```text
source_type
provenance/evidence
confidence
requires_human_confirmation
```

Domain-related fields must additionally separate observed evidence from domain assumptions.

### Layer 3: expert assessment

Read-only expert agents produce candidate assessments. The default v0.2
assessment shape is a triad:

```text
architecture assessment
verification assessment
adversarial assessment
synthesis assessment
```

Role reports are phase-boundary artifacts, so they must be returned as strict
JSON conforming to `schemas/project-assessment.schema.json`. Markdown or
prose-only assessment output is invalid workflow evidence: the main agent must
reject it and rerun or pause instead of silently normalizing it as authoritative.
Synthesis is allowed only after all required role reports validate against the
schema and the synthesis artifact records that validation.

For prompt-sensitive target workflows, initialization may add a
`prompt_engineering` role report. This is additive; the architecture,
verification and adversarial triad remains required.

The role reports may overlap. They produce candidate workflow/gate/risk
recommendations, open questions and human-decision items. Their findings are
candidate findings and follow the review-finding validation model.

### Layer 4: documentation disposition

For existing projects, initialization must classify the current documentation
corpus after structured inventory and expert assessment exist, and before
drafting overlays, preparing a target workflow, or resolving legacy agent/process
artifacts.

This is broader than legacy agent-system adoption. It covers README files,
architecture notes, ADRs, runbooks, implementation history, process documents and
domain documentation, not only agent instructions.

Output: `project-documentation-disposition.yaml`.

Each material document or document group is classified as one of:

```text
keep-authoritative
keep-evidence
extract-and-normalize
mark-stale-or-superseded
needs-human-decision
rewrite-or-delete-after-approval
```

The default is conservative: unclassified documents require a human decision or
remain evidence-only. Initialization must not delete, rewrite or silently
de-authorize existing project documentation without explicit human approval.

For `prepare-workflow`, this artifact is run-level context. It tells the target
workflow which documents may be treated as authority, evidence, normalized input
or unresolved context, without promoting those decisions into long-lived project
policy unless the human explicitly chooses onboarding or policy activation.

### Layer 5: human operating-decisions interview

After the structured inventory and expert assessment exist, the main/orchestrating
agent conducts a dialogue with the human project owner. This is not a request for
the human to manually fill a YAML or JSON file.

The dialogue decides:

```text
- default workflows and strictness override policy;
- verification gate blockers and advisory checks;
- canonical test/lint/typecheck/security/performance/domain commands;
- required evidence for gate acceptance;
- whether red-before/green-after evidence is mandatory for implementation workflows;
- reviewer count and reviewer roles;
- whether different models or harnesses should be used for review;
- whether external reviewers are allowed and what context they may receive;
- maximum review cycles and escalation conditions;
- who may approve scope changes, gate changes, topology changes, legacy migration or residual risk;
- where run artifacts and evidence live;
- whether reports/raw logs are committed, gitignored, redacted or omitted.
```

The agent must ask focused questions, offer conservative defaults when supported
by evidence, and summarize decisions back to the human. For
`adoption-onboarding` or explicit persistent policy activation, the normalized
result is `project-operating-decisions.yaml`. For `prepare-workflow`, missing
target-workflow operating context and material scope, ADR, risk, contract, gate,
review, evidence, authority or workflow-design decisions are recorded in the run-level
`target_workflow_context_decision_packet` unless the human explicitly switches to
onboarding or persistent policy activation.

For `prepare-workflow`, a material design decision is any human-owned choice that
can change the target workflow binding, gate set, evidence policy, authority
model, task contract or downstream implementation scope. It is a declared
human-mediated checkpoint: the main/orchestrating agent groups options, pauses
for the human answer, records the answer in the decision packet and preflight run
artifacts, and resumes only when blocking-material decisions are confirmed or
explicitly deferred with stated constraints and no unresolved decision blocks the
next gate. Target workflow binding/readiness handoff artifacts are drafted only
after `target_workflow_readiness_gate` accepts the operating context.

Each material decision is marked as one of:

```text
confirmed
defaulted
unresolved
rejected
explicitly_deferred_with_constraints
```

Unresolved decisions remain visible and must not silently become project defaults.
Blocking-material target-workflow decisions may be deferred only with stated
constraints; bare unresolved blocking decisions block readiness.

### Layer 6: human confirmation

The human approves or corrects the project overlay, disputed inventory fields,
domain assumptions, workflow selection, gate strategy and operating decisions.

## Initialization workflow

The shared backbone is:

```text
1. Read project intake / research assignment.
2. Ask or record preflight user context/domain-expertise questions.
3. Attach or verify pinned AgentsFlow upstream when the run will produce overlay
   or workflow-binding artifacts.
4. Run raw project scan.
5. Discover documentation and implementation history.
6. Produce structured project inventory, including domain identification.
7. Run schema-bound triad expert assessments and synthesize candidate
   recommendations only after all required role reports validate.
8. For existing-project modes, record project documentation disposition before
   legacy adoption, target-workflow readiness or overlay drafting.
```

The remaining steps are mode-gated:

```text
unknown-discovery
  Stop after inventory, assessment and human questions unless the human asks to
  continue into onboarding.

adoption-onboarding
  Record `project-documentation-disposition.yaml`, then resolve legacy adoption
  when legacy artifacts are in scope.
  Conduct the human operating-decisions interview, normalize
  `project-operating-decisions.yaml`, draft overlay/gates as draft artifacts,
  validate them, produce initialization report and wait for human approval.

prepare-workflow
  Confirm `target_workflow`, record run-level `project-documentation-disposition.yaml`
  with a human-confirmed documentation legacy adoption mode,
  check whether sufficient gate/review/evidence and authority context exists,
  capture missing context or material design forks in a run-level target workflow
  human decision packet and ask grouped human questions for missing material
  context, block readiness on unresolved blocking-material forks, run
  `target_workflow_readiness_gate`, then draft only target-workflow
  binding/readiness handoff artifacts when ready.

legacy-cleanup
  Record `project-documentation-disposition.yaml` with a human-confirmed
  documentation legacy adoption mode, select legacy agent-system adoption mode,
  draft migration/quarantine and
  `active-instruction-map.yaml`, then wait for human approval before activation.

risk-domain-assessment
  Stop after domain/risk assessment and human domain-expertise questions unless
  the human asks to continue into onboarding or prepare-workflow.
```

## Human interaction protocol

Project initialization uses the human interaction protocol in
`docs/human-interaction-protocol.md`.

The main/orchestrating agent is the workflow driver after explicit human
invocation. It may pause the run only at declared human decision points or when
analysis is blocked by missing human-owned context.

Declared human-pause phases:

```text
read_project_intake
documentation_disposition_decision
legacy_adoption_mode_decision
operating_decisions_interview
target_workflow_context_decision_packet
human_approval
```

Review agents do not ask the human questions directly. They produce candidate
findings, risks, recommendations and `questions_for_human`; the main agent
synthesizes those into decision prompts.

Questions are stored in `human-questions.yaml`; answers are stored in
`human-decisions.yaml`. Long-lived operating choices are then normalized into
`project-operating-decisions.yaml`.

## Modes of operation

```text
scan-only
  Produce raw scan, inventory, assessment and questions. Do not create overlay files.

draft-overlay
  Create draft `.agentsflow/` overlay files for human review. This is used by
  onboarding and activation paths, not by discovery-only or risk-only exits.

apply-approved
  Apply approved overlay after human confirmation.
```

Default unknown/risk discovery stops at scan, inventory, assessment and
questions. `draft-overlay` is a continuation for adoption-onboarding,
legacy-cleanup activation, or prepare-workflow binding/policy activation.

Before human approval, generated overlay files are draft-only. The agent may
write normalized draft artifacts for review, but must not treat them as active
project policy, rewrite `AGENTS.md`, activate a migration, or replace existing
instructions without explicit approval.


## Legacy agent-system adoption

Existing projects may already contain agent instructions, skills, prompts,
workflow docs and process artifacts. Initialization must not simply add
AgentsFlow on top of them.

Legacy adoption consumes `project-documentation-disposition.yaml` but does not
replace it. Documentation disposition answers "what is the status of current
project documentation?" Legacy adoption answers "what is the active agent/process
authority layer?"

The documentation disposition phase also records a separate documentation legacy
adoption choice. This is a human-confirmed project-documentation handling
decision, not an agent-selected default. The main agent may recommend an option
and explain tradeoffs, but it must not choose the mode without the human's
confirmation.

Supported documentation legacy adoption modes:

```text
preserve-as-is
knowledge-extraction
rewrite-migration
archive-delete
```

When `knowledge-extraction` is selected, extraction depth is recorded as a
separate orthogonal choice:

```text
light
standard
deep
```

`light` depth is for exploratory, design-only or pilot runs and extracts only
the knowledge needed for the active run or target workflow. It does not unlock an
implementation phase unless the human explicitly accepts that risk or the
workflow upgrades depth to `standard` or `deep`. `standard` is the default depth
for `prepare-workflow` runs that may proceed to implementation. `deep` is for
large, conflicting, high-risk or documentation-heavy projects.
`rewrite-migration` and `archive-delete` require explicit human approval plus a
plan/backups before source documentation changes.

Before drafting the final project overlay, initialization must run a legacy adoption step:

```text
legacy agent-system discovery
legacy documentation/process classification
adoption mode decision
backup/quarantine if required
knowledge extraction / patch / rebuild / shadow pilot
active instruction map creation
validation that no ambiguous authority remains
human approval
```

Supported adoption modes:

```text
full-archive-rebuild
knowledge-extraction
minimal-patch-adapt
shadow-pilot
```

The final state must have one active agent-instruction authority layer. Every legacy artifact must be classified as active, imported, archived, deprecated, non-authoritative, or needs-human-decision.

See:

```text
docs/legacy-agent-system-adoption-model.md
docs/adr/ADR-0015-legacy-adoption-modes.md
```

## Optional haft / Quint Code integration

Project initialization is one of the best places to use haft/quint-code as an optional advanced decision-engineering provider.

Use it when:

```text
- project direction is unclear;
- workflow strategy is contested;
- gate strategy has long-term consequences;
- architecture/process decisions need frame/explore/compare/decide/verify;
- target system vs enabling system split is important;
- domain constraints need explicit decision contracts.
```

Expected outputs must be normalized into AgentsFlow artifacts:

```text
term-map.md
target-system-spec.md
enabling-system-spec.md
decision-contract.md
project-assessment.json
initialization-report.md
```

## Non-goals

Initialization does not implement features, rewrite source code, or silently apply process changes without approval.
