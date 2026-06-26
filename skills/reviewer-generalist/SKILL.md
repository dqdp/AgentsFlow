# Skill: reviewer-generalist

## Purpose

Run the baseline homogeneous review pass using the common rubric. This role is
not a specialist. It is used when two independent reviewers should receive the
same prompt, packet, rubric and output schema.

## Inputs

- `review_packet`
- `contract`
- `diff_or_artifact`
- `verification_gate_report`
- `evidence_bundle`
- relevant ADRs and accepted decisions included in the packet
- selected risk surfaces, Failure Path Matrix, known blockers and evidence
  freshness when included in the packet

## Procedure

1. Read only the provided review packet and referenced artifacts.
2. Start with the packet's relevance inputs: `focus_zone` when present,
   `risk_surface_profile`, `failure_path_matrix`, `changed_files`,
   `verification_gate_report`, `evidence_freshness`, and `known_blockers`.
3. Check contract and accepted-decision consistency.
4. Check verification evidence, including missing mandatory checks and red/green
   evidence when required.
5. Check selected risk surfaces, Failure Path Matrix rows, path-class bindings,
   known blockers and evidence freshness when present in the packet.
6. Check scope boundaries and non-goals.
7. Look for obvious architecture, reliability, safety, workflow or evidence risks.
8. Report any plausible P0/P1 candidate blocker, even if it spans multiple rubric
   sections.
9. Return candidate findings only.

## Homogeneous Execution Rule

When used in `homogeneous-dual`, both reviewer instances receive the same prompt,
same packet, same rubric and same output schema. Reviewer labels such as
`generalist-a` and `generalist-b` are instance identifiers only; they do not
change the prompt.

## Review-Agent Execution Rule

This skill is read-only. It starts from fresh zero conversation context and must
not receive a forked main-agent/orchestrator conversation. It must not run tests,
execute scripts, modify files, generate patches, or update evidence.

If additional verification is needed, report it as a candidate finding such as
`needs-additional-verification`.

## Risk-Aware Review Rule

The reviewer must not choose or change review topology. It may report that the
packet's selected risk surfaces, focus zones, Failure Path Matrix coverage or
freshness evidence appear inconsistent, incomplete or stale. Missing selected
risk-surface/FPM evidence is a candidate evidence gap, not proof that the
implementation is wrong.

A P0/P1 finding should cite the relevant packet input when applicable. If no
relevance input applies, classify the issue as a contract, review-packet,
verification or valid-late-discovery gap instead of treating it as an ordinary
implementation blocker.

## Candidate Finding Rule

Reviewer findings are candidate findings, not authoritative truth. The
main/orchestrating agent validates relevance before a finding becomes an accepted
issue or required change.
