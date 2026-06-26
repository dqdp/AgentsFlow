# ADR-0007: Review Findings Require Relevance Validation

Status: Accepted

Date: 2026-06-17

## Context

AgentsFlow uses read-only review agents to find risks, evidence gaps, contract violations,
and possible blockers after a verification gate. Review agents are useful precisely
because they are independent, but independence also creates false positives, duplicated
concerns, taste-based objections, and findings that may be irrelevant to the accepted
contract or current workflow.

If reviewer findings are treated as truth automatically, review agents become an
uncontrolled authority rather than an input to a controlled workflow.

## Decision

Reviewer findings are candidate findings until the main/orchestrating agent validates
their relevance.

The main/orchestrating agent must validate each material finding against the task
contract, artifact/diff, verification gate report, evidence bundle, relevant ADRs,
accepted decisions, workflow profile, and non-goals.

A candidate finding may be classified as:

- `accepted-relevant`;
- `rejected-irrelevant`;
- `needs-more-evidence`;
- `duplicate`;
- `human-decision-required`.

P0/P1 candidate findings must not be silently discarded. Rejection or downgrading of
a plausible blocker must include a recorded reason.

Proposed follow-up: ADR-0022 should define a review-loop health checkpoint for
repeated validated blockers. Health triggers count only main-agent validated
P0/P1 blockers and mandatory evidence gaps, not raw reviewer candidates.

Review-fix loops must not treat a closure-only review as an acceptance-capable
review gate after a material change. After material fixes, the next
acceptance-capable review must inspect the full current review packet and must
ask reviewers both to confirm closure of prior validated findings and to look
for new P0/P1 blockers across the changed scope.

After a finding is validated and before a fix-loop starts, the
main/orchestrating agent must choose the remediation layer. Validating a P0/P1
finding does not imply that the current workflow, evaluator or schema should gain
new responsibilities.

The default remediation order is:

1. remove misplaced responsibility from the current layer;
2. fail closed and defer proof to the owning workflow or evidence producer;
3. use an existing contract, field or evidence reference;
4. add a small local check;
5. add a new schema field, artifact class or mechanism only with an explicit
   rationale for why the first four options are insufficient.

The chosen remediation layer and rationale should be recorded in the existing
finding-validation or review-cycle report. No separate schema is required unless
a workflow needs deterministic validation of that record.

Important P2/P3 findings may be fixed while a validated blocker loop is already
open. P2/P3-only findings do not trigger another review gate unless the fix
materially changes contract, schema, validator behavior, mandatory evidence,
verification result, project overlay, workflow policy or current evidence
examples. Accepted, fixed, deferred and rejected P2/P3 rationale should be
recorded in finding validation or the review-cycle report.

## Consequences

- Review reports become structured inputs, not final truth.
- Fusion reports are decision support, not final acceptance.
- The main/orchestrating agent owns relevance triage before implementing reviewer
  suggestions or declaring acceptance.
- False positives and irrelevant concerns can be rejected, but not silently.
- Future implementation agents must receive validated findings, not raw reviewer output.
