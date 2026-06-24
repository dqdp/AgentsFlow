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

Updated for review-gate hardening on 2026-06-24: review-loop and health-control
decisions count validated findings and mandatory evidence gaps, not raw reviewer
candidates. A candidate P0/P1 does not block acceptance or trigger a health
checkpoint until the main/orchestrating agent records a grounded validation
decision.

Validated P0/P1 findings and mandatory evidence gaps block acceptance by
default. Important P2/P3 findings may be fixed while a validated blocker loop is
already open, but the main/orchestrating agent must record whether the fix is
material to review inputs.

P2/P3-only findings do not trigger a review rerun unless the fix materially
changes contract, scope, schema, validator behavior, mandatory evidence,
verification result, project overlay, workflow policy, review packet content or
current evidence examples.

The main/orchestrating agent records accepted, fixed, deferred and rejected
P2/P3 rationale in the review-cycle or finding-validation report.

## Consequences

- Review reports become structured inputs, not final truth.
- Fusion reports are decision support, not final acceptance.
- The main/orchestrating agent owns relevance triage before implementing reviewer
  suggestions or declaring acceptance.
- False positives and irrelevant concerns can be rejected, but not silently.
- Future implementation agents must receive validated findings, not raw reviewer output.
