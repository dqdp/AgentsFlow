# Script Contract

A script is deterministic automation.

Each script should have:

```text
scripts/<script-name>.py
scripts/contracts/<script-name>.yaml
```

## Requirements

Scripts should:

- be deterministic;
- be suitable for CI;
- return non-zero exit codes on failure;
- produce clear text or JSON-like evidence;
- avoid hidden model calls;
- avoid changing files unless explicitly designed as a formatter/generator.

## Manifest fields

```yaml
name: boundary_check
type: script
version: 0.1
entrypoint: scripts/boundary_check.py
inputs:
  - contract_path
  - changed_files
outputs:
  - pass_fail
  - violations
  - evidence_json
deterministic: true
ci_compatible: true
```

## Current scripts

| Script | Purpose |
|---|---|
| `contract_lint.py` | Checks that a task contract has required sections. |
| `gherkin_lint.py` | Detects missing Given/When/Then and vague assertions. |
| `boundary_check.py` | Checks changed files against allowed/forbidden path prefixes in a contract. |
| `impact_map_check.py` | Checks that an impact map has required fields. |
| `evidence_validate.py` | Checks that an evidence report has required sections. |

These scripts are intentionally simple in v0.1. They are scaffolding for design review.
