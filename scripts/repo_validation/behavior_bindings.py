from __future__ import annotations

from pathlib import Path

from .common import parse_yaml


VALID_BINDING_CHECK_TYPES = {
    'test', 'script', 'bdd_runner', 'eval', 'trace_assertion', 'log_assertion',
    'static_analysis', 'dynamic_analysis', 'benchmark', 'security_scan',
    'manual_evidence', 'external_tool',
}


def _contract_scenarios(contract_path: Path) -> set[str]:
    try:
        lines = contract_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    scenarios: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Scenario:"):
            scenario = stripped.split("Scenario:", 1)[1].strip()
            if scenario:
                scenarios.add(scenario)
    return scenarios


def _allows_placeholder_contract_refs(path: Path) -> bool:
    return path.name == "behavior-bindings.yaml" and path.parent.name == "templates"


def _is_placeholder_contract_ref(path: Path, contract_ref: object) -> bool:
    text = str(contract_ref)
    return _allows_placeholder_contract_refs(path) and (text == "task.contract.md" or ("<" in text and ">" in text))


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
    default_contract = data.get("contract")
    default_contract_scenarios: set[str] | None = None
    if default_contract and not _allows_placeholder_contract_refs(path):
        default_contract_path = path.parent / str(default_contract)
        if default_contract_path.is_file():
            default_contract_scenarios = _contract_scenarios(default_contract_path)
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
        scenario = item.get("scenario")
        source = item.get("source") or {}
        source_path = source.get("path") if isinstance(source, dict) else None
        source_scenarios = default_contract_scenarios
        if source_path and source_path != default_contract:
            source_contract_path = path.parent / str(source_path)
            if source_contract_path.is_file():
                source_scenarios = _contract_scenarios(source_contract_path)
            elif item.get("required") is True and not _is_placeholder_contract_ref(path, source_path):
                errors.append(f"{path}: binding {bid} source contract file does not exist: {source_path}")
        elif (
            item.get("required") is True
            and default_contract
            and default_contract_scenarios is None
            and not _is_placeholder_contract_ref(path, default_contract)
        ):
            errors.append(f"{path}: binding {bid} contract file does not exist: {default_contract}")
        if item.get("required") is True and isinstance(scenario, str) and source_scenarios is not None and scenario not in source_scenarios:
            errors.append(f"{path}: binding {bid} scenario is not declared in contract: {scenario}")
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
