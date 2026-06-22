# PR Merge Readiness Examples

This directory contains small artifacts for the `pr-merge-readiness` utility
workflow. The examples are validation fixtures, not a release automation system.

`complete/pr-merge-readiness-report.json` is a complete validation fixture with
recorded human approval, deterministic check evidence, provider-mirrored review
evidence and live-shaped Claude invocation metadata references. It is marked
with `fixture.not_real_readiness_evidence: true`, so the evaluator treats it as
non-mergeable fixture evidence. The report-facing raw-output evidence uses
redacted summary artifacts, and the Claude invocation metadata records the raw
provider output hash without a persisted raw-output path. This directory is not
proof that an actual live PR readiness run occurred.
