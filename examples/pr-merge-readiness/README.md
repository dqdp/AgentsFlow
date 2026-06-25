# PR Merge Readiness Examples

This directory contains small artifacts for the `pr-merge-readiness` utility
workflow. The examples are validation fixtures, not a release automation system.

`complete/pr-merge-readiness-report.json` is a complete validation fixture with
recorded human approval, deterministic check evidence and the default
`homogeneous-plus-focused` review evidence: `generalist-a`, `generalist-b` and
`adversarial-codex`. It is marked with
`fixture.not_real_readiness_evidence: true`, so the evaluator treats it as
non-mergeable fixture evidence. This directory is not proof that an actual live
PR readiness run occurred.
