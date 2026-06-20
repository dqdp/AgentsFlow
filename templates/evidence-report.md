# Evidence Report: <task-or-feature-name>

Status: <pass|pass-with-notes|needs-changes|blocked>
Contract: `<path/to/contract.md>`
Workflow: `<workflow-name>`
Effective Strictness: `<workflow-default-or-explicit-override>`
Material Change ID: `<latest-material-change-id-or-none>`
Latest Green Gate: `<path-or-id>`

## Summary

What changed and why.

## Changed Files

- `path/to/file`: reason

## Scenario Coverage

| Scenario | Risk surface | Path class | Evidence | Status |
|---|---|---|---|---|
| Scenario name | `audit_persistence` | `denied_attempt_persisted` | test/script/review evidence | pass/fail/skip |

## Failure Path Matrix Coverage

| FPM ID | Risk surface | Path class | Evidence binding | Status | Notes |
|---|---|---|---|---|---|
| FPM-001 | `audit_persistence` | `denied_attempt_persisted` | `AF-BHV-...` / gate check | pass/fail/skip/deferred |  |

## Verification Commands

```bash
# command
```

Result: pass/fail/skip

Structured command evidence:

```yaml
command:
cwd:
started_at:
finished_at:
exit_code:
result: pass
output_summary:
artifact_paths: []
raw_log_path: null
```

## Evidence Freshness

| Item | Value |
|---|---|
| Latest material change id |  |
| Material change summary |  |
| Green verification after latest material change | yes/no |
| Review packet generated after latest green evidence | yes/no/not-applicable |
| Stale evidence excluded or marked | yes/no |

## Boundary Check

- Allowed paths respected: yes/no
- Forbidden paths touched: yes/no
- Notes: ...

## Impact Map

- Affected modules: ...
- Required tests: ...
- Tests run: ...
- Gaps: ...

## Review Results

| Reviewer or stage | Result | Notes |
|---|---|---|
| reviewer-or-stage-id | pass/needs-changes/not-run | ... |

## Known Limitations

- ...

## Follow-up Items

- ...
