# Workflow Phase Schema

## Purpose

Workflow phases describe the ordered protocol of a workflow. `Phase` is not a
new top-level AgentsFlow abstraction; it is a structural element inside
`workflow.yaml`.

A phase should declare its id/name, kind, coordinator or actor role, inputs,
outputs, used skills/scripts/templates, and preconditions.

## Minimal phase shape

```yaml
- id: repository_grounding
  kind: planning
  mode: human_guided
  coordinator: main-agent
  reserved_optional_actors:
    - planning-agent
  uses:
    skills:
      - repository-grounding
  outputs:
    - repository-grounding-report.md
```

## Phase kinds

Recommended v0.2 phase kinds:

```text
intake
planning
specification
research
decision
gate
implementation
verification
review
finding_validation
fusion
reporting
```

The exact set may be simplified per workflow. The important property is that
phase order and permissions remain explicit.

## Planning phases

Current planning phases are human-guided by default:

```yaml
kind: planning
mode: human_guided
coordinator: main-agent
reserved_optional_actors:
  - planning-agent
```

Planning Agent remains a reserved optional role. The default workflow behavior is
human + main/orchestrating-agent collaboration.

## Verification phases

Verification phases declare a concrete gate manifest and instruments instead of assuming only tests/scripts. A gate/verification phase must include `gate:`:

```yaml
- id: verification_gate
  kind: verification
  gate: verification_gate
  actor_class: verification_gate
  owns_evidence_production: true
  instruments:
    - type: tests
      command: pytest
    - type: static_analysis
      command: ruff check .
    - type: dynamic_analysis
      command: sanitizer run
    - type: deterministic_script
      command: python3 scripts/boundary_check.py
  outputs:
    - verification-gate-report.md
    - evidence-bundle
```

## Review phases

Review phases are read-only by default and consume evidence rather than produce
it by running verification:

```yaml
- id: review
  kind: review
  actor_class: review_agent
  runs_after:
    - verification_gate
  default_permissions:
    read: true
    write: false
    run_tests: false
    run_verification_instruments: false
    run_tools: false
  explicit_tool_exceptions_allowed: true
  outputs:
    - reviewer-report.md
```

If a reviewer receives a tool exception, it must be declared explicitly in the
workflow, reviewer manifest, or reviewer prompt. The result remains a candidate
finding, not authoritative verification evidence.

## Fusion phases

Fusion phases synthesize. They do not orchestrate by default:

```yaml
- id: fusion
  kind: fusion
  actor_class: fusion_agent
  role: synthesis
  may_launch_reviewers: false
  may_run_gates: false
  may_request_additional_review: true
  inputs:
    - reviewer reports
    - finding validation report
    - verification gate report
    - evidence bundle
  outputs:
    - fusion-report.md
```

## Required invariants

Validators and reviewers should enforce these invariants:

- review phases that review implementation must run after a verification gate;
- review agents must not run verification instruments unless explicitly allowed,
  and such exceptions do not turn review into verification;
- review findings must pass relevance validation before they become accepted issues;
- fusion must not erase validated blockers or candidate blockers by majority vote;
- fusion must not launch reviewers/gates by default;
- implementation must respect required plan/contract gates when the workflow declares them;
- a phase of `kind: implementation` must normally be framed by a preceding red-capture phase (executable tests authored from the contract, run against the not-yet-implemented state, failing run captured) and a following green-verify phase (same tests re-run, passing run captured) — ADR-0017; refactor-only implementation may use `test_framing: baseline_capture` before `change_type: refactor` because the pre-change behavior-preservation baseline is expected to pass rather than fail;
- external planning-provider outputs must be normalized into AgentsFlow artifacts.

## Gate executability

Every phase with `kind: gate` or `kind: verification`, and every phase whose id is a
concrete `*_gate`, must reference a gate manifest:

```yaml
- id: verification_gate
  kind: verification
  gate: verification_gate
```

The referenced gate must exist under `gates/<gate-id>.yaml` and must declare a
runner entrypoint. BDD/prose specifications can inform a gate, but they cannot
replace the runner.
