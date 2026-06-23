# Checkpoint: AgentsFlow v0.2 Supported Path Narrowing

## Purpose

This checkpoint supersedes the v0.2 workflow-scope statements in
`checkpoint-2026-06-18-v0.2.0-slice2.md` where they describe a broader
`prepare-workflow` target set.

## Accepted supported path for v0.2

AgentsFlow v0.2 supports one application path end to end:

```text
project-initialization.prepare-workflow
-> big-feature-contract-first
```

`project-initialization` remains the application/onboarding workflow. It is broad
enough to support discovery, adoption onboarding, prepare-workflow, legacy
cleanup and risk/domain assessment modes.

For `prepare-workflow`, the only supported `target_workflow` in v0.2 is:

```text
big-feature-contract-first
```

## Workflow status boundary

`review-only-fusion` remains a v0.2 utility workflow. It can be used for
independent review and fusion of existing artifacts or diffs, but it is not a
supported `prepare-workflow.target_workflow`.

`bugfix-regression-capture` and `new-project-spec-first` remain schema-valid
reference/next workflows in v0.2. They are not supported target workflows and
are not part of the v0.2 pilot path.

Reference/experimental workflows remain schema-valid only unless a future
accepted decision promotes them.

## Contract consequences

Project intake and project documentation disposition schemas reject
`prepare-workflow.target_workflow` values other than
`big-feature-contract-first`.

Repository review-control validators apply v0.2 review policy checks to:

```text
big-feature-contract-first
review-only-fusion
```

They do not treat reference/next workflows as v0.2 review-control surfaces.

## Rationale

The v0.2 pilot is intended to prove one real workflow application path before the
project claims broad workflow support. Keeping the supported target set narrow
reduces false completion risk, avoids overclaiming unproven workflow coverage,
and keeps the Bro pilot focused on initialization followed by a large feature
contract-first workflow.
