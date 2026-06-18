# Review and Fusion Model

## Goal

Multi-model review and fusion reduce correlated blind spots in agent-assisted development.

They are not a replacement for deterministic checks or explicit contracts.


## Execution order

Review and fusion run after the verification gate.

```text
implementation/artifact
  ↓
verification gate: runs tests, scripts, checks, and evidence validation
  ↓
read-only review agents: inspect gate artifacts and classify issues
  ↓
fusion: synthesizes reviewer reports and preserves candidate blockers
  ↓
main-agent relevance validation: accepts/rejects/escalates findings
```

Review agents are read-only. They must not run tests, execute scripts, modify files,
or generate patches. If a reviewer believes more checks are needed, it reports
`needs-additional-verification`; the workflow or human decides whether to re-run
the verification gate. Reviewer findings are candidate findings, not authoritative
truth; the main/orchestrating agent must validate relevance before treating them
as accepted issues.

See `docs/review-control-model.md` for the shared control model and `docs/review-agent-interaction-protocol.md` for blocking definitions, loop exit criteria, and the relevance-validation decision matrix.

## Fusion is optional and workflow-selected

Fusion is not the global default. A workflow/profile may select no review,
`homogeneous-dual`, `homogeneous-plus-focused`, `heterogeneous-variable`, or the
non-primary `collision-control` exception. The topology is configuration, not
philosophy.

If review is enabled as a primary review gate, the minimum reviewer count is two.
Collision-control review is also batched through two reviewers: when one or more
blocker-level candidate findings are rejected or downgraded by the
main/orchestrating agent in the same review cycle, the workflow creates one
collision batch and sends that focused packet to two fresh-context control
reviewers.

## Review topology

Review topology is metadata selected by a workflow/profile.

Examples:

- `none`
- `homogeneous-dual`
- `homogeneous-plus-focused`
- `heterogeneous-variable`
- `collision-control` for rejected or downgraded blocker collision batches only, not as a primary gate

Reviewers start from fresh zero conversation context. They must not receive a
forked main-agent/orchestrator conversation. Their input is the review packet and
referenced artifacts declared by the workflow or project binding.

## Reviewer roles

### Architecture reviewer

Checks:

- ADR consistency;
- modularity;
- boundaries;
- architecture drift;
- hidden coupling;
- overengineering.

### Verification reviewer

Checks:

- test adequacy;
- impact map;
- evidence quality;
- weakened tests;
- missing regression cases.

### Adversarial reviewer

Checks:

- scope creep;
- ambiguous requirements;
- hidden failure modes;
- prompt/policy bypass;
- ungrounded claims;
- false completion.

## Fusion rules

Fusion is decision support, not final truth. It preserves reviewer findings and
disagreements, but the main/orchestrating agent must validate finding relevance
before accepted changes are required.

Fusion receives:

- task contract;
- diff or artifact;
- test/script results;
- evidence report;
- independent reviewer reports.

Fusion outputs:

- consensus points;
- disagreements;
- candidate blocking issues;
- non-blocking issues;
- required changes;
- human-decision items.

## Non-negotiable rule

Fusion must not erase a P0/P1 candidate issue by majority vote.

If one reviewer finds a plausible blocking issue, fusion must surface it explicitly.
The main/orchestrating agent may later reject or downgrade it only with a recorded
relevance-validation reason.


## Review cycle exit

Fusion may recommend a cycle decision, but the default AgentsFlow exit criterion is
validated by the main/orchestrating agent:

```text
no_validated_blocking_findings
```

Repeated review agents are not rerun when all P0/P1 candidate findings have been
validated and no validated blockers or mandatory evidence gaps remain. P2/P3/NOTE
findings can become follow-up work without forcing another review cycle.

## Result states

- `pass`
- `pass-with-notes`
- `needs-changes`
- `needs-verification-evidence`
- `human-decision-required`
- `blocked`

## Design note

In early versions, fusion can be prompt/manual. Automation should come after report formats stabilize.

## Fusion agent semantics

In AgentsFlow, Fusion Agent is a read-only synthesis actor, not a default
orchestrator. It consumes already-produced artifacts and reports:

- reviewer reports;
- finding validation reports;
- verification gate reports;
- evidence bundles;
- workflow context and accepted decisions.

It produces decision support: consensus, disagreement, blocker summary,
non-blocking concerns, and human-decision items.

By default, Fusion Agent must not launch additional reviewers, run verification
gates, run tests, call tools, or modify artifacts. It may recommend additional
review or verification, but the main/orchestrating agent owns the actual workflow
orchestration.
