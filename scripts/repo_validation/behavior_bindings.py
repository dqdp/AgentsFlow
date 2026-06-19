from __future__ import annotations

from pathlib import Path

from .common import parse_yaml


VALID_BINDING_CHECK_TYPES = {
    'test', 'script', 'bdd_runner', 'eval', 'trace_assertion', 'log_assertion',
    'static_analysis', 'dynamic_analysis', 'benchmark', 'security_scan',
    'manual_evidence', 'external_tool',
}


def validate_behavior_binding(path: Path) -> list[str]:
    errors: list[str] = []
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"{path}: behavior binding is not a mapping"]
    for key in ["version", "contract", "bindings"]:
        if key not in data:
            errors.append(f"{path}: missing required field {key}")
    bindings = data.get("bindings", []) or []
    if not isinstance(bindings, list):
        return errors + [f"{path}: bindings must be a list"]
    seen: set[str] = set()
    for idx, item in enumerate(bindings):
        if not isinstance(item, dict):
            errors.append(f"{path}: binding #{idx} must be a mapping")
            continue
        bid = str(item.get("id", f"#{idx}"))
        if bid in seen:
            errors.append(f"{path}: duplicate binding id {bid}")
        seen.add(bid)
        for key in ["id", "scenario", "required", "checks", "gates"]:
            if key not in item:
                errors.append(f"{path}: binding {bid} missing {key}")
        if item.get("required") is True and not item.get("checks"):
            errors.append(f"{path}: required binding {bid} has no checks")
        if item.get("required") is True and not item.get("gates"):
            errors.append(f"{path}: required binding {bid} has no gates")
        for check in item.get("checks", []) or []:
            if not isinstance(check, dict):
                errors.append(f"{path}: binding {bid} check must be a mapping")
                continue
            ctype = check.get("type")
            if ctype not in VALID_BINDING_CHECK_TYPES:
                errors.append(f"{path}: binding {bid} has unknown check type {ctype}")
            if ctype != "manual_evidence" and not (check.get("command") or check.get("target")):
                errors.append(f"{path}: binding {bid} check {check.get('id')} lacks command/target")
    return errors


def validate_behavior_binding_gate_refs(path: Path, known_gates: set[str]) -> list[str]:
    errors: list[str] = []
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return errors
    for item in data.get("bindings", []) or []:
        if not isinstance(item, dict):
            continue
        bid = item.get("id", "<unknown>")
        for gate in item.get("gates", []) or []:
            if isinstance(gate, dict):
                gate_id = gate.get("id") or gate.get("gate")
            else:
                gate_id = gate
            if gate_id and str(gate_id) not in known_gates:
                errors.append(f"{path}: binding {bid} references unknown gate: {gate_id}")
    return errors

