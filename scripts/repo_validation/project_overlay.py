from __future__ import annotations

from pathlib import Path

from .common import parse_yaml, safe_resolve, validate_against_schema
from .gates import required_workflow_gates, validate_project_gate_manifest
from .review import validate_enabled_review_minimum


def validate_project_overlay_example(
    root: Path,
    project_rel: str,
    project_schema: dict,
    workflow_binding_schema: dict,
    reviewer_role_names: set[str],
) -> list[str]:
    errors: list[str] = []
    project = root / project_rel
    overlay = project / ".agentsflow"
    if not overlay.exists():
        return [f"{project_rel}: missing .agentsflow overlay"]
    lock_file = overlay / "agentsflow.lock.yaml"
    if not lock_file.exists():
        errors.append(f"{project_rel}: missing .agentsflow/agentsflow.lock.yaml")
    project_yaml = overlay / "project.yaml"
    if not project_yaml.exists():
        errors.append(f"{project_rel}: missing .agentsflow/project.yaml")
    else:
        data = parse_yaml(project_yaml) or {}
        if not isinstance(data, dict):
            errors.append(f"{project_yaml}: project manifest must be a mapping")
        else:
            errors.extend(validate_against_schema(project_yaml, data, project_schema))
    workflow_dir = overlay / "workflows"
    if not workflow_dir.exists():
        errors.append(f"{project_rel}: missing .agentsflow/workflows")
    else:
        binding_files = sorted(workflow_dir.glob("*.binding.yaml"))
        if not binding_files:
            errors.append(f"{project_rel}: no workflow binding files found")
        for binding_file in binding_files:
            binding = parse_yaml(binding_file) or {}
            if not isinstance(binding, dict):
                errors.append(f"{binding_file}: workflow binding must be a mapping")
                continue
            errors.extend(validate_against_schema(binding_file, binding, workflow_binding_schema))
            errors.extend(
                validate_enabled_review_minimum(
                    binding_file,
                    binding.get("review"),
                    "review",
                    reviewer_role_names,
                )
            )
            extends = binding.get("extends")
            extends_path = safe_resolve(root, extends, f"{binding_file}: extends", errors)
            if extends_path and not extends_path.exists():
                errors.append(f"{binding_file}: upstream workflow does not exist: {extends}")
            gates = binding.get("gates", {}) or {}
            if extends_path and extends_path.exists() and isinstance(gates, dict):
                missing_gates = sorted(
                    required_workflow_gates(extends_path, binding.get("strictness"))
                    - set(str(key) for key in gates)
                )
                if missing_gates:
                    errors.append(f"{binding_file}: missing project gate binding(s): {', '.join(missing_gates)}")
            for gate_id, cfg in (binding.get("gates", {}) or {}).items():
                if not isinstance(cfg, dict):
                    continue
                upstream = cfg.get("extends")
                upstream_path = safe_resolve(root, upstream, f"{binding_file}: gate {gate_id} extends", errors)
                if upstream_path and not upstream_path.exists():
                    errors.append(f"{binding_file}: gate {gate_id} upstream contract missing: {upstream}")
                elif upstream_path:
                    upstream_data = parse_yaml(upstream_path) or {}
                    if isinstance(upstream_data, dict):
                        upstream_id = str(upstream_data.get("id", upstream_path.stem))
                        if upstream_id != str(gate_id):
                            errors.append(
                                f"{binding_file}: gate {gate_id} extends upstream gate id {upstream_id}"
                            )
                manifest = cfg.get("manifest")
                manifest_path = safe_resolve(project, manifest, f"{binding_file}: gate {gate_id} manifest", errors)
                if manifest_path and not manifest_path.exists():
                    errors.append(f"{binding_file}: gate {gate_id} project manifest missing: {manifest}")
                elif manifest_path:
                    errors.extend(validate_project_gate_manifest(manifest_path, project, upstream, cfg.get("runner")))
                runner = cfg.get("runner")
                runner_path = safe_resolve(project, runner, f"{binding_file}: gate {gate_id} runner", errors)
                if runner_path and not runner_path.exists():
                    errors.append(f"{binding_file}: gate {gate_id} runner missing: {runner}")
    return errors

