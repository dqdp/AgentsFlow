# Review Gate Hardening Plan

Status: draft plan for review

Date: 2026-06-24

Source context: Bro TG-A Tools Gateway rerun against AgentsFlow `f02b6dc`.

## Purpose

This plan records the accepted direction for hardening AgentsFlow review gates
after the TG-A dogfood rerun. It prevents design drift before the work is split
into ADRs, amendments and implementation slices.

This is a planning artifact, not a new workflow rule by itself. The current
v0.2 supported application path remains:

```text
project-initialization.prepare-workflow -> big-feature-contract-first
```

## Goals

- Make review gates measurable through run-level metrics, timestamps and
  provider usage evidence.
- Separate external-provider configuration/preflight blockers from substantive
  review cycles.
- Preserve mixed-provider review without silent fallback when an external
  reviewer is required.
- Keep `homogeneous-plus-focused` useful for elevated-risk slices while
  enforcing same substantive prompt/packet/rubric for the baseline generalists.
- Clarify how important P2/P3 findings may be handled while a blocker loop is
  already open.
- Add a lightweight review-loop health checkpoint so repeated blockers lead to
  root-cause correction obligations instead of only local patching.

## Non-Goals

- Do not build a workflow runtime.
- Do not add a generic multi-provider reviewer platform.
- Do not require live Claude evidence in CI.
- Do not make old-vs-new run comparison a standard workflow artifact; that
  comparison is a methodology-development pattern, not ordinary workflow
  evidence.
- Do not use review-loop health as a cycle cap.
- Do not launch a new review gate only to create a health checkpoint.

## Anti-Overengineering Checks

Before accepting each work slice, apply these checks. If a proposed change fails
one of them, reduce the scope or record an explicit human decision explaining
why the extra mechanism is justified.

1. **Artifact necessity**
   - Does this new artifact answer a question that existing artifacts cannot
     answer clearly?
   - Can the same evidence be represented as a section in an existing artifact
     for the MVP?

2. **Validator boundary**
   - Is this rule deterministic enough for a validator?
   - If not, is it better recorded as agent protocol or human review guidance
     rather than schema/script enforcement?

3. **Runtime boundary**
   - Does this change keep AgentsFlow a workflow kit rather than a workflow
     runtime?
   - Does it avoid automatic orchestration, hidden phase transitions and hidden
     reviewer launches?

4. **Cost and latency**
   - Does this add a new provider call, reviewer launch or slow check?
   - If yes, can it be cached, made optional, or delayed until a material
     trigger fires?

5. **MVP shape**
   - Is there a smaller version that preserves the core safety property?
   - For health-check closure, prefer a section in the next review-fix-loop
     report before adding a standalone closure schema.

6. **Source-of-truth fit**
   - Does the decision belong in a new ADR, an amendment to an existing ADR, a
     profile/template, or only the planning note?
   - Avoid adding new ADRs for clarifications already owned by an accepted ADR.

7. **Observed-need test**
   - Is the mechanism motivated by a real failure or friction observed in a
     dogfood run, not only by speculative completeness?

8. **Human-in-the-loop proportionality**
   - Does the change add human review only where a real decision is required?
   - Avoid asking the human to approve routine mechanical artifacts.

## Complexity Risk Controls

These controls are accepted constraints for the review-gate hardening track.
They limit the slices below when a proposed implementation starts to look like a
workflow runtime or telemetry subsystem.

1. **Concrete-failure test**
   - Each new rule must map to a concrete failure or friction observed in Bro
     TG-A or an AgentsFlow dogfood run.
   - If the motivation is abstract completeness only, keep the rule as guidance
     instead of promoting it to a schema, validator or gate.

2. **Health checkpoint as exception**
   - A review-loop health checkpoint is created only when an accepted trigger
     fires.
   - It is not a standard phase in every review cycle.
   - If no trigger fires, no health-check artifact is required.

3. **Minimal metrics first**
   - The first `review-metrics.json` implementation must be the smallest useful
     generated artifact.
   - Minimum scope: timestamps, elapsed versus summed runtime, planned versus
     completed reviewers, preflight blockers separated from review cycles, and
     provider-reported token/cost availability.
   - Do not build a general telemetry subsystem in the first metrics slice.

4. **Preflight latency guard**
   - Full external-provider preflight runs once before the first required
     external reviewer invocation in a run.
   - Later external cycles use cheap fingerprint checks unless a recorded stale
     or changed fingerprint reason requires full preflight again.
   - Do not add a slow live Claude call before every external review cycle.

5. **Diagnostic reviewers are trigger-bound**
   - Fresh-context diagnostic reviewers are optional and never automatic.
   - Launch them only when root cause is unclear, disputed, or there is a
     concrete risk that the main agent is stuck in local patching or drifting
     from accepted scope/authority decisions.

6. **Schema deferral**
   - Slice A remains decision/docs-only.
   - New schemas or validators are added only in later implementation slices
     when the artifact shape is stable enough for deterministic validation.
   - Closure starts as a section in the review-cycle/report artifact; add a
     standalone closure schema only if validation needs prove it is necessary.

## Decision Structure

### New ADR: Review Observability And External Provider Evidence

This ADR should cover the evidence/telemetry side of review gates:

- `review-metrics.json` is required for review-enabled gates.
- Review metrics record timestamps, durations, cycle counts, planned reviewer
  slots, actual provider invocations, normalized reports, retries and failures.
- Token/cost usage is recorded when a provider exposes it.
- When usage is unavailable, the artifact records `available: false` with a
  reason instead of estimating.
- External reviewer preflight has two modes:
  - full deterministic preflight once before the first external reviewer
    invocation in a run;
  - cheap cached fingerprint check before later external cycles.
- The fingerprint includes provider config hash, wrapper hash, schema hash,
  prompt-contract hash, role/rubric hash, forbidden-env fingerprint and
  permission/sandbox mode.
- A provider preflight/config blocker is not a substantive review cycle and is
  not a reviewer finding.
- Full preflight must not add a slow live provider review call before every
  cycle.

### New ADR: Review Loop Health Check

This ADR should cover the new workflow-control concept:

- Trigger policy uses `any` / `OR`, not `all` / `AND`.
- A health checkpoint is required when any trigger fires:
  - 3 consecutive review cycles have validated P0/P1 blockers or mandatory
    evidence gaps;
  - the same validated risk surface repeats in 2 cycles;
  - stale or false-green evidence blockers repeat.
- The checkpoint is owned by the main/orchestrating agent by default.
- It is not a new review gate and does not launch reviewers by default.
- Optional fresh-context diagnostic reviewers are used only when root-cause
  classification is unclear, disputed, or risks scope/authority drift.
- The checkpoint records root-cause classification and correction obligations.
- Health-check risk-surface matching uses the run's selected surface set from
  `risk_surface_profile.selected_risk_surfaces` plus declared project-local
  surfaces, not arbitrary reviewer wording. Main-agent finding validation maps
  candidate findings to those selected surface ids, or records an unmapped/new
  surface as a possible contract/update decision.
- A closure artifact is required before the next review gate after a triggered
  checkpoint.
- The next review packet includes the checkpoint and closure artifact so
  reviewers can inspect whether the repeated class of problem was actually
  addressed.

### Amendment: ADR-0016 External Reviewer Provider Interface

ADR-0016 already defines the external reviewer provider boundary. Amend it
instead of creating another provider ADR.

Clarifications:

- Claude Code external reviewers must use project-bound wrappers.
- Claude Code reviewers require `sandbox_mode: require_escalated`.
- API-key/proxy routes remain forbidden.
- If an external reviewer is required by the review topology, provider
  unavailability or config/preflight failure blocks the workflow; it must not
  silently fall back to internal-only review.
- Raw provider output retention must be classified as non-sensitive, redacted,
  or replaced by a pointer/summary with the reason.
- Provider usage, token and cost evidence must be normalized when exposed by the
  provider.

### Amendment: ADR-0003 And Review Topology Docs

`homogeneous-plus-focused` already exists in profiles. It should be clarified
as a first-class elevated-risk topology rather than replaced.

Clarifications:

- The homogeneous baseline pair may use different providers.
- Baseline generalists must receive the same substantive prompt, same packet,
  same rubric and same output schema.
- Provider transport metadata may differ.
- Focused reviewers receive the same full review packet and diff plus an
  explicit focus zone.
- Focus zones may overlap and must not prevent reporting plausible P0/P1
  blockers outside the focus.
- Artifact preparation should record equality evidence for the baseline
  generalist prompts/packets/rubrics.

### Amendment: ADR-0007 Review Findings Require Relevance Validation

ADR-0007 already owns candidate finding validation. Amend it to clarify the
finding lifecycle inside review-fix loops.

Clarifications:

- Candidate findings remain non-authoritative until main-agent validation.
- Validated P0/P1 findings and mandatory evidence gaps block acceptance.
- Important P2/P3 findings may be fixed while a validated blocker loop is
  already open.
- P2/P3-only findings do not trigger a review rerun unless the fix materially
  changes contract, schema, validator behavior, mandatory evidence,
  verification result, project overlay, workflow policy or current evidence
  examples.
- The main agent records accepted, fixed, deferred and rejected P2/P3 rationale.

## Open Clarifications Before Slice A

Resolve these clarifications before drafting the ADRs and amendments in Slice A.

### Health triggers count validated findings only

Health-check triggers are computed from main-agent validated findings and
mandatory evidence gaps, not raw reviewer candidates.

- Candidate P0/P1 findings do not trigger a health checkpoint by themselves.
- Mandatory evidence gaps count only after the main/orchestrating agent accepts
  them as blocking or mandatory for the current review gate.
- Rejected, duplicate or downgraded findings do not count unless the validation
  record keeps a grounded blocker/evidence-gap path open.

### Repeated risk surface uses canonical selected surfaces

Repeated-surface detection uses canonical risk-surface ids selected for the run.

Canonical sources:

- `risk_surface_profile.selected_risk_surfaces`;
- declared project-local surfaces from the project overlay or project operating
  decisions;
- Failure Path Matrix rows that reference selected surfaces.

Reviewer wording is not a source of truth. Finding validation maps a candidate
finding to a canonical selected `risk_surface_id`. If a finding does not map to
an existing selected surface, validation records it as an
`unmapped_or_new_surface_candidate` and decides whether the task contract or
project-local surface policy needs an update.

### Review metrics should be generated where possible

`review-metrics.json` should be script-generated or script-updated where
possible, not hand-written narrative evidence.

Primary inputs:

- `review-invocation-set.json`;
- reviewer invocation metadata;
- normalized reviewer reports;
- external reviewer preflight artifacts;
- finding-validation reports;
- review-cycle reports.

The main agent may add bounded judgment fields or notes when needed, but counts,
timestamps, hashes, retry counts and provider usage should come from structured
evidence whenever available.

### Time fields distinguish elapsed and summed runtime

Metrics must not collapse parallel wall-clock time and summed invocation time.

Minimum timing concepts:

- `cycle_started_at`;
- `cycle_finished_at`;
- `cycle_elapsed_ms`;
- `reviewer_elapsed_ms`;
- `provider_runtime_ms`;
- `summed_provider_runtime_ms`;
- `review_phase_elapsed_ms`.

`elapsed` means the wall-clock interval. `summed` means the sum of individual
invocation runtimes. They answer different questions and must be reported
separately.

### Token and cost usage is provider-reported only

Token and cost metrics are recorded only when the provider or runner exposes
them. AgentsFlow must not estimate usage.

Allowed states:

- `available: true` when provider-reported usage is present;
- `available: false` with a reason when usage is unavailable;
- `redacted: true` when policy permits only partial usage retention.

Token and cost usage is evidence for observability and tradeoff analysis; it is
not an acceptance gate by itself.

### Closure starts minimal

The first health-check implementation should keep closure lightweight.

MVP closure may be a dedicated section in the next review-fix-loop report. A
separate `review-loop-health-closure.json` should be added only when mechanical
validator enforcement needs a standalone closure artifact.

### Health checkpoint does not replace phase-transition control

Review-loop health is local to the review-fix loop.

It does not:

- compute the next workflow phase;
- replace ADR-0018 phase transition control;
- launch gates, tests or reviewers;
- mutate `phase_guard`;
- become a review-cycle cap.

It only records repeated-blocker diagnosis and correction obligations that must
be considered before the next review gate.

## Execution Methodology For This Track

This hardening track should be developed through AgentsFlow self-application,
but without pretending that not-yet-implemented rules already exist.

Use the current AgentsFlow methodology as the governing process for this work.
Do not start a new `project-initialization` run for AgentsFlow itself; the
repository already has source-of-truth docs, ADRs, profiles, schemas,
validators, examples and next-slice planning. Use `big-feature-contract-first`
with an operating-context preflight for this track.

Recommended branch and run shape:

- create a fresh branch for Slice A, for example
  `codex/review-gate-hardening-slice-a`;
- start a new self-application BFCF run, for example
  `2026-06-24-review-gate-hardening-slice-a`;
- treat this plan as design input for the run, not as authority above accepted
  ADRs;
- keep run artifacts separate from methodology-source files;
- do not use previous dogfood run artifacts as implementation authority except
  as motivating evidence and comparison context.

Recommended run structure:

- one parent planning/design run may hold the track-level scope, accepted
  decisions and sequencing;
- Slice A may live in that parent run because it is decision-layer
  documentation only;
- larger behavior-changing slices such as review metrics, external preflight
  and health-check validation should use their own BFCF implementation runs.

Slice A scope:

- add the two new ADRs described above;
- amend ADR-0016, ADR-0003/topology docs and ADR-0007;
- add or update a checkpoint linking the work to the TG-A dogfood lessons;
- do not change schemas, validators, scripts or examples except for
  source-of-truth references needed by the decision layer.

Slice A verification:

- run repository validation;
- run targeted documentation/source-of-truth consistency checks when available;
- do not require Red Capture for Slice A because it does not change executable
  schema/script behavior;
- do not require `review-metrics.json`, external preflight cache or
  review-loop health artifacts for Slice A, because those mechanisms are not
  implemented yet.

Later implementation slices:

- Slice B/C/F and any other behavior-changing schema/script slices should use
  full BFCF red-capture, implementation, green-verification and review framing;
- review topology for higher-risk implementation slices should use
  `homogeneous-plus-focused` when the selected risk surfaces justify it;
- external Claude review should use the currently implemented wrapper/provider
  rules until the new preflight/cache mechanism is implemented.

## Work Slices

### Slice A: Pre-Implementation Decision Layer

Scope:

- Add the two new ADRs.
- Patch ADR-0016, ADR-0003/topology docs and ADR-0007.
- Add a checkpoint note linking this work to the TG-A dogfood lessons.

Workflow interpretation:

- In `big-feature-contract-first`, this slice is part of the
  pre-implementation contract/design/human-decision work.
- It is not an implementation phase and should not be treated as Red Capture ->
  implementation -> Green Verification work.
- It produces methodology-source decisions that later implementation slices will
  execute.

Exit evidence:

- ADRs and amendments are reviewed for source-of-truth consistency.
- No schema or script behavior changes are included in this slice.

### Slice B: Review Metrics

Scope:

- Add `schemas/review-metrics.schema.json`.
- Add `templates/review-metrics.json`.
- Add validation for review metrics artifacts.
- Update review/evidence templates and example run artifacts.
- Start with the minimum generated metrics artifact: timestamps, elapsed versus
  summed runtime, planned versus completed reviewers, preflight blockers
  separated from substantive review cycles, and token/cost availability when
  provider-reported.
- Defer richer per-provider telemetry until a concrete run need proves it is
  necessary.

Expected metrics distinctions:

- review-gate family;
- review cycle;
- planned reviewer slot;
- actual provider invocation;
- normalized reviewer report;
- retry;
- preflight/config blocker.

### Slice C: External Reviewer Preflight Evidence

Scope:

- Add `schemas/external-reviewer-preflight.schema.json`.
- Add `templates/external-reviewer-preflight.json`.
- Extend the external reviewer wrapper or review-set preparation flow to write
  full preflight once per run.
- Add cached fingerprint evidence for later cycles.
- Add invocation-set or review-metrics references to the preflight evidence.
- Validate provider blocker versus review cycle distinction.

Constraints:

- Do not add a live Claude review/preflight call before every cycle.
- Do not permit internal-only fallback when external review is required.
- Do not repeat full preflight when the cached fingerprint is unchanged and
  still fresh.

### Slice D: Topology And Prompt Equality Hardening

Scope:

- Update `profiles/review_topologies/homogeneous-plus-focused.yaml`.
- Update `profiles/review_profiles/homogeneous-plus-focused.yaml`.
- Extend artifact preparation evidence for baseline same-prompt/same-packet/
  same-rubric checks.
- Update mixed-provider examples, especially Codex generalist + Claude
  generalist + adversarial Codex.

Exit evidence:

- Baseline generalist equality is machine-checkable or at least hash-recorded in
  artifact preparation evidence.
- Provider-specific metadata differences are allowed but bounded.

### Slice E: Finding Lifecycle Policy

Scope:

- Update `schemas/review-cycle.schema.json`.
- Update `templates/review-cycle-report.md`.
- Update `workflows/big-feature-contract-first/README.md` and workflow policy
  where needed.
- Add examples for important P2/P3 fixed during blocker loops and P2/P3-only
  no-rerun decisions.

Exit evidence:

- Review-cycle artifacts can record why P2/P3 were fixed, deferred or rejected.
- Rerun policy distinguishes material evidence changes from non-material
  editorial cleanup.

### Slice F: Review-Loop Health Check

Scope:

- Start with a minimal checkpoint section/template tied to the review-cycle or
  review-fix-loop report.
- Add `schemas/review-loop-health-check.schema.json` only if the checkpoint
  shape proves stable enough for deterministic validation.
- Add a human-readable template if useful.
- Add `review-loop-health-closure` schema/template only if the closure shape
  needs separate validation.
- Add validator coverage: if trigger evidence exists, the health checkpoint must
  exist.
- Add review packet requirements after a triggered checkpoint: include the
  checkpoint and closure artifact.

Exit evidence:

- Trigger policy is `OR`.
- The checkpoint is main-agent owned.
- Optional diagnostic reviewers are not launched by default.
- Correction obligations are traceable to closure evidence before the next
  review gate.

## Validation Plan

For each implementation slice:

```bash
.venv/bin/python scripts/validate_repo.py --root .
.venv/bin/python -m pytest -q
```

For external reviewer changes, also run the CI-safe mock smoke test:

```bash
.venv/bin/python scripts/reviewers/run_external_reviewer.py \
  --provider claude-code \
  --config examples/external-reviewers/claude-code/claude-code.yaml \
  --input examples/external-reviewers/claude-code/review-packet.architecture.json \
  --mock-response examples/external-reviewers/claude-code/mock-raw-output.json \
  --output /tmp/reviewer-report.claude-architecture.json
```

## Recommended Order

1. Slice A: decision layer.
2. Slice B: `review-metrics.json`.
3. Slice C: external reviewer preflight evidence.
4. Slice D: topology and prompt equality hardening.
5. Slice E: finding lifecycle policy.
6. Slice F: review-loop health checkpoint.

The review metrics slice comes before the health-check slice because metrics and
timestamps provide the substrate for later loop diagnostics.
