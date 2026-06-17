# Reviewer Report

## Read-only review rule

This report is produced by a read-only review agent after a verification gate. The reviewer inspected gate artifacts and did not run tests, execute scripts, modify files, or generate patches.

All findings in this report are **candidate findings**. They are not authoritative truth until the main/orchestrating agent validates their relevance against the contract, artifact/diff, evidence, workflow context, and accepted decisions.

Reviewer Role: <architecture|verification|adversarial|product-spec|domain>
Model/Harness: <optional>
Contract: `<path>`
Artifact/Diff: `<path or description>`
Verification Gate Report: `<path>`

## Verdict

<pass|pass-with-notes|candidate-needs-changes|candidate-blocked|human-decision-suggested>

This verdict is a reviewer recommendation only.

## Blocking Candidate Findings

Each item should include a stable id, severity, evidence reference, relevance claim, and suggested validation.

| Finding ID | Severity | Candidate finding | Evidence reference | Relevance claim | Suggested validation |
|---|---:|---|---|---|---|
| F-001 | P0/P1 | ... | ... | why this matters for the current contract/workflow | what the main/orchestrating agent should check |

## Non-blocking Candidate Findings

| Finding ID | Severity | Candidate finding | Evidence reference | Relevance claim |
|---|---:|---|---|---|
| F-101 | P2/P3/NOTE | ... | ... | ... |

## Contract Adherence

- Intent satisfied: yes/no/uncertain
- Boundaries respected: yes/no/uncertain
- Fixed decisions preserved: yes/no/uncertain
- Evidence sufficient: yes/no/uncertain

## Missing Scenarios or Tests

- ...

## Risk Notes

- ...

## Suggested Changes

Suggested changes are not mandatory until the main/orchestrating agent validates the underlying finding.

- ...

## Reviewer Self-check

- I did not run tests or scripts.
- I did not modify files or generate a patch.
- I marked speculative concerns as speculative.
- I provided evidence/relevance claims for candidate findings.
- I understand that the main/orchestrating agent must validate relevance before acting on these findings.
