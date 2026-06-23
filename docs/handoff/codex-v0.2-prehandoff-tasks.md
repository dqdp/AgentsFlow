# Codex Handoff: v0.2 Pre-Handoff Fix List (Task 0, Historical)

Status: **historical/completed pre-handoff fix list**
Produced by: independent read-only design review of v0.1.13
Date: 2026-06-17

Current status: this document is retained as historical design-review handoff
evidence. The Task 0 implementation has been superseded by the accepted v0.2
source-of-truth docs, checkpoints, validators, schemas and examples. Do not use
this document as the active task list for new v0.2 work; use the README
suggested review path and `docs/plans/v0.2-next-slices.md` for current planning.

## Purpose

This document was the self-contained first task ("Task 0") for the coding agent
(Codex) before v0.2 MVP implementation proper. It captured every blocker and
consistency issue found in the v0.1.13 pre-handoff design review. All design
decisions below were already made for that historical slice.

After this task list was applied and the validation in the final section passed,
the repository moved from `needs-fixes-before-codex` toward the v0.2 readiness
track.

## Prime directive

```text
Do not expand scope. Implement the accepted decisions below. Make AgentsFlow
usable for the v0.2 MVP path.
```

Do not introduce any non-goal listed in `AGENTS.md` (no CLI/package
distribution, no multi-provider runtime, no API-key Claude usage, no
implementation-agent runtime, no UI/DB/cloud). Every task here stays inside the
accepted MVP freeze.

## Source of truth (read before changing design)

1. `docs/checkpoints/checkpoint-2026-06-17-v0.1.13.md`
2. `docs/adr/ADR-0001..0016`
3. `AGENTS.md`
4. `docs/mvp-ready-workflow-standard.md`
5. Model docs: `project-application-model`, `project-initialization-model`,
   `gate-executability-model`, `behavior-binding-model`, `review-control-model`,
   `review-agent-interaction-protocol`, `external-reviewer-provider-model`,
   `legacy-agent-system-adoption-model`.

## Frozen decisions (do not re-litigate)

- DoD "X is represented" means **Doc + Instance + Wired**: a model doc in
  `docs/`, a concrete artifact instance (schema + template + at least one
  `examples/` instance), and a reference from at least one MVP `workflow.yaml`
  or project binding.
- Python dependencies are declared in `pyproject.toml`
  `[project.optional-dependencies].dev`; the interpreter is unified to `python3`.
- DoD criterion "Claude external reviewer provider minimally works" is verified
  by the **mock smoke test** (no live Claude call required). Live invocation is
  an optional manual check only.
- Non-MVP workflows (`agentic-system-hardening`, `prompt-behavior-eval`,
  `safe-refactor`, `research-to-ADR`) stay reference/experimental: schema-valid
  and labeled `post-v0.2-reference` only. Do not deepen them.

---

## Open design decisions (decide before building the hard layer)

These are NOT tasks for Codex to "just implement". They are conceptual gaps that
writing more code will NOT close, because the hard part is non-deterministic.
The plan stage is the right time to choose an answer. Each is OPEN until a human
decides. Until then, Codex must not silently pick one.

Context: AgentsFlow's three boldest claims — non-averaging fusion, main-agent
relevance validation, and "no ambiguous coexistence" — are currently written as
*policy an agent should follow*, not as *mechanism that enforces it*. Most of that
gap is ordinary implementation work. The three decisions below are the part that
implementation alone cannot resolve.

### ODD-1 — Who checks the validator? (DECIDED)

**Problem.** The review system routes final authority to one "main / orchestrating
agent" that decides which findings are real. That agent is the same class of
fallible LLM the system is meant to discipline. If it labels a P0/P1
"rejected-irrelevant", nothing checks whether that judgment is correct.

**Constraint.** The workflow must run automatically at runtime; humans are involved
only at design/planning time. No live human prompts during a run. A run may still
*end* in a `needs-human-decision` state for later asynchronous review — that is a
terminal result state, not a live stop.

**Why code won't fix it.** No deterministic script can decide whether a rejection
reason is correct. The trust problem can be mitigated, not removed.

**Superseded update.** The accepted v0.2 control rule is now the two-reviewer
collision-control batch defined by `AGENTS.md`, `docs/review-profile-model.md`
and `profiles/review_profiles/collision-control.yaml`. The older one-advocate
wording below is retained only as historical rationale.

**Decision — the relevance check is a short side-branch with a definitive verdict, not a loop:**

The extra agent fires only when the main orchestrator *rejects an already-found
blocker as irrelevant* — not on every finding, and not as a fix/re-review cycle.
Rejection is rare (most blockers are fixed, and ungrounded findings are dropped
cheaply), so the same rule applies to P0 and P1 alike — no severity split.

- **Two control reviewers, once, batched.** All blocker-level findings the
  orchestrator rejected or downgraded in a cycle go to one collision batch and
  are reviewed by two fresh-context control reviewers. There are no per-finding
  agents and no loop.
- **Control outputs remain candidate input.** The two control reviewers do not
  drop or reinstate findings by authority. They provide focused candidate
  findings on the collision batch; the main/orchestrating agent records the final
  relevance-validation decision. If the collision still requires changing an
  accepted decision, the run ends `needs-human-decision`.
- **Missing mandatory evidence** still blocks (unchanged).

This relevance side-branch is separate from the broader fix→re-review loop. It runs
once and resolves; it does NOT use `max_review_cycles`.

**Concrete hole this closes:** today `do_not_rerun_on:
irrelevant_findings_rejected_with_reason` lets a rejection silently end the review
with the finding dropped. A rejected or downgraded P0/P1 must instead pass
through the two-control-reviewer collision batch before it can be dropped.

**Status:** DECIDED.

### ODD-2 — Can the kit tell a real binding from a fake one? (DECIDED)

**Problem.** A required scenario (e.g. "must reject invalid input") can be bound to
a check that always passes. Every schema is satisfied; the green checkmark proves
nothing. The kit validates that a binding *exists and has the right shape*, not
that the bound check actually exercises the scenario. Context: the Gherkin scenario
is the plain-language requirement (top layer); the bound test is the code-level
proof; nothing guarantees the test matches the sentence.

**Why code won't fix it (fully).** Structural validation only sees shape. Whether a
check genuinely tests its scenario is not deterministically decidable in general.

**Decision (two layers, no human in the loop):**
- **A — always-on deterministic floor.** For required (P0/P1) behavior scenarios
  bound to test-type checks, "fail-first" (red→green) is mandatory: the evidence
  bundle must contain a recorded **failing** run (on the broken/unimplemented state)
  and a **passing** run (on the final state). A deterministic script enforces
  "red→green pair present" — it does not judge test quality, only that the check
  ever actually failed. This kills the always-green fake. (Now realized structurally
  by ODD-5 / ADR-0017: the red→green pair is a byproduct of the test-framed
  implementation phase, and this deterministic script is its enforcement. The "no
  fix without captured regression" rule it generalizes lives in
  `docs/mvp-ready-workflow-standard.md`, realized by bugfix's `regression_gate`.)
- **B — not a new component; already part of review, made explicit.** The
  verification / adversarial reviewers already inspect test adequacy, weakened
  tests, missing regression cases, and false completion. Make it explicit in their
  spec that they must check a bound test actually exercises its scenario (matches
  the Gherkin intent), not merely that it exists. No separate "binding-quality
  agent" is added; the responsibility stays inside the existing read-only reviewers
  and remains a candidate finding.
- **C — rejected.** Deferring fake-binding detection to a human at runtime breaks
  the automation goal (no live human in a run). Not used.

Together: A catches dead/always-green tests (deterministic, every required
scenario); B catches alive-but-wrong-target tests (reviewer judgment). Both failure
modes covered with no human in the loop.

**Honest limit:** A proves a test has teeth, not that it bites the right thing; B is
model judgment and can be fooled. Neither is a 100% guarantee — but together they
close the cheap, common fakes, which is the point.

**Status:** DECIDED.

### ODD-3 — Lightweight path & who selects altitude (DECIDED)

**Premise corrected.** The earlier framing ("~13 artifacts even for a tiny change")
was wrong. Ceremony already scales: lightweight workflows + real
`profiles/strictness/L0..L4.yaml` + `profiles/review_topologies/none.yaml`. A small
fix uses `bugfix-regression-capture` at L1 with topology `none` ≈ 3 artifacts
(reproduction note, regression scenario, fix evidence), no review panel. The
~13-artifact load is specific to `big-feature-contract-first` at high strictness,
not to all changes. **The lightweight path already exists.**

**Superseded direction — see ADR-0019.** The human still confirms workflow choice
and material risk exceptions, but strictness is no longer a routine task-setup
selection. The workflow declares `default_strictness`; a project binding or run
records `strictness` only as an explicit override with a reason. Review topology
remains an explicit workflow/binding policy.

**Small follow-up (Codex cleanup, not a design decision):** `L0.yaml` exists but is
not listed in any workflow's `supported_profiles` (workflows start at L1). Either
wire L0 into the light workflows or confirm L1 is the practical floor and document
it.

**Status:** DECIDED.

### ODD-4 — Review-cycle policy (DECIDED)

**Context.** `max_review_cycles` caps how many times the broader fix→re-review loop
may repeat. Today it is `integer, minimum: 1` in
`schemas/review-cycle.schema.json`, set per-workflow (1 for light, 2 for
implementation), with a prose-only default (2/1) in the protocol — and read by NO
code yet.

**Key reframing.** `max_review_cycles` is a runaway *safety ceiling*, not the
expected number of rounds. A healthy run exits earlier on its own when no validated
blocking findings remain; the ceiling only catches non-convergence. Because fixes
can introduce new problems and reviewers miss findings on the first pass,
legitimate convergence may take several rounds — a tight cap would cut off a healthy
run.

**Decision:**
- Schema: `max_review_cycles` → optional, `minimum: 3` when present, **no default**
  and **no maximum**. Absence means no cycle-count cap.
- `minimum: 3` constrains the configured *ceiling value*, NOT the number of cycles
  executed. A run whose first review is clean exits after a **single pass**; one
  cycle is a normal outcome. The ceiling is only an upper bound that healthy runs
  rarely reach.
- Natural exit stays the primary terminator: stop when no validated blocking
  findings remain (`no_validated_blocking_findings`), at whatever cycle count
  (including 1).
- Hitting the ceiling without convergence → run ends `needs-human-decision`, never a
  silent pass.
- **Progress-based early stop — this is what makes an unbounded ceiling safe:** stop
  early and escalate to human when the loop is thrashing rather than converging
  (validated-blocker count not trending down, the same blocker oscillating, or a fix
  re-breaking something previously fixed). Healthy "slow but converging" runs
  continue; stuck runs stop early without burning cycles.
- When the orchestrator is built it must read `max_review_cycles` only when the
  project policy or workflow binding provides it. If absent, review cycles are not
  limited by count; progress-based human escalation still prevents thrashing.

**Superseded consequence:** concrete numeric ceilings may live in project policy
or workflow bindings, not upstream workflow definitions. Upstream workflows must
not require a concrete value. Bindings/policies use minimum 3 only when they set
the cap; omission means no cycle-count cap.

**Status:** DECIDED.

### ODD-5 — Test-framed implementation phase (DECIDED)

**Decision.** Red-before / green-after is a **phase-topology rule**, not a scattered
convention. Any workflow with a `kind: implementation` phase must frame it:

```
[ contract → executable tests → run, capture RED ]  →  [ implementation ]  →  [ re-run same tests → GREEN ]
```

The red→green evidence pair is a byproduct of this structure. Enforced structurally
by `validate_repo.py` / the workflow schema (reject an `implementation` phase that
is not framed by the two phases), mirroring the existing "gate phase must declare a
manifest" check.

**Why it exists.** The red step was implicit and only half-present (bugfix-only, via
`reproduce` / `regression_gate`); `big-feature-contract-first` had no red-capture
before implementation. Full rationale + alternatives in
`docs/adr/ADR-0017-test-framed-implementation-phase.md`.

**Bricks.**
- Rule + rationale: ADR-0017 (done) + a section in `behavior-binding-model.md`.
- Structural check: `validate_repo.py` + `schemas/workflow-phase.schema.json` /
  `schemas/workflow.schema.json`.
- Missing phase: add the pre-implementation red-capture phase to
  `big-feature-contract-first/workflow.yaml` (bugfix already conforms).
- Evidence: `failing_run` / `passing_run` fields (shared with ODD-2 layer A's
  `redgreen_check`).
- CONTENTS.md: add the ADR-0017 line.

**Relation to ODD-2.** ODD-5 is the rule; ODD-2 layer A's deterministic red→green
check is its *enforcement* (the topology produces the pair, the script confirms it
was recorded). ODD-2 layer B (reviewer judges test-vs-scenario) stays separate.

**Status:** DECIDED.

---

## Tasks

### T1 — [P1] Declare dependencies, add install step, unify on python3

**Finding:** CLD-DR-001 · Category: handoff-readiness

**Why:** The first two DoD criteria ("repository validation passes; tests pass")
cannot be reproduced from a clean clone. `pyproject.toml` declares no
dependencies, yet 6 scripts `import yaml`; tests need `pytest`. `Makefile` and
`README.md` call `python`, which is absent on the target machine (only `python3`).

**Files:**
- `pyproject.toml`
- `Makefile`
- `README.md`
- `AGENTS.md` (see T7)

**Do:**
1. Add to `pyproject.toml`:
   ```toml
   [project.optional-dependencies]
   dev = ["PyYAML", "pytest"]
   ```
   Add `jsonschema` to this list **only if** T5 wires real schema validation.
2. Replace `python` with `python3` in `Makefile` targets, or document a required
   `python` alias. Prefer `python3`.
3. Add an install step to `README.md` Quick validation: `pip install -e ".[dev]"`
   before the validate/pytest commands.

**Acceptance:**
- From a clean clone: `pip install -e ".[dev]"` then `python3 scripts/validate_repo.py --root .` and `python3 -m pytest -q` both succeed.
- No `python ` (without `3`) invocation remains in `Makefile` or example scripts,
  or the required alias is documented.

---

### T2 — [P2] Record the operational DoD bar in the MVP standard

**Finding:** CLD-DR-002 · Category: mvp-scope

**Why:** Several DoD items ("represented", "coherent", "usable") are not
machine-checkable and were a hidden design decision.

**Files:** `docs/mvp-ready-workflow-standard.md`

**Do:** Add a short "DoD interpretation" subsection encoding the frozen bar:
`represented` = Doc + Instance + Wired; `project-initialization path is coherent`
= every `project-initialization/workflow.yaml` output has a template or is marked
deferred; `Claude provider minimally works` = mock smoke test passes;
`AGENTS.md usable` = contains source-of-truth order + explicit v0.2 scope +
scope-expansion prohibition + validation commands + accepted-decision pointers.

**Acceptance:** The subsection exists and each soft DoD bullet maps to a concrete
check.

---

### T3 — [P2] Reconcile behavior-binding schema with checker and model

**Finding:** CLD-DR-007 · Category: behavior-binding · **Decision: Option A (loosen schema)**

**Why:** `schemas/behavior-binding.schema.json` requires `checks` minItems:1 and
`gates` minItems:1 for **every** binding, but `scripts/bdd_binding_check.py` only
requires them when `required: true`, and `docs/behavior-binding-model.md` allows
`required: false / status: specification-only` to be unbound. A spec-only binding
with empty checks passes the checker but fails the schema — contradictory verdicts.

**Files:** `schemas/behavior-binding.schema.json`

**Do:** Make `checks`/`gates` mandatory only when `required: true` (e.g. JSON
Schema `if`/`then`: when `required` is `true`, apply `minItems: 1`; otherwise
allow `minItems: 0`). Keep the checker as-is (it already matches model intent).

**Acceptance:**
- A spec-only binding (`required: false`, empty `checks`/`gates`) passes **both**
  `bdd_binding_check.py` and JSON-schema validation.
- A `required: true` binding with empty `checks` still fails both.
- Add such a spec-only scenario to one example binding so the path is exercised.

---

### T4 — [P2] Broaden the forbidden-env baseline for the Claude provider

**Finding:** CLD-DR-010 · Category: external-reviewer · **Decision: Option A (expand)**

**Why:** The forbidden-env list contains only `ANTHROPIC_API_KEY`. The policy
intent is "no API billing, subscription-local only", but Claude Code can route
through Bedrock/Vertex/proxy/auth-token while `ANTHROPIC_API_KEY` is absent.

**Files:**
- `examples/external-reviewers/claude-code/claude-code.yaml`
- `docs/external-reviewer-provider-model.md` (document the recommended minimum)

**Do:**
1. Extend `billing.fail_if_env_present` to include at least:
   `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`,
   `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`.
2. Document this set as the recommended minimum baseline in the provider model.
3. Optional hardening: in `scripts/reviewers/providers/claude_code.py`, run the
   subprocess with a scrubbed/allowlisted env instead of inheriting the full
   parent env. Keep this optional and minimal.

**Note:** `scripts/reviewers/run_external_reviewer.py` already hard-requires
`ANTHROPIC_API_KEY` to be in the list (`validate_provider_config`) and enforces
the env check before invocation (including in mock mode). Do not weaken that.

**Acceptance:** `enforce_billing_policy` fails fast when any of the listed vars is
present; the example config lists the expanded set; the provider model documents it.

---

### T5 — [P2] Make the provider's schema-validation promise true

**Finding:** CLD-DR-011 · Category: external-reviewer

**Why:** `claude-code.yaml` sets `normalization.require_schema_validation: true`
and points to `schemas/reviewer-report.schema.json`, but
`run_external_reviewer.py` only does hand-rolled structural checks and never
validates against the schema file (no `jsonschema` use).

**Files:**
- `scripts/reviewers/run_external_reviewer.py`
- (if validating) `pyproject.toml` dev deps (add `jsonschema` — see T1)
- or `examples/external-reviewers/claude-code/claude-code.yaml` + provider model

**Do:** Choose one and make config and code agree:
- **Option A:** wire real validation of the normalized report against
  `schemas/reviewer-report.schema.json` (add `jsonschema` to dev deps), keeping
  the existing structural invariants (all findings `candidate-unvalidated`).
- **Option B:** relax the config/model wording to "structural validation" and
  drop the false promise.

Prefer Option A if it stays minimal.

**Acceptance:** The behavior described by `require_schema_validation` matches what
the code actually does; the mock smoke test still passes.

---

### T6 — [P2] Fix the verification-gate anti-pattern in the canonical e2e

**Finding:** CLD-DR-013 · Category: gate-model · **Decision: Option A (runner executes both instruments)**

**Why:** This is the primary teaching example, and it currently models exactly
the anti-pattern `gate-executability-model.md` forbids. The project-bound
`verification_gate.yaml` declares two instruments (`unit_tests`,
`behavior_binding_check`), but `run_verification_gate.sh` runs only
`pytest tests`, while `verification-gate-report.md` claims
`behavior_binding_check: pass`.

**Files:**
- `examples/e2e/minimal-python-project/.agentsflow/scripts/run_verification_gate.sh`
- `examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/verification-gate-report.md`

**Do:**
1. Make the runner execute **both** declared instruments: `pytest tests` and the
   `bdd_binding_check.py` invocation from the gate manifest (against the run's
   `behavior.bindings.yaml`). Use `python3`.
2. Ensure the gate report references evidence the runner actually produced.

**Acceptance:** Running `run_verification_gate.sh` executes both instruments; the
report's claimed evidence corresponds to real runner output. (If the example
keeps `.agentsflow/upstream/` uninstalled per the known illustrative limit, point
the bdd check at the repo-root `scripts/bdd_binding_check.py` so it is runnable.)

---

### T7 — [P2] Add a Validation section to AGENTS.md

**Finding:** CLD-DR-014 · Category: handoff-readiness

**Why:** `AGENTS.md` is the coding-agent handoff doc but contains no concrete
validation/test commands; they live only in `README.md`, which the AGENTS.md
source-of-truth list does not even point to.

**Files:** `AGENTS.md`

**Do:** Add a "Validation" section:
```bash
pip install -e ".[dev]"
python3 scripts/validate_repo.py --root .
python3 -m pytest -q
# external reviewer wrapper smoke test (no live Claude call):
python3 scripts/reviewers/run_external_reviewer.py \
  --provider claude-code \
  --config examples/external-reviewers/claude-code/claude-code.yaml \
  --input examples/external-reviewers/claude-code/review-packet.architecture.json \
  --mock-response examples/external-reviewers/claude-code/mock-raw-output.json \
  --output /tmp/reviewer-report.claude-architecture.json
```

**Acceptance:** `AGENTS.md` contains runnable validation/test commands using
`python3`.

---

### T8 — [P3] Polish batch

Low-risk, no design decisions. Apply all:

- **CLD-DR-003** (`docs/specification-development-roadmap.md`): add one line
  noting `new-project-spec-first` is reference/next in v0.2, not a supported
  target workflow; this roadmap is the later deep-research track.
- **CLD-DR-004** (`examples/e2e/minimal-python-project/.agentsflow/`): pick one
  concrete `upstream_mode` (e.g. `git-submodule`) in `project.yaml` and add a
  minimal `agentsflow.lock.yaml` from `templates/agentsflow.lock.yaml`.
- **CLD-DR-005** (`workflows/project-initialization/workflow.yaml` /
  `templates/`): either add a minimal `templates/documentation-history-index.md`
  or mark the `documentation-history-index.md` output optional/deferred.
- **CLD-DR-006** (`schemas/legacy-adoption-decision.schema.json`): make the
  safety invariants required sub-fields — `legacy_handling.no_ambiguous_coexistence`,
  `legacy_handling.final_authority_layer_required`, `legacy_handling.backup_required`,
  `human_approval.required`, `human_approval.status`; require a `justification`
  field when `adoption_mode == minimal-patch-adapt` (keep it the rare/strict mode).
- **CLD-DR-008** (`docs/gate-executability-model.md` or
  `docs/behavior-binding-model.md`): add a mapping table between gate instrument
  types and behavior-binding check types (e.g. `tests` ↔ `test`,
  `deterministic_script` ↔ `script`), or unify the vocabularies.
- **CLD-DR-009** (`docs/review-fusion-model.md`): add `needs-verification-evidence`
  to the result-states list, or reference the protocol as the single source.
- **CLD-DR-012** (`scripts/reviewers/run_external_reviewer.py`): remove the
  always-false `api_key_env_detected` field from invocation metadata, or replace
  it with a verified-policy constant.
- **CLD-DR-015** (`AGENTS.md`): add a pointer to README's "Suggested review path"
  or a short list of model docs + the e2e example in the source-of-truth section.

**Acceptance:** Each item applied; `validate_repo.py` and `pytest` still pass.

---

## Final validation (Task 0 done = ready-for-codex)

Task 0 is complete when, from a clean clone:

```bash
pip install -e ".[dev]"
python3 scripts/validate_repo.py --root .
python3 -m pytest -q
python3 scripts/bdd_binding_check.py --bindings examples/memory-policy/Docs/contracts/memory-policy.bindings.yaml
# e2e gate runner executes both instruments:
( cd examples/e2e/minimal-python-project && bash .agentsflow/scripts/run_verification_gate.sh )
# external reviewer mock smoke test passes (see AGENTS.md Validation section)
```

All commands succeed, and:

- behavior-binding schema and `bdd_binding_check.py` agree on specification-only
  bindings (T3);
- the Claude provider config and code agree on schema validation (T5) and the
  expanded forbidden-env baseline is in place (T4);
- the e2e gate report only claims evidence its runner produced (T6);
- `AGENTS.md` carries the validation commands (T7);
- non-MVP workflows remain `post-v0.2-reference` and schema-valid only.

## Finding-to-task index

| Finding | Severity | Task |
|---|---|---|
| CLD-DR-001 | P1 | T1 |
| CLD-DR-002 | P2 | T2 |
| CLD-DR-007 | P2 | T3 |
| CLD-DR-010 | P2 | T4 |
| CLD-DR-011 | P2 | T5 |
| CLD-DR-013 | P2 | T6 |
| CLD-DR-014 | P2 | T7 |
| CLD-DR-003 | P3 | T8 |
| CLD-DR-004 | P3 | T8 |
| CLD-DR-005 | P3 | T8 |
| CLD-DR-006 | P3 | T8 |
| CLD-DR-008 | P3 | T8 |
| CLD-DR-009 | P3 | T8 |
| CLD-DR-012 | P3 | T8 |
| CLD-DR-015 | P3 | T8 |
