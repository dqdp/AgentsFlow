# Skill: impact-map-builder

## Purpose

Map affected modules/paths and selected risk surfaces to required tests,
scripts, contracts, ADRs, evidence bindings and verification gaps.

## Inputs

- `contract`
- `changed_paths_or_planned_paths`
- `domain_pack`
- `risk_surface_profile`
- `failure_path_matrix`
- `behavior_bindings`


## Outputs

- `impact_map`
- `required_tests`
- `required_scripts`
- `risk_surface_check_map`
- `failure_path_binding_gaps`
- `related_adrs`


## Procedure

1. Identify affected modules.
2. Map paths to test suites.
3. Map selected risk surfaces and FPM rows to concrete checks: tests, scripts,
   static/dynamic analysis, trace/log assertions, manual evidence or domain
   tools.
4. Verify that each required FPM row has an evidence binding or an explicit
   human-approved deferral.
5. Include architecture, policy, audit/persistence, secret/privacy, external IO,
   timeout/budget or other checks implied by selected risk surfaces.
6. Include related ADRs/contracts.
7. Mark verification gaps with the affected risk surface, path class and FPM id.


## Quality bar

- Required tests are specific enough for an implementer.
- Gaps are visible.
- Gaps identify the exact risk surface/path class/FPM row they affect.


## Anti-patterns

- Saying “run tests” without specifying which tests.
- Treating a selected risk surface as covered without a mapped check or explicit
  deferral.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.
