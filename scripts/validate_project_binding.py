#!/usr/bin/env python3
"""Validate a project overlay that binds AgentsFlow upstream workflows/gates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import jsonschema
import yaml

from repo_validation.review import validate_enabled_review_minimum

VALID_GATE_INSTRUMENT_TYPES = {
    "tests",
    "deterministic_script",
    "bdd_runner",
    "static_analysis",
    "dynamic_analysis",
    "debugger",
    "trace_analysis",
    "log_analysis",
    "network_traffic_analysis",
    "profiler",
    "fuzzer",
    "benchmark",
    "security_scanner",
    "domain_tool",
    "manual_evidence_check",
    "schema_validation",
    "fusion_protocol_check",
    "review_protocol_check",
}


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def schema_error_path(error: jsonschema.ValidationError) -> str:
    parts = [str(part) for part in error.absolute_path]
    return ".".join(parts) if parts else "<root>"


def validate_schema(path: Path, data: dict, schema: dict) -> list[str]:
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"{path}: schema error at {schema_error_path(error)}: {error.message}"
        for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    ]


def safe_resolve(base: Path, ref: object, label: str, errors: list[str]) -> Path | None:
    if not ref:
        return None
    ref_path = Path(str(ref))
    if ref_path.is_absolute() or ".." in ref_path.parts:
        errors.append(f"{label} must be a relative non-escaping path: {ref}")
        return None
    resolved_base = base.resolve()
    resolved = (base / ref_path).resolve()
    try:
        resolved.relative_to(resolved_base)
    except ValueError:
        errors.append(f"{label} escapes expected root: {ref}")
        return None
    return resolved


def collect_reviewer_roles(agentsflow_root: Path) -> set[str]:
    roles: set[str] = set()
    for path in (agentsflow_root / "profiles" / "reviewer_roles").glob("*.yaml"):
        data = load_yaml(path)
        roles.add(str(data.get("name", path.stem)))
    return roles


def collect_review_topologies(agentsflow_root: Path) -> set[str]:
    topologies: set[str] = set()
    for path in (agentsflow_root / "profiles" / "review_topologies").glob("*.yaml"):
        data = load_yaml(path)
        if data.get("deprecated") is not True:
            topologies.add(str(data.get("name", path.stem)))
    return topologies


def validate_review_policy(
    path: Path,
    review: object,
    topologies: set[str],
    reviewer_roles: set[str],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(review, dict) or not review:
        return errors
    topology = review.get("topology")
    if not topology or topology == "none":
        return errors
    if topology not in topologies:
        errors.append(f"{path}: review.topology unknown: {topology}")
    if topology == "single-reviewer" or topology == "collision-control":
        errors.append(f"{path}: review.topology {topology} is not valid for primary project bindings")
    errors.extend(validate_enabled_review_minimum(path, review, "review", reviewer_roles))
    return errors


def validate_review_cycle_policy(path: Path, review_cycle: object) -> list[str]:
    errors: list[str] = []
    if review_cycle is None:
        return errors
    if not isinstance(review_cycle, dict):
        errors.append(f"{path}: review_cycle must be a mapping")
        return errors
    max_review_cycles = review_cycle.get("max_review_cycles")
    if max_review_cycles is None:
        return errors
    if not isinstance(max_review_cycles, int):
        errors.append(f"{path}: review_cycle.max_review_cycles must be an integer")
    elif max_review_cycles < 3:
        errors.append(f"{path}: review_cycle.max_review_cycles must be at least 3")
    return errors


def validate_project_gate_manifest(
    path: Path,
    project_root: Path,
    binding_extends: object,
    binding_runner: object,
) -> list[str]:
    errors: list[str] = []
    data = load_yaml(path)
    for key in ["extends", "runner", "instruments", "outputs"]:
        if key not in data:
            errors.append(f"{path}: project gate manifest missing {key}")
    manifest_runner = data.get("runner")
    if manifest_runner != binding_runner:
        errors.append(f"{path}: runner must match workflow binding runner")
    manifest_extends = data.get("extends")
    if manifest_extends not in {binding_extends, f".agentsflow/upstream/{binding_extends}"}:
        errors.append(f"{path}: extends must match workflow binding gate extends")
    runner_path = safe_resolve(project_root, manifest_runner, f"{path}: runner", errors)
    if runner_path and not runner_path.exists():
        errors.append(f"{path}: runner does not exist: {manifest_runner}")
    instruments = data.get("instruments", []) or []
    if not isinstance(instruments, list) or not instruments:
        errors.append(f"{path}: instruments must be a non-empty list")
        return errors
    for idx, instrument in enumerate(instruments):
        if not isinstance(instrument, dict):
            errors.append(f"{path}: instrument #{idx} must be a mapping")
            continue
        instrument_type = instrument.get("type")
        if not instrument.get("id") or not instrument_type:
            errors.append(f"{path}: instrument #{idx} must include id and type")
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
    workflow = load_yaml(workflow_path)
    selected_strictness = effective_strictness(workflow, selected_strictness)
    gates: set[str] = set()
    for phase in workflow.get("phases", []) or []:
        if not isinstance(phase, dict) or not phase.get("gate"):
            continue
        applies = phase.get("applies_to_strictness")
        if not applies:
            gates.add(str(phase["gate"]))
            continue
        if str(selected_strictness) in {str(item) for item in applies or []}:
            gates.add(str(phase["gate"]))
    return gates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="Path to project root or overlay root")
    parser.add_argument("--agentsflow-root", default=".")
    args = parser.parse_args()
    project = Path(args.project).resolve()
    af = Path(args.agentsflow_root).resolve()
    errors: list[str] = []
    project_schema = load_json(af / "schemas" / "project-binding.schema.json")
    workflow_binding_schema = load_json(af / "schemas" / "workflow-binding.schema.json")
    reviewer_roles = collect_reviewer_roles(af)
    review_topologies = collect_review_topologies(af)

    overlay = project / ".agentsflow"
    if not overlay.exists():
        overlay = project
    project_root = overlay.parent

    project_yaml = overlay / "project.yaml"
    lock_yaml = overlay / "agentsflow.lock.yaml"
    if not lock_yaml.exists():
        errors.append(f"missing agentsflow.lock.yaml at {lock_yaml}")
    if not project_yaml.exists():
        errors.append(f"missing project.yaml at {project_yaml}")
    else:
        data = load_yaml(project_yaml)
        errors.extend(validate_schema(project_yaml, data, project_schema))

    workflow_dir = overlay / "workflows"
    if not workflow_dir.exists():
        errors.append(f"missing workflows directory at {workflow_dir}")
    else:
        binding_files = sorted(workflow_dir.glob("*.binding.yaml"))
        if not binding_files:
            errors.append(f"no workflow binding files found in {workflow_dir}")
        for binding_file in binding_files:
            binding = load_yaml(binding_file)
            errors.extend(validate_schema(binding_file, binding, workflow_binding_schema))
            errors.extend(validate_review_policy(binding_file, binding.get("review"), review_topologies, reviewer_roles))
            errors.extend(validate_review_cycle_policy(binding_file, binding.get("review_cycle")))
            extends = binding.get("extends")
            extends_path = safe_resolve(af, extends, f"{binding_file}: extends", errors)
            if extends_path and not extends_path.exists():
                errors.append(f"{binding_file}: upstream workflow does not exist: {extends}")
            gates = binding.get("gates", {}) or {}
            if not isinstance(gates, dict):
                errors.append(f"{binding_file}: gates must be a mapping")
                continue
            if extends_path and extends_path.exists():
                workflow = load_yaml(extends_path)
                strictness_errors, override_strictness = validate_binding_strictness_policy(
                    binding_file,
                    binding,
                    workflow,
                )
                errors.extend(strictness_errors)
                missing_gates = sorted(
                    required_workflow_gates(extends_path, override_strictness)
                    - set(str(key) for key in gates)
                )
                if missing_gates:
                    errors.append(f"{binding_file}: missing project gate binding(s): {', '.join(missing_gates)}")
            for gate_id, cfg in gates.items():
                if not isinstance(cfg, dict):
                    errors.append(f"{binding_file}: gate {gate_id} binding must be a mapping")
                    continue
                upstream = cfg.get("extends")
                upstream_path = safe_resolve(af, upstream, f"{binding_file}: gate {gate_id} extends", errors)
                if upstream_path and not upstream_path.exists():
                    errors.append(f"{binding_file}: gate {gate_id} upstream contract missing: {upstream}")
                elif upstream_path:
                    upstream_data = load_yaml(upstream_path)
                    upstream_id = str(upstream_data.get("id", upstream_path.stem))
                    if upstream_id != str(gate_id):
                        errors.append(
                            f"{binding_file}: gate {gate_id} extends upstream gate id {upstream_id}"
                        )
                manifest = cfg.get("manifest")
                manifest_path = safe_resolve(project_root, manifest, f"{binding_file}: gate {gate_id} manifest", errors)
                if manifest_path and not manifest_path.exists():
                    errors.append(f"{binding_file}: gate {gate_id} project manifest missing: {manifest}")
                elif manifest_path:
                    errors.extend(validate_project_gate_manifest(manifest_path, project_root, upstream, cfg.get("runner")))
                runner = cfg.get("runner")
                if not runner:
                    errors.append(f"{binding_file}: gate {gate_id} missing project runner")
                    continue
                runner_path = safe_resolve(project_root, runner, f"{binding_file}: gate {gate_id} runner", errors)
                if runner_path and not runner_path.exists():
                    errors.append(f"{binding_file}: gate {gate_id} runner missing: {runner}")

    if errors:
        print("Project binding validation failed:")
        for e in errors:
            print(f"- {e}")
        return 1
    print("Project binding validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
