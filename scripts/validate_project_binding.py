#!/usr/bin/env python3
"""Validate a project overlay that binds AgentsFlow upstream workflows/gates."""
from __future__ import annotations

import argparse
from pathlib import Path

from repo_validation.collect import collect_active_review_topologies, collect_yaml_manifest_names
from repo_validation.common import parse_json, parse_yaml, safe_resolve, validate_against_schema
from repo_validation.gates import (
    required_workflow_gates,
    validate_binding_strictness_policy,
    validate_project_gate_manifest,
)
from repo_validation.review import validate_enabled_review_minimum


def load_yaml(path: Path) -> dict:
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_json(path: Path) -> dict:
    data = parse_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


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
    reviewer_roles = collect_yaml_manifest_names(af, "profiles/reviewer_roles")
    review_topologies = collect_active_review_topologies(af)

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
        errors.extend(validate_against_schema(project_yaml, data, project_schema))

    workflow_dir = overlay / "workflows"
    if not workflow_dir.exists():
        errors.append(f"missing workflows directory at {workflow_dir}")
    else:
        binding_files = sorted(workflow_dir.glob("*.binding.yaml"))
        if not binding_files:
            errors.append(f"no workflow binding files found in {workflow_dir}")
        for binding_file in binding_files:
            binding = load_yaml(binding_file)
            errors.extend(validate_against_schema(binding_file, binding, workflow_binding_schema))
            errors.extend(validate_review_policy(binding_file, binding.get("review"), review_topologies, reviewer_roles))
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
