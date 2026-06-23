# Term Map

| Term | Meaning | Notes / Related Terms |
|------|---------|-----------------------|
| workflow | Primary user-facing process abstraction | |
| skill | Agent-facing procedure/reasoning block | |
| script | Deterministic check or automation | |
| gate | Workflow control point with explicit exit criteria and authority mode | Do not infer authority from the word "gate"; use `deterministic_gate`, `review_gate`, or `human_mediated_gate` when the distinction matters. |
| deterministic_gate | Gate decided by a deterministic runner over declared checks/evidence | Produces a gate report; may return `needs_human_decision` for missing manual evidence, but does not make human approval decisions. |
| review_gate | Gate based on independent reviewer reports plus main-agent relevance validation | Reviewers produce candidate findings; exit requires no validated blockers and no mandatory evidence gaps. |
| human_mediated_gate | Gate where the main agent synthesizes evidence/review/options and the human makes or confirms the decision | Used for plan approval, scope/ADR changes, high-risk overrides, and other human-owned decisions. |
| default_strictness | Workflow-owned baseline for evidence, gate and review depth | A workflow should declare the baseline depth that fits its normal use; project bindings inherit it unless they explicitly override. |
| effective_strictness | The strictness value used for a concrete project binding or run | Derived from `default_strictness` plus any explicit `strictness_override`. Conditional gates use this value. |
| strictness_override | Explicit deviation from a workflow's `default_strictness` | Requires a reason and should be rare; use it for project risk, pilot scope or exceptional constraints, not as a routine setup question. |
| strictness_taxonomy | The named set of strictness values available to workflows | v0.2 remains compatible with current `L*` identifiers; a smaller two- or three-level taxonomy is a follow-up decision, not a new workflow mechanism. |
| reviewer | Read-only evaluator | |
| fusion | Synthesis of reviewer outputs | |
| evidence | Artifact proving what was checked | |
