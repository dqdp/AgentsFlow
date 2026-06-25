# ADR-0021: Review Observability and External Provider Evidence

## Status

Proposed.

Date: 2026-06-25

## Context

AgentsFlow review gates produce acceptance evidence. Dogfood work showed that a
mixed internal/external review gate needs to distinguish facts that are easy to
blur together:

- whether review artifacts were prepared;
- whether an external provider was configured and permitted to run;
- whether the external reviewer actually completed;
- how long the review phase and each reviewer invocation took;
- whether token or cost usage was reported by the provider;
- whether a failure happened before substantive review or during review.

Without this split, a provider permission/configuration problem can look like a
review-cycle problem, and elapsed wall time can be confused with summed reviewer
runtime.

## Decision

AgentsFlow should add small review observability evidence for review-enabled
gates. The target run-level artifact name is:

```text
review-metrics.json
```

The first implementation must be intentionally small. It must not become a
general telemetry subsystem.

Minimum first-slice scope:

- timestamps;
- elapsed wall-clock time versus summed reviewer/provider runtime;
- planned reviewer slots versus completed reviewer invocations;
- provider preflight/config blockers separated from substantive review cycles;
- token/cost availability and values only when provider-reported.

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
project-bound wrapper should perform:

1. a deterministic preflight before the first external reviewer invocation in
   the run;
2. cheap cached fingerprint checks before later external review cycles in the
   same run.

The preflight fingerprint should include at least:

- provider config hash;
- wrapper hash;
- reviewer-report schema hash;
- prompt-contract hash;
- role/rubric hash;
- forbidden-environment fingerprint;
- permission/sandbox mode;
- provider transport mode.

A provider preflight/config failure is a config or evidence blocker. It is not:

- a reviewer finding;
- a substantive review cycle;
- a reason to silently fall back to internal-only review when the topology
  requires an external reviewer.

Full preflight must not add a slow live provider review call before every
external review cycle. A later cycle should rerun full preflight only when the
fingerprint changes or the previous preflight is stale for a recorded reason.

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

Metrics should be script-generated or script-updated where possible from
existing evidence such as:

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
- The first implementation can start with a small schema/template/generator
  rather than a telemetry subsystem.

## Non-Goals

- Do not implement a generic multi-provider reviewer runtime.
- Do not implement dashboards or cross-run analytics.
- Do not require live Claude review in CI.
- Do not estimate token or cost usage.
- Do not require full provider preflight before every review cycle when the
  cached fingerprint is unchanged.

## Implementation Guidance

Do not promote `review-metrics.json` to mandatory evidence for every review gate
until a small generator/template path exists and validation can check the
artifact without requiring live external providers.
