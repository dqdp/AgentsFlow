# Plan: Boundary Trace Finding Validation

## Scope

This run adds a small triggered Boundary Trace rule to existing review/fusion
artifacts. It deliberately avoids a new workflow, new schema or new validator.

## Steps

1. Add a failing smoke test that expects:
   - Boundary Trace trigger conditions in the finding-validation template.
   - The label set to be present.
   - The phrase that boundary impact is not severity.
   - Fusion skill/template to preserve suspected boundary impact for
     orchestrator validation.
   - Review protocol to make the trace trigger-based, not universal.
2. Update the minimal docs/templates/skill surfaces:
   - `templates/finding-validation-report.md`
   - `templates/fusion-report.md`
   - `skills/fusion-synthesis/SKILL.md`
   - `docs/review-agent-interaction-protocol.md`
   - `docs/review-fusion-model.md`
   - `templates/review-prompts/base.md`
3. Add a v0.2 MVP contract scenario and binding for the smoke check.
4. Run targeted and full validation.
5. Run a short Codex-only `homogeneous-plus-focused` review gate:
   - generalist baseline reviewer A;
   - generalist baseline reviewer B;
   - process-semantics / over-complexity focused reviewer.
6. Validate findings critically. Fix only accepted P0/P1 or cheap consistency
   issues with clear value.
7. Commit the slice.

## Over-Complexity Guard

Do not add a parser, schema, validator or new artifact type unless validation
shows the rule cannot be kept coherent through existing templates and smoke
coverage.
