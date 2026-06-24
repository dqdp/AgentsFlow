# ADR-0021: Review Observability and External Provider Evidence

## Status

Accepted.

Date: 2026-06-24

Decision provenance: accepted by the human-mediated Slice A planning and
decision discussion on 2026-06-24. Local run artifacts may record a normalized
decision log, but this ADR is the repository authority for the accepted rule.

## Context

AgentsFlow review gates are evidence-producing workflow controls. As soon as a
gate mixes internal and external reviewers, the run must distinguish several
different facts:

- whether the review packet was prepared;
- whether an external provider was configured and permitted to run;
- whether the external reviewer actually completed;
- how long the review phase and each reviewer invocation took;
- whether token or cost usage was reported by the provider;
- whether a failure happened before substantive review or during review.

A dogfood run exposed that these facts are easy to conflate. A provider
permission/config problem can look like a review-cycle problem unless the run
records preflight separately. Likewise, elapsed wall time, summed reviewer time
and provider-reported runtime are different measurements and should not be
collapsed into one informal duration.

## Decision

Review-enabled gates must produce review observability evidence. The target
run-level artifact is:

```text
review-metrics.json
```

This artifact is required for review-enabled gates once the corresponding
implementation slice introduces the schema/template/script support. Until then,
run artifacts may record the same information in structured review-cycle or
evidence reports.

The first implementation must be intentionally small. It should not become a
general telemetry subsystem.

Minimum first-slice scope:

- timestamps;
- elapsed wall-clock time versus summed reviewer/provider runtime;
- planned reviewer slots versus completed reviewer invocations;
- provider preflight/config blockers separated from substantive review cycles;
- token/cost availability and values only when provider-reported.

Richer provider telemetry, trend analysis, dashboards, or cross-run analytics
are out of scope unless a later concrete run need justifies them.

`review-metrics.json` records:

- review gate id, workflow, run id and material change id;
- planned reviewer slots and actual completed reviewer invocations;
- review cycle count, excluding provider preflight/config blockers;
- cycle timestamps and elapsed time;
- per-reviewer start, finish and elapsed time;
- external provider runtime when provider-reported;
- summed reviewer/provider runtime and wall-clock elapsed time separately;
- retry counts, timeout status, nonzero exits and normalization status;
- links to review packet, prompt contract, invocation metadata, normalized
  reviewer reports and finding-validation reports;
- provider usage, token and cost information when the provider exposes it.

Provider usage values must be provider-reported. AgentsFlow must not estimate
tokens or cost and present the estimate as evidence. When usage is unavailable,
the artifact records `available: false` and a reason.

Minimum timing fields:

```text
review_phase_started_at
review_phase_finished_at
review_phase_elapsed_ms
cycle_started_at
cycle_finished_at
cycle_elapsed_ms
reviewer_started_at
reviewer_finished_at
reviewer_elapsed_ms
provider_runtime_ms
summed_provider_runtime_ms
```

## External Provider Preflight

External provider preflight is separate from substantive review.

For a run that requires an external reviewer, the main/orchestrating agent or
project-bound wrapper performs:

1. a full deterministic preflight before the first external reviewer invocation
   in the run;
2. cheap cached fingerprint checks before later external review cycles in the
   same run.

The preflight fingerprint includes at least:

- provider config hash;
- wrapper hash;
- reviewer-report schema hash;
- prompt-contract hash;
- role/rubric hash;
- forbidden-environment fingerprint;
- permission/sandbox mode;
- provider transport mode.

For prepared external review gates, the preflight also records
`assignment_fingerprints[]`. Each Claude assignment fingerprint binds the
specific reviewer id to the provider config, wrapper, reviewer-report schema,
prompt contract, role contract, rubric, forbidden-environment fingerprint and
permission/sandbox/transport modes used by that assignment. A single generic
provider fingerprint is not enough evidence for a completed mixed-provider
gate.

A provider preflight/config failure is a config or evidence blocker. It is not:

- a reviewer finding;
- a substantive review cycle;
- a reason to silently fall back to internal-only review when the topology
  requires an external reviewer.

The full preflight must not add a slow live provider review call before every
external review cycle. A later cycle should rerun full preflight only when the
fingerprint changes or the previous preflight is stale for a recorded reason.
An unchanged fresh fingerprint uses the cheap check; it must not trigger a slow
live Claude call merely to prove the provider still exists.

## Raw Provider Output

Raw external reviewer output is evidence only when the provider config or run
policy explicitly classifies it as non-sensitive and preserveable.

Otherwise the run stores one of:

- redacted output;
- summary artifact;
- pointer to local operator-held output;
- omission reason.

The normalized reviewer report and invocation metadata remain required evidence
for a completed external reviewer assignment.

## Generation Boundary

Metrics should be script-generated or script-updated where possible from:

- `review-invocation-set.json`;
- reviewer invocation metadata;
- normalized reviewer reports;
- external reviewer preflight artifacts;
- finding-validation reports;
- review-cycle reports.

The main/orchestrating agent may add bounded judgment fields or notes, but
counts, timestamps, hashes, retry counts and provider usage should come from
structured evidence whenever available.

## Consequences

- Review gates become quantitatively comparable without requiring live provider
  calls in CI.
- Provider setup failures no longer inflate review-cycle counts.
- Token and cost reporting is honest about provider availability.
- The model leaves room for later schemas and generators without making Slice A
  a behavior-changing implementation.
- Local subscription/provider access remains project-bound and operator-owned.

## Non-Goals

- Do not implement a generic multi-provider reviewer runtime.
- Do not implement a general telemetry subsystem.
- Do not require live Claude review in CI.
- Do not estimate token or cost usage.
- Do not require full provider preflight before every review cycle when the
  cached fingerprint is unchanged.

## Follow-Up

Later slices should add the concrete schema/template and generator/update path
for `review-metrics.json`, then bind it into review-enabled gate evidence.
