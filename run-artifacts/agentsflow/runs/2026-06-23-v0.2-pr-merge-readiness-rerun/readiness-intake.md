# Readiness Intake: v0.2 PR Merge Readiness Rerun

## Scope

- Workflow: `pr-merge-readiness`
- Run id: `2026-06-23-v0.2-pr-merge-readiness-rerun`
- Base branch: `main`
- Base commit: `aa4374a`
- Target branch: `v0.2-prehandoff-design`
- Target content head: `8a2c197`
- Commit range: `main..8a2c197`
- Application mode: self-application PR acceptance

## Rerun Reason

The previous PR-readiness attempt for `fc5f09c` was blocked by validated P1
evidence gaps:

- range-bound `git diff --check main..fc5f09c` failed;
- deterministic evidence lacked durable command evidence paths;
- live Claude provider-mirrored review failed without normalized reports.

Commit `8a2c197` fixes the range whitespace issue and hardens failed external
review invocation evidence and prompt serialization requirements. This run is a
fresh run for the new material change id.

## Authority Boundary

This run must not claim merge readiness before:

- deterministic evidence is recorded;
- provider-mirrored review completes;
- fusion and finding validation complete;
- a human `merge.acceptance` decision is recorded against the final readiness
  report hash.

## Review Focus

The accepted review topology remains provider-mirrored topic pairs:

- verification evidence: Codex and Claude;
- architecture/process: Codex and Claude;
- adversarial authority: Codex and Claude.

Workflow composition integrity remains a dedicated architecture-process focus.
The known duplication of review-control policy text is non-blocking unless a
reviewer identifies a concrete contradiction, broken validator path or false
readiness claim.
