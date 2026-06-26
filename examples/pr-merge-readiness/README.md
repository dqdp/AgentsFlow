# PR Merge Readiness Examples

This directory contains small artifacts for the `pr-merge-readiness` utility
workflow. The examples are validation fixtures, not a release automation system.

`complete/pr-merge-readiness-report.json` is a lite validation fixture with
recorded human approval, deterministic check evidence and the default
required PR readiness review evidence: `generalist-a`, `generalist-b` and
`adversarial-codex`. The review gate that produced that evidence is outside this
fixture; `complete/review-requirements.yaml` is the hash-bound normalized source
for the fixture's required review list. The report is marked with
`fixture.not_real_readiness_evidence: true`, so the evaluator treats it as
non-mergeable fixture evidence. This directory is not proof that an actual live
PR readiness run occurred.
