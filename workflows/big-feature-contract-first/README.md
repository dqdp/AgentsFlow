# Workflow: big-feature-contract-first

## Intent

Implement a large feature through contract, BDD scenarios, impact map, verification gates, and evidence.

## Typical outputs

- task contract
- BDD scenarios
- impact map
- implementation plan
- evidence report
- review/fusion reports when enabled

## Operating context

The workflow starts with an operating-context preflight. A prior
`project-initialization` run is useful but not mandatory: the required condition
is enough project policy, workflow binding, verification gate, review policy and
evidence-location context to execute the target workflow safely.

Open questions in the task contract are classified before the agent asks the
human. `blocking-material` questions pause the workflow; nonblocking questions
are recorded with defaults, limitations or follow-up handling.


## Primary skills

- contract-authoring
- bdd-scenario-design
- impact-map-builder
- adr-consistency-check
- evidence-reporting
- reviewer-architecture
- reviewer-verification
- fusion-synthesis


## Notes

This workflow is a composition recipe. Do not duplicate the full content of invoked skills here.

Per ADR-0017, the implementation phase is to be framed by a pre-implementation
red-capture (write the contract's acceptance tests, run them against the
unimplemented state, capture the failing runs) and the verification gate's green
re-run; the red→green evidence pair is a byproduct of this structure. `workflow.yaml`
now represents this topology with `test_framing` markers, and `validate_repo.py`
checks the structural framing.

When effective strictness reaches the workflow's plan-gate depth, the workflow
includes a manifest-level `plan_gate` before red capture. The gate validates that
the plan is grounded, scoped, testable and ready for implementation; it is not a
prose-only step. Project bindings inherit the workflow default unless they
explicitly record a strictness override reason.

Passing the plan gate is necessary but not sufficient to enter red-capture. The
workflow includes a human-mediated `contract_acceptance` after the plan gate
and before red-capture. The main agent presents the contract, behavior bindings,
risk surface profile, Failure Path Matrix, impact map and technical plan; the
human accepts them for red-capture or requests changes. The agent records the
normalized decision in `human-decisions.yaml` and updates run metadata before
red-capture may begin.

After review, fixes are classified as material or non-material before deciding
whether another review cycle is required. A P2 finding can still produce a
material fix if the fix changes schemas, validators, workflow policy, bindings,
mandatory evidence or examples used as evidence.
