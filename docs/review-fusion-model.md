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
plausible blocker-path candidate findings are rejected or downgraded by the
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
- `collision-control` for rejected or downgraded plausible blocker-path collision
  batches only, not as a primary gate

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
- prior finding validation reports when this is a later review cycle.

Fusion outputs:

- consensus points;
- disagreements;
- candidate blocking issues;
- non-blocking issues;
- required changes;
- human-decision items.

## Reusable finding-control pipeline

Review/fusion/finding-validation is a reusable gate-control block. Workflows
select the review topology and provide the contract, evidence, risk surfaces,
Failure Path Matrix and reviewer assignments; they should not duplicate the
finding-control procedure locally.

After reviewer reports arrive, the shared pipeline is:

1. Mechanical intake: check that expected reviewer reports exist, are
   schema-valid, fresh for the latest material change and match the declared
   reviewer assignment, provider, model family, role and topic where applicable.
2. Canonical finding extraction: preserve each source finding and add normalized
   triage metadata such as provider, model, topic, role, severity, evidence
   references, risk surface and FPM row when available.
3. Duplicate / related / conflict grouping: group true duplicates without
   losing max severity, mark related findings that share an area but differ in
   mechanism, and preserve conflicts as disagreements requiring validation.
4. Topic-pair comparison: when a topology uses mirrored topics or providers,
   compare findings inside the same topic pair before drawing cross-topic
   conclusions.
5. Fusion report: surface consensus, disagreements, candidate blockers,
   mandatory evidence gaps and validation priorities.
6. Main-agent relevance validation: accept, reject, downgrade, mark duplicate,
   request more evidence or escalate findings against contract, diff/artifact,
   evidence, accepted decisions, scope and non-goals. P0/P1 validation must
   record a grounded blocker path; reviewer severity is not accepted severity.
7. Collision-control: if the orchestrator rejects or downgrades plausible
   blocker-path candidate findings, batch those collisions and send them to two
   fresh-context control reviewers before final triage.
8. Review-cycle decision: exit only when there are no validated blockers, no
   unresolved P0/P1 candidates and no mandatory evidence gaps.

## Severity calibration

Fusion preserves reviewer-suggested severity, but it does not convert that
severity into a validated blocker. For every candidate blocker, fusion should
hand off the asserted blocker path when the reviewer provided one: the violated
contract, accepted decision, gate policy, authority boundary or mandatory
evidence requirement; the evidence reference; and the concrete consequence for
acceptance.

If a reviewer marks a finding P0/P1 based only on risk-surface or Failure Path
Matrix membership, fusion must preserve the candidate finding but flag that the
blocker path is missing. Risk/FPM membership guides review attention and
verification depth; it is not severity by itself.

When reviewers identify suspected boundary impact, fusion preserves that
boundary hint for main-agent validation. Boundary Trace is required only when
triggered by accepted P0/P1, a mandatory evidence gap, a changed gate invariant
or another concrete boundary-loss path. The trace belongs to finding validation;
fusion should not turn boundary impact into severity.

## Authority boundary

This reusable block must not confuse automatic gates with human-in-the-loop
authority. Deterministic automation may validate report structure, schema,
freshness and declared evidence references. Fusion provides decision support.
The main/orchestrating agent validates candidate findings. Human-mediated gates
remain human-owned and require normalized human decisions before the workflow
claims human acceptance or merge readiness.

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

- schema-bound reviewer-report JSON artifacts;
- verification gate reports;
- evidence bundles;
- workflow context and accepted decisions.
- prior finding validation reports when available from earlier cycles.

It produces decision support: consensus, disagreement, blocker summary,
non-blocking concerns, and human-decision items.

Markdown reviewer summaries or raw reviewer transcripts are optional sidecars.
Fusion may reference them for orientation or traceability, but normalized JSON
reviewer-report artifacts are the source reports consumed by gates and finding
fusion.

By default, Fusion Agent must not launch additional reviewers, run verification
gates, run tests, call tools, or modify artifacts. It may recommend additional
review or verification, but the main/orchestrating agent owns the actual workflow
orchestration.
