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
