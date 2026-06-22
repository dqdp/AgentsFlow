# Design Decision Review: pr-merge-readiness First Slice

## Purpose

This artifact is the design-review decision packet for the
`pr-merge-readiness` bootstrap run. It does not ask for one blanket approval
without context. It first lists the open decisions, then reviews each decision
with options, tradeoffs and a recommended path.

Human acceptance of this packet authorizes `red_capture`, not implementation
without failing-test evidence.

## Review Procedure

1. Present the full open decision inventory.
2. Review each decision independently.
3. For each decision, show viable options, tradeoffs, recommendation and
   rationale.
4. Record explicit human acceptance or change requests.
5. Only after accepted blocking decisions are recorded, enter `red_capture`.

## Open Decision Inventory

| ID | Decision | Blocking before red-capture? | Recommended path |
|---|---|---:|---|
| DDR-001 | Utility workflow scope and status | yes | v0.2 utility workflow, not primary application workflow |
| DDR-002 | Build method for this workflow | yes | implement through `big-feature-contract-first` |
| DDR-003 | Self-application artifact separation | yes | ignored `.agentsflow/` overlay plus `run-artifacts/agentsflow/runs/...` run root |
| DDR-004 | First implementation slice shape | yes | workflow + schema + template + example + validator + docs |
| DDR-005 | Readiness authority model | yes | evidence report plus required human merge decision |
| DDR-006 | Failure Path Matrix scope | yes | cover false readiness, missing/stale evidence, mock/live confusion, raw redaction and blocker triage |
| DDR-007 | External Claude evidence policy | yes | normalized report and invocation metadata always; raw only when non-sensitive |
| DDR-008 | Target workflow review gate topology | yes | heterogeneous-variable with provider-mirrored Codex/Claude topic pairs |
| DDR-009 | Allowed and forbidden change boundaries | yes | narrow methodology paths; no release platform, PR mutation or provider rewrite |
| DDR-010 | Readiness report field names and exact validator strictness | no | decide during red-capture from failing tests |

## DDR-001: Utility Workflow Scope and Status

### Problem

AgentsFlow needs a repeatable way to judge whether a branch is ready for PR
opening, PR acceptance or merge. This should not expand v0.2's primary workflow
surface.

### Options

| Option | Description | Strengths | Costs / risks |
|---|---|---|---|
| A | Documentation-only checklist | Fast, no schema or validator work | Easy to drift; not enforceable; weak evidence story |
| B | v0.2 utility workflow | Fits `review-only-fusion` precedent; gives a reusable gate without becoming an application workflow | Requires workflow/schema/template/test work |
| C | Primary application workflow | First-class visibility | Expands v0.2 scope and competes with `project-initialization -> BFCF` |
| D | Full release workflow | Could eventually cover release operations | Out of v0.2 scope; pulls in platform/runtime decisions |

### Recommendation

Use Option B: `pr-merge-readiness` as a v0.2 utility workflow.

### Rationale

This keeps the supported application path narrow while giving the project an
explicit acceptance/merge gate. It avoids pretending that merge readiness is
just prose, but also avoids turning v0.2 into a release platform.

### Human Acceptance Question

Is `pr-merge-readiness` accepted as a v0.2 utility workflow rather than a
primary application workflow or release platform?

## DDR-002: Build Method for This Workflow

### Problem

AgentsFlow is applying itself to build a new workflow. The process must avoid
ad hoc edits and avoid cyclic proof.

### Options

| Option | Description | Strengths | Costs / risks |
|---|---|---|---|
| A | Direct edits without workflow run | Fast | Undercuts the methodology; weak evidence trail |
| B | Build through existing `big-feature-contract-first` | Dogfoods accepted workflow; contract, red/green and review are explicit | More ceremony |
| C | Wait until `pr-merge-readiness` exists, then use it | Conceptually neat later | Cyclic for bootstrap; impossible before implementation |

### Recommendation

Use Option B for the bootstrap run.

### Rationale

`big-feature-contract-first` is already the supported feature workflow. The new
workflow must not prove itself before it exists, so the first full
`pr-merge-readiness` use should happen in a later PR/merge acceptance run.

### Human Acceptance Question

Is it accepted that this first slice is built through BFCF and explicitly marked
as a bootstrap, not a self-proof?

## DDR-003: Self-Application Artifact Separation

### Problem

AgentsFlow is both methodology source and target project. Run evidence,
project overlay and methodology files can be confused.

### Options

| Option | Description | Strengths | Costs / risks |
|---|---|---|---|
| A | Put run artifacts under `docs/` | Discoverable | Confuses evidence with methodology source |
| B | Put run artifacts under `.agentsflow/` | Localized | `.agentsflow/` should be overlay/cache, not durable run history |
| C | Put run artifacts under `Docs/agentsflow/runs/` | Matches ordinary target-project convention | Bad for this repo because `Docs` can collapse into existing `docs` on case-insensitive filesystems |
| D | Use `run-artifacts/agentsflow/runs/<run-id>/` | Clear separation from methodology source and overlay | Adds one repository-local artifact root |

### Recommendation

Use Option D for self-application run history, with `.agentsflow/` reserved for
ignored local overlay.

### Rationale

This protects the source/evidence boundary with minimal machinery. Ordinary
target projects can still use the canonical `Docs/agentsflow/runs/...` pattern;
this repository needs the special case because it already has lowercase
`docs/`.

### Human Acceptance Question

Is the self-application storage boundary accepted: ignored `.agentsflow/`
overlay, run evidence in `run-artifacts/agentsflow/runs/...`, promoted
methodology changes only through explicit source diffs?

## DDR-004: First Implementation Slice Shape

### Problem

A workflow can be documented but still not usable. The first slice must be
small enough for v0.2 and concrete enough to validate.

### Options

| Option | Description | Strengths | Costs / risks |
|---|---|---|---|
| A | Docs only | Cheapest | Not executable; weak DoD |
| B | Workflow + docs | Better structure | Still no report contract or validator evidence |
| C | Workflow + schema + template + example + validator + docs | Executable first slice; validates examples and report semantics | More files and tests |
| D | Full runner/runtime integration | Most complete | Too much scope for v0.2 closure |

### Recommendation

Use Option C.

### Rationale

The desired v0.2 UX needs a concrete readiness packet, not just workflow prose.
The schema/template/example/validator set is enough to make the workflow usable
without creating a new runtime.

### Human Acceptance Question

Is the first slice accepted as workflow definition, readiness report schema,
template, examples, validator coverage and docs, with no platform mutation
runtime?

## DDR-005: Readiness Authority Model

### Problem

The workflow evaluates evidence, but merge acceptance is a human authority
boundary.

### Options

| Option | Description | Strengths | Costs / risks |
|---|---|---|---|
| A | Green checks imply merge-ready | Simple | Removes human authority; dangerous false readiness |
| B | Green checks produce `awaiting_human_decision` until recorded approval | Clear authority split | Requires one more decision artifact |
| C | Workflow may auto-approve low-risk PRs | Convenient later | Out of scope and risky for v0.2 |

### Recommendation

Use Option B.

### Rationale

The readiness workflow can say evidence is complete and no blockers are known.
It must not silently convert that into human merge approval. This also gives the
future PR acceptance run a clean gate.

### Human Acceptance Question

Is it accepted that no report may claim accepted merge readiness without a
recorded human merge decision?

## DDR-006: Failure Path Matrix Scope

### Problem

The workflow must test likely failure modes, not only happy-path report
generation.

### Options

| Option | Description | Strengths | Costs / risks |
|---|---|---|---|
| A | Happy path only | Minimal | Misses the actual PR-readiness risks |
| B | Generic broad risk list | Comprehensive-looking | Can become noisy and unfocused |
| C | Focused FPM from this workflow's risk surfaces | Testable and tied to authority/evidence risks | Requires maintaining scenario-to-test bindings |

### Recommendation

Use Option C.

### Rationale

The selected FPM covers false readiness, missing evidence, missing human
approval, mock/live Claude confusion, sensitive raw output, rejected blocker
triage, stale review and cyclic self-proof. These are the risks most likely to
make a PR gate misleading. The same FPM also shapes review specialization:
selected risk surfaces and failure paths are mapped into review topics and focus
zones, while every reviewer remains responsible for reporting plausible P0/P1
issues outside the assigned focus.

### Human Acceptance Question

Is the focused FPM accepted as the required red-capture target and
reviewer-specialization input for this slice?

## DDR-007: External Claude Evidence Policy

### Problem

Live Claude review is useful evidence, but raw external output can contain
sensitive local context. Mock smoke evidence must not be confused with live
review.

### Options

| Option | Description | Strengths | Costs / risks |
|---|---|---|---|
| A | Commit all raw Claude output | Maximum auditability | Sensitive leakage risk |
| B | Commit normalized report and invocation metadata; commit raw only when non-sensitive | Good auditability with redaction boundary | Requires explicit redaction reason/pointer |
| C | Store no live invocation evidence | Avoids leakage | Weak proof that live review occurred |
| D | Treat mock smoke as equivalent to live | CI-friendly | Misleading and procedurally wrong |

### Recommendation

Use Option B.

### Rationale

This preserves enough evidence to verify that live Claude was invoked and what
candidate findings were produced, while avoiding default raw-output commits.
The schema should distinguish mock, live, redacted and unavailable states.

### Human Acceptance Question

Is the Claude evidence policy accepted: normalized report and invocation
metadata always, raw output only when explicitly non-sensitive?

## DDR-008: Target Workflow Review Gate Topology

### Problem

Future `pr-merge-readiness` runs have different review concerns: verification
evidence, methodology architecture and adversarial authority failures. A single
generalist pair may miss important differences. This decision describes the
target workflow's PR-readiness review topology, not the BFCF development review
gate used to build the workflow.

### Options

| Option | Description | Strengths | Costs / risks |
|---|---|---|---|
| A | Homogeneous dual generalist review | Simple and already standard | Under-focused for PR/merge readiness |
| B | Heterogeneous review with one provider per topic | Focused | Provider disagreement is hard to interpret because topics differ |
| C | Provider-mirrored topic pairs: each topic reviewed by Codex and Claude | Focused plus model diversity on same questions | Six reports; more expensive and slower |
| D | Large unconstrained reviewer pool | Broad | Noisy; higher orchestration cost |

### Recommendation

Use Option C for PR/merge readiness.

### Rationale

Mirroring makes provider disagreement meaningful: Codex and Claude both inspect
verification/evidence, both inspect architecture/process and both inspect
adversarial/authority. Fusion can compare disagreements within each topic
instead of mixing unrelated review scopes. The gate uses the shared
review/fusion/finding-validation control block rather than duplicating local
rules: mechanical intake, canonical finding extraction,
duplicate/related/conflict grouping, topic-pair comparison, fusion report,
orchestrator relevance validation, collision-control for rejected or downgraded
P0/P1 candidates, and review-cycle decision. The block preserves authority
boundaries: deterministic automation validates structure and evidence, fusion
provides decision support, the orchestrator validates candidate findings, and
human-mediated gates remain human-owned.

This six-report gate is not automatically used to review the implementation of
`pr-merge-readiness` itself. The current BFCF development run uses a separate,
proportional development review gate after green verification: two generalists
(Codex and Claude when local Claude is available) plus one Codex
adversarial-authority specialist for the riskiest authority layer.

### Human Acceptance Question

Is the provider-mirrored heterogeneous gate accepted for future
`pr-merge-readiness` runs, despite the six-report cost?

## DDR-009: Allowed and Forbidden Change Boundaries

### Problem

The slice must not sprawl into adjacent systems.

### Options

| Option | Description | Strengths | Costs / risks |
|---|---|---|---|
| A | Broad edits wherever convenient | Flexible | Scope creep and methodology drift |
| B | Narrow workflow/schema/template/example/docs/validator paths | Controlled and reviewable | Some future improvements deferred |
| C | Split every adjacent issue into separate ADRs before implementation | Very controlled | Too slow for v0.2 closure |

### Recommendation

Use Option B.

### Rationale

The current target is a usable PR-readiness utility, not a redesign of
project-initialization, BFCF, provider wrappers or release automation. Narrow
paths reduce accidental methodology drift.

One approved exception is the minimal hardening of the existing reusable
review/fusion layer, so `pr-merge-readiness` can parameterize that block instead
of copying fusion and finding-validation rules into its own workflow.

### Human Acceptance Question

Are the allowed/forbidden path and behavior boundaries accepted for this slice?

## DDR-010: Field Names and Exact Validator Strictness

### Problem

The report schema needs concrete fields, and raw-output redaction needs exact
validation rules. Some details are best discovered by writing failing tests.

### Options

| Option | Description | Strengths | Costs / risks |
|---|---|---|---|
| A | Decide every field before red-capture | Precise | Can become abstract bikeshedding |
| B | Set semantic requirements now, derive exact fields through red-capture | Test-driven and pragmatic | Requires discipline during implementation |
| C | Leave fields mostly free-form | Flexible | Weak validator and poor interoperability |

### Recommendation

Use Option B.

### Rationale

The contract already fixes semantics: human decision required, evidence paths
validated, live/mock distinction, stale review exclusion, redaction reason. The
exact field names can be designed through failing tests without changing the
accepted behavior.

### Human Acceptance Question

Is it accepted that exact report field names and validator strictness are
nonblocking details to be fixed in red-capture tests before implementation?

## Aggregate Recommendation

Proceed to `red_capture` only if DDR-001 through DDR-009 are accepted. DDR-010
may remain delegated to red-capture as long as the semantic requirements above
remain binding.

## Evidence

- `human-decisions.yaml`
- `human-questions.yaml`
- `task.contract.md`
- `behavior.bindings.yaml`
- `impact-map.yaml`
- `plan.md`
- `plan-gate-report.md`

## Freshness / Revisit Triggers

- The branch gains material methodology changes after this packet.
- The report schema cannot express one of the accepted FPM paths.
- Live Claude invocation policy changes.
- Reviewers find a P0/P1 issue with the decision model.
- PR platform automation becomes an accepted v0.3 goal.

## Rollback / Migration Notes

Remove the utility workflow, schema/template/example, validator hooks and docs
updates. Historical run artifacts remain under `run-artifacts/agentsflow/runs/`
and do not become methodology source.
