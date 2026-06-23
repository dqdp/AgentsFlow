# Red Capture Gate Report

Status: fail-as-expected

## Purpose

Before implementation, the contract scenario "Calculator adds two integers" was
bound to `tests/test_minicalc.py::test_add` and run against the not-yet-satisfied
state.

## Captured Failure

| Instrument | Status | Evidence |
|---|---|---|
| unit_tests | fail-as-expected | `PYTHONPATH=src python3 -m pytest tests/test_minicalc.py::test_add` failed before `minicalc.add` existed. |
| behavior_binding_check | pass | `behavior.bindings.yaml` bound the required scenario to the failing test and verification gate. |

The post-implementation `verification-gate-report.md` re-runs the same bound
behavior and records the green result.
