# Skill: pr-merge-readiness

## Purpose

Assemble a pull-request readiness report from already-produced verification,
review-gate, finding-validation, external-provider and human-decision evidence.

This skill guides the main agent. It is not the acceptance authority. The
deterministic readiness evaluator decides the computed readiness state from the
report and referenced artifacts.

## Inputs

- branch, base branch and intended commit range;
- worktree state;
- deterministic verification evidence;
- required review-gate evidence, including review packets and reviewer reports
  produced by the source workflow, project binding or explicit review gate;
- hash-bound review requirements source artifact produced by the source
  workflow, project binding or explicit review gate;
- external reviewer invocation metadata when external review is required;
- finding-validation report and collision-control evidence when applicable;
- human merge decision record when accepted merge-ready status is claimed;
- optional GitHub publication evidence when publication is claimed.

## Outputs

- `pr-merge-readiness-report.json`;
- evidence reference list for the deterministic evaluator;
- unresolved blocker or missing-evidence summary.

## Procedure

1. Record branch identity, base branch, commit range, worktree state, run id and
   material change id.
2. Reference existing deterministic checks and verification evidence. Do not run
   tests or verification from this skill.
3. Reference existing required review-gate evidence. Do not launch reviewers,
   choose review topology, run fusion or validate findings from this skill. If
   required review evidence is missing, record a missing-evidence state instead
   of treating the PR as ready.
4. Bind `review_requirements.required_reviews` to its source artifact by path and
   SHA-256 hash.
5. Record external reviewer evidence, including live-vs-mock status and
   invocation metadata, when an external-backed review is required.
6. Reference finding-validation and collision-control evidence for accepted,
   rejected, downgraded or duplicate blocker-path findings.
7. Reference the human merge decision only when it is human-authored,
   confirmed, and bound to the current material change and readiness report
   hash.
8. Mark missing, stale or blocked evidence explicitly instead of inferring
   success.
9. Run the deterministic readiness evaluator through repository validation with
   the concrete report path:
   `python3 scripts/validate_repo.py --root . --pr-merge-readiness-report <path>`.

## Authority Boundary

- The skill may assemble and summarize evidence.
- The skill must not accept a PR by judgment alone.
- The deterministic evaluator computes accepted, awaiting-human, blocked or
  incomplete readiness states.
- Review agents and external providers produce candidate findings only.
- Accepted merge-ready status requires fresh required review-gate evidence.

## Anti-Patterns

- Launching a fresh review gate from this skill.
- Duplicating review topology or reviewer assignment policy in the readiness
  report when the source workflow or project binding already owns it.
- Treating green tests plus reviewer approval as accepted merge-ready without a
  hash-bound human decision.
- Treating green tests without required review-gate evidence as merge-ready.
- Treating mock external reviewer evidence as live provider evidence.
