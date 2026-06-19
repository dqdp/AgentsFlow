from __future__ import annotations

from pathlib import Path

from .common import parse_yaml, safe_resolve


VALID_GATE_INSTRUMENT_TYPES = {
    'tests',
    'deterministic_script',
    'bdd_runner',
    'static_analysis',
    'dynamic_analysis',
    'debugger',
    'trace_analysis',
    'log_analysis',
    'network_traffic_analysis',
    'profiler',
    'fuzzer',
    'benchmark',
    'security_scanner',
    'domain_tool',
    'manual_evidence_check',
    'schema_validation',
    'fusion_protocol_check',
    'review_protocol_check',
}

TARGET_WORKFLOW_DECISION_CATEGORIES = {
    "scope",
    "adr",
    "risk",
    "contract",
    "gate",
    "review",
    "evidence",
    "authority",
    "workflow-design",
}


def validate_gate_manifest(root: Path, path: Path, data: dict | None = None) -> list[str]:
    errors: list[str] = []
    data = data if data is not None else parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"Gate {path} is not a mapping"]
    required = ["id", "name", "kind", "purpose", "runner", "inputs", "instruments", "outputs", "result_states", "pass_policy"]
    for key in required:
        if key not in data:
            errors.append(f"{path}: missing required gate field: {key}")
    if data.get("kind") != "gate":
        errors.append(f"{path}: kind must be 'gate'")
    runner = data.get("runner")
    if runner:
        runner_path = root / str(runner)
        if not runner_path.exists():
            errors.append(f"{path}: generic runner path does not exist: {runner}")
    if data.get("binding_level") and data.get("binding_level") != "upstream_gate_contract":
        errors.append(f"{path}: upstream gates should use binding_level=upstream_gate_contract")
    instruments = data.get("instruments", []) or []
    if not isinstance(instruments, list) or not instruments:
        errors.append(f"{path}: instruments must be a non-empty list")
    else:
        for idx, inst in enumerate(instruments):
            if not isinstance(inst, dict):
                errors.append(f"{path}: instrument #{idx} is not a mapping")
                continue
            if "id" not in inst or "type" not in inst:
                errors.append(f"{path}: instrument #{idx} must include id and type")
    pass_policy = data.get("pass_policy", {}) or {}
    pass_policy_map = pass_policy if isinstance(pass_policy, dict) else {}
    if isinstance(pass_policy, dict):
        for key in ["fail_on", "inconclusive_on"]:
            if key not in pass_policy:
                errors.append(f"{path}: pass_policy missing {key}")
    else:
        errors.append(f"{path}: pass_policy must be a mapping")
    if data.get("id") in {"project_initialization_gate", "target_workflow_readiness_gate"}:
        gate_id = str(data.get("id"))
        inputs = set(str(item) for item in data.get("inputs", []) or [])
        if "project-documentation-disposition.yaml" not in inputs:
            errors.append(
                f"{path}: {gate_id} inputs must include project-documentation-disposition.yaml"
            )
        required_evidence = set(str(item) for item in data.get("required_evidence", []) or [])
        if not any("project-documentation-disposition.yaml" in item for item in required_evidence):
            errors.append(
                f"{path}: {gate_id} required_evidence must include project-documentation-disposition.yaml"
            )
        if gate_id == "target_workflow_readiness_gate":
            decision_categories = set(str(item) for item in data.get("decision_categories", []) or [])
            missing_categories = sorted(TARGET_WORKFLOW_DECISION_CATEGORIES - decision_categories)
            if missing_categories:
                errors.append(
                    f"{path}: target_workflow_readiness_gate decision_categories missing: {', '.join(missing_categories)}"
                )
            if not any("existing project policy/workflow binding evidence" in item for item in inputs):
                errors.append(
                    f"{path}: target_workflow_readiness_gate inputs must allow existing project policy/workflow binding evidence"
                )
            if not any("target workflow preflight findings" in item for item in inputs):
                errors.append(
                    f"{path}: target_workflow_readiness_gate inputs must allow target workflow preflight findings"
                )
            if not any("human decision packet" in item for item in inputs):
                errors.append(
                    f"{path}: target_workflow_readiness_gate inputs must allow human decision packet"
                )
            if not any("existing project policy/workflow binding evidence" in item for item in required_evidence):
                errors.append(
                    f"{path}: target_workflow_readiness_gate required_evidence must include existing project policy/workflow binding evidence or preflight findings"
                )
            if not any("human decision packet" in item for item in required_evidence):
                errors.append(
                    f"{path}: target_workflow_readiness_gate required_evidence must include human decision packet"
                )
            needs_human_decision_on = set(str(item) for item in pass_policy_map.get("needs_human_decision_on", []) or [])
            if "unresolved_material_design_decision" not in needs_human_decision_on:
                errors.append(
                    f"{path}: target_workflow_readiness_gate must block unresolved material design decisions"
                )
    return errors


def validate_project_gate_manifest(
    path: Path,
    project_root: Path,
    binding_extends: object,
    binding_runner: object,
) -> list[str]:
    errors: list[str] = []
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"{path}: project gate manifest must be a mapping"]
    for key in ["extends", "runner", "instruments", "outputs"]:
        if key not in data:
            errors.append(f"{path}: project gate manifest missing {key}")
    if data.get("runner") != binding_runner:
        errors.append(f"{path}: runner must match workflow binding runner")
    if data.get("extends") not in {binding_extends, f".agentsflow/upstream/{binding_extends}"}:
        errors.append(f"{path}: extends must match workflow binding gate extends")
    runner_path = safe_resolve(project_root, data.get("runner"), f"{path}: runner", errors)
    if runner_path and not runner_path.exists():
        errors.append(f"{path}: runner does not exist: {data.get('runner')}")
    instruments = data.get("instruments", []) or []
    if not isinstance(instruments, list) or not instruments:
        errors.append(f"{path}: project gate manifest instruments must be a non-empty list")
    else:
        for idx, instrument in enumerate(instruments):
            if not isinstance(instrument, dict):
                errors.append(f"{path}: instrument #{idx} must be a mapping")
                continue
            if not instrument.get("id") or not instrument.get("type"):
                errors.append(f"{path}: instrument #{idx} must include id and type")
            instrument_type = instrument.get("type")
            if instrument_type not in VALID_GATE_INSTRUMENT_TYPES:
                errors.append(f"{path}: instrument {instrument.get('id')} has unknown type {instrument_type}")
            if instrument_type in {"tests", "deterministic_script"} and not instrument.get("command"):
                errors.append(f"{path}: instrument {instrument.get('id')} must include command")
    return errors


STRICTNESS_OVERRIDE_SOURCES = {"project_override", "task_override", "legacy_selected"}


def supported_workflow_strictness(workflow: dict) -> set[str]:
    return {str(item) for item in ((workflow.get("supported_profiles") or {}).get("strictness") or [])}


def validate_binding_strictness_policy(path: Path, binding: dict, workflow: dict) -> tuple[list[str], object]:
    errors: list[str] = []
    local_strictness = binding.get("strictness")
    source = binding.get("strictness_source")
    reason = binding.get("strictness_override_reason")
    supported = supported_workflow_strictness(workflow)
    default = workflow.get("default_strictness")

    if default is not None and supported and str(default) not in supported:
        errors.append(f"{path}: workflow default_strictness {default} is not listed in supported_profiles.strictness")

    override_valid = False
    if local_strictness is not None:
        if not supported:
            errors.append(
                f"{path}: local strictness override requires upstream workflow "
                "supported_profiles.strictness"
            )
        if source not in STRICTNESS_OVERRIDE_SOURCES:
            errors.append(
                f"{path}: local strictness requires strictness_source "
                "project_override, task_override, or legacy_selected"
            )
        if not reason:
            errors.append(f"{path}: local strictness requires strictness_override_reason")
        if supported and str(local_strictness) not in supported:
            errors.append(
                f"{path}: strictness {local_strictness} is not supported by upstream workflow "
                f"{workflow.get('name', binding.get('workflow'))}"
            )
        override_valid = bool(
            source in STRICTNESS_OVERRIDE_SOURCES
            and reason
            and supported
            and str(local_strictness) in supported
        )

    return errors, local_strictness if override_valid else None


def effective_strictness(workflow: dict, selected_strictness: object) -> object:
    if selected_strictness is not None:
        return selected_strictness
    return workflow.get("default_strictness")


def required_workflow_gates(workflow_path: Path, selected_strictness: object) -> set[str]:
    if not workflow_path.exists():
        return set()
    data = parse_yaml(workflow_path) or {}
    if not isinstance(data, dict):
        return set()
    selected_strictness = effective_strictness(data, selected_strictness)
    gates: set[str] = set()
    for phase in data.get("phases", []) or []:
        if not isinstance(phase, dict) or not phase.get("gate"):
            continue
        applies = phase.get("applies_to_strictness")
        if not applies:
            gates.add(str(phase["gate"]))
            continue
        if str(selected_strictness) in {str(item) for item in applies or []}:
            gates.add(str(phase["gate"]))
    return gates
