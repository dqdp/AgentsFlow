# Skill: reviewer-adversarial

## Purpose

Look for scope creep, prompt/policy bypasses, hidden failure modes, and false completion.

## Inputs

- `contract`
- `artifact`
- `evidence_report`
- `domain_pack`
- `risk_surface_profile`
- `failure_path_matrix`
- `known_blockers`


## Outputs

- `adversarial_review_report`
- `risk_notes`


## Procedure

1. Start with the packet's relevance inputs: `focus_zone` when present,
   `risk_surface_profile`, `failure_path_matrix`, `changed_files`,
   `verification_gate_report`, `evidence_freshness`, and `known_blockers`.
2. Assume the implementation may be subtly wrong.
3. Search for boundary violations.
4. Search for bypasses, false completion or hidden failure modes in selected
   risk surfaces and FPM rows.
5. Search for ambiguous behavior.
6. Search for false or stale evidence.
7. Propose regression scenarios tied to concrete triggers and path classes.


## Quality bar

- Findings are plausible and testable.
- Speculative concerns are labeled as such.
- Bypass/failure concerns name the affected surface, path class or contract
  boundary when possible.


## Anti-patterns

- Blocking on vague suspicion without a concrete failure mode.
- Expanding review scope by inventing unselected risk surfaces without contract,
  ADR or project-policy support.


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

Treat selected risk surfaces, Failure Path Matrix rows, freshness metadata and
known blockers as attack surfaces for review. Report plausible bypass,
misclassification, missing denial path, hidden timeout/failure path, audit loss
or false-completion risks as candidate findings with concrete triggers.

A P0/P1 finding should cite the relevant packet input when applicable. If no
relevance input applies, classify the issue as a contract, review-packet,
verification or valid-late-discovery gap instead of treating it as an ordinary
implementation blocker.
