# Verification Gate Report

See also: `templates/gate-report.md`. This file is the default gate-report specialization for implementation workflows.

## Gate

- Name:
- Workflow:
- Strictness profile:
- Review topology:

## Inputs

- Contract:
- Diff/artifact:
- Impact map:
- Domain pack:

## Checks executed by gate

| Check | Command / mechanism | Required | Result | Notes |
|---|---|---:|---|---|
| Contract lint |  | yes/no | pass/fail/skip |  |
| Gherkin lint |  | yes/no | pass/fail/skip |  |
| Boundary check |  | yes/no | pass/fail/skip |  |
| Impact map check |  | yes/no | pass/fail/skip |  |
| Unit tests |  | yes/no | pass/fail/skip |  |
| Integration tests |  | yes/no | pass/fail/skip |  |
| Architecture checks |  | yes/no | pass/fail/skip |  |
| Evidence validation |  | yes/no | pass/fail/skip |  |

## Evidence bundle

- Test logs:
- Script outputs:
- Changed files:
- Coverage notes:
- Skipped checks with justification:

## Gate result

Choose one:

- `pass`
- `pass_with_notes`
- `fail`
- `needs_human_decision`
- `blocked`

## Handoff to review agents

Review agents may inspect this report and the evidence bundle. They must not run
additional tests/scripts or modify artifacts. Missing verification must be reported
as a finding.
