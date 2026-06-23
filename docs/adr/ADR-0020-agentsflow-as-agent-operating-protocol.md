# ADR-0020: AgentsFlow as Agent Operating Protocol

## Status

Proposed.

Date: 2026-06-20

## Context

AgentsFlow is used by external coding agents that already have their own runtime,
tool execution model, conversation state, review-launch mechanism and project
environment. The project can add schemas, templates, workflow definitions,
validators and evidence contracts, but it should not try to become a complete
workflow engine for those agents.

This is not only a practical limitation. It is an architectural advantage:

- AgentsFlow remains portable across agent providers and local environments.
- Project-specific execution stays in project overlays and project-bound gates.
- The main/orchestrating agent can still use engineering judgment where judgment
  is required.
- Judgment becomes reviewable because it is recorded in contracts, decisions,
  gates, review packets and evidence reports.
- Validators can remain honest about what they actually prove.

Recent design work on risk surfaces and risk-driven review topology exposed this
boundary clearly. A deterministic checker can validate that a review packet has
declared risk surfaces, a Failure Path Matrix reference and evidence freshness
metadata. It cannot cheaply or reliably decide the best architecture reviewer
composition for every project without reintroducing hidden model judgment under
the label of automation.

## Decision

AgentsFlow is an **agent operating protocol**, not a workflow runtime.

It standardizes:

- workflow shapes and phase boundaries;
- project overlays and project-bound gate bindings;
- task contracts and behavior bindings;
- human questions and decisions;
- gate reports and evidence reports;
- review topology declarations, review packets and finding validation;
- provenance, freshness and artifact authority expectations.

It does not try to:

- own the external agent's execution loop;
- automatically launch all gates, reviewers or implementation steps;
- infer project policy that was not declared in workflow, project binding or run
  artifacts;
- hide model judgment inside deterministic validators;
- replace human-mediated decisions with implicit automation;
- become a generic multi-provider agent runtime.

Engineering judgment may be agent-mediated when the choice is not deterministic,
cheap and evidence-grounded. The protocol requires that such judgment be made
explicit, normalized into artifacts and exposed to verification, review or human
decision gates when material.

## Enforcement Boundary

AgentsFlow validators should enforce shape, references and protocol invariants,
for example:

- required files and schemas exist;
- required workflow phases and gate bindings are declared;
- review agents are read-only and run after verification by policy;
- required behavior bindings have checks and gates;
- review packets contain required context fields;
- workflow-run ledgers do not promote future-phase artifacts;
- project operating decisions contain required policy blocks.

Validators should not claim to prove:

- that an architecture is correct;
- that a risk surface selection is complete for every domain;
- that a heterogeneous reviewer set is optimal;
- that reviewer processes received no hidden context beyond protocol evidence;
- that all failure semantics are understood beyond the project-bound checks and
  evidence actually supplied.

When a check cannot be deterministic and cheap, AgentsFlow should prefer a
protocol requirement:

```text
record the decision -> bind the evidence -> review the packet -> validate
findings -> ask the human when authority is required
```

rather than an overconfident automated rule.

## Risk-Driven Review Implication

Risk-driven review topology follows this ADR.

The protocol may require a task to record:

```yaml
review:
  topology: heterogeneous-variable
  topology_source: risk_surface_profile
  selected_risk_surfaces:
    - authority_boundary
    - audit_persistence
  escalation_reason: "Authority and audit failure paths need architecture, verification and adversarial focus."
```

It may require the review packet to include:

- selected risk surfaces;
- Failure Path Matrix rows or references;
- classified behavior bindings;
- latest green evidence after the latest material change;
- known blockers and their status.

It should not silently auto-route reviewers from an opaque rule such as:

```text
feature looks complex -> add more reviewers
```

Nor should it hard-code a universal reviewer mapping for every surface. A project
or workflow binding may define a deterministic mapping if it is useful locally,
but the upstream v0.2 protocol keeps the default rule smaller:

```text
selected risk surfaces -> required failure paths -> evidence obligations ->
minimal justified review topology -> review packet with rationale
```

## Relationship To Existing ADRs

This ADR supports:

- ADR-0001, because workflows compose skills, scripts, templates, packs and
  profiles rather than becoming monolithic runtimes.
- ADR-0005, because review agents consume verification evidence instead of
  producing it by running gates themselves.
- ADR-0007, because reviewer output remains candidate findings until
  main-agent relevance validation.
- ADR-0010 and ADR-0012, because executable gates remain project-bound
  deterministic runners rather than upstream prose.
- ADR-0013 and ADR-0014, because project application and initialization record
  decisions and overlays without assuming a central workflow engine.
- ADR-0018, because phase transition control is a read-only boundary check, not
  an orchestrator.

It also constrains future work after ADR-0019: default/effective strictness may
control gate and review depth, but it should not become a hidden runtime mode
that automates unrecorded judgment.

## Consequences

- AgentsFlow stays small enough for v0.2 MVP while still making external-agent
  behavior auditable.
- Protocol artifacts become the durable source of truth, not conversation memory
  or hidden runtime state.
- Project-bound gates and local wrappers remain the right place for executable
  project-specific checks.
- Risk-driven heterogeneous review remains explicit and evidence-grounded.
- Future automation is allowed when it is deterministic, scoped and honest about
  its proof strength.
- The project should resist adding parallel abstractions that duplicate existing
  artifacts merely to simulate a workflow runtime.

## Alternatives Considered

### Build a workflow runtime

Rejected for v0.2. It would duplicate external agent runtimes, increase surface
area, and blur the boundary between deterministic checks, model judgment and
human authority.

### Make validators decide all process choices

Rejected. Validators are valuable when they enforce declared structure and
evidence shape. They become misleading when they pretend to make architectural or
domain judgments without project-bound evidence.

### Leave everything to prompt discipline

Rejected. AgentsFlow exists because important process behavior should not depend
only on memory or prompt text. The protocol must record contracts, decisions,
evidence and review packets so another agent or human can inspect the run.

## Open Questions

- Which future checks are deterministic and useful enough to promote from
  protocol requirements into validators?
- Should project bindings optionally define local deterministic mappings from
  risk surfaces to reviewer roles?
- How much review-packet generation should be scripted before it starts to look
  like an orchestrator?
