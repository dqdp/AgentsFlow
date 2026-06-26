# Skill: reviewer-architecture

## Purpose

Independently review artifacts for architecture consistency, modularity, scope, and ADR drift.

## Inputs

- `contract`
- `diff_or_artifact`
- `adrs`
- `evidence_report`
- `risk_surface_profile`
- `failure_path_matrix`
- `review_topology_rationale`


## Outputs

- `architecture_review_report`


## Procedure

1. Start with the packet's relevance inputs: `focus_zone` when present,
   `risk_surface_profile`, `failure_path_matrix`, `changed_files`,
   `verification_gate_report`, `evidence_freshness`, and `known_blockers`.
2. Read contract and fixed decisions.
3. Check boundary preservation.
4. Check module design.
5. Check whether selected architecture-relevant risk surfaces, such as
   `authority_boundary`, `public_api_contract`, `state_migration`,
   `persistence_consistency` or project-local surfaces, are reflected in
   boundaries and FPM rows.
6. Check review topology rationale for role/focus-zone fit when the packet
   claims risk-driven focused or heterogeneous review.
7. Flag architecture drift.
8. Classify issues by severity.


## Quality bar

- Review is grounded in contract and ADRs.
- Blocking issues are explicit.
- Risk-surface concerns are tied to contract/FPM/evidence, not architectural
  taste.


## Anti-patterns

- Reviewing by taste without contract reference.
- Choosing a different topology instead of reporting why the recorded topology
  rationale is inconsistent or unsupported.


## Handoff

Use deterministic scripts for checks when possible. Produce artifacts that can be consumed by workflows and review/fusion stages.


## Review-agent execution rule

This skill is a read-only review-agent skill.

It runs only after a verification gate has produced a gate report and evidence
bundle. It must not run tests, execute scripts, modify files, generate patches, or
update evidence. If additional verification is needed, report it as a finding for
workflow/human decision.


## Candidate finding rule

Reviewer findings are candidate findings, not authoritative truth. The reviewer must ground each finding in contract/evidence context and provide a relevance claim, but the main/orchestrating agent validates relevance before the finding becomes an accepted issue or required change.

## Interaction protocol

This reviewer produces candidate findings only. It must assign stable finding ids
where possible, mark P0/P1 items as candidate blockers, and provide evidence and
relevance claims.

The main/orchestrating agent validates findings using the decision matrix in
`docs/review-agent-interaction-protocol.md`. Review findings do not become required
changes until that validation occurs.

Default loop rule: repeated review agents are not rerun when there are no validated
blocking findings and no mandatory evidence gaps.

## Tool permission rule

This reviewer is read-only by default. Tool use is exceptional and must be explicitly granted by the workflow, reviewer manifest, or prompt. Any tool observation remains a candidate finding and does not replace verification-gate evidence.

## Risk-aware focus

Treat selected risk surfaces, Failure Path Matrix rows, evidence freshness and
known blockers as review inputs. Report missing or stale risk evidence as
candidate findings. Do not infer unselected risk surfaces as mandatory scope
unless the contract, ADRs or project policy make the omission a plausible P0/P1.

A P0/P1 finding should cite the relevant packet input when applicable. If no
relevance input applies, classify the issue as a contract, review-packet,
verification or valid-late-discovery gap instead of treating it as an ordinary
implementation blocker.
