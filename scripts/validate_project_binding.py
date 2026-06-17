#!/usr/bin/env python3
"""Validate a project overlay that binds AgentsFlow upstream workflows/gates."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import yaml


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="Path to project root or overlay root")
    parser.add_argument("--agentsflow-root", default=".")
    args = parser.parse_args()
    project = Path(args.project).resolve()
    af = Path(args.agentsflow_root).resolve()
    errors: list[str] = []

    overlay = project / ".agentsflow"
    if not overlay.exists():
        overlay = project

    project_yaml = overlay / "project.yaml"
    if not project_yaml.exists():
        errors.append(f"missing project.yaml at {project_yaml}")
    else:
        data = load_yaml(project_yaml)
        for key in ["name", "agentsflow_version", "paths"]:
            if key not in data:
                errors.append(f"{project_yaml}: missing {key}")

    workflow_dir = overlay / "workflows"
    if workflow_dir.exists():
        for binding_file in workflow_dir.glob("*.binding.yaml"):
            binding = load_yaml(binding_file)
            extends = binding.get("extends")
            if extends and not (af / str(extends)).exists():
                errors.append(f"{binding_file}: upstream workflow does not exist: {extends}")
            gates = binding.get("gates", {}) or {}
            if not isinstance(gates, dict):
                errors.append(f"{binding_file}: gates must be a mapping")
                continue
            for gate_id, cfg in gates.items():
                if not isinstance(cfg, dict):
                    errors.append(f"{binding_file}: gate {gate_id} binding must be a mapping")
                    continue
                upstream = cfg.get("extends")
                if upstream and not (af / str(upstream)).exists():
                    errors.append(f"{binding_file}: gate {gate_id} upstream contract missing: {upstream}")
                manifest = cfg.get("manifest")
                if manifest and not (project / str(manifest)).exists() and not (overlay.parent / str(manifest)).exists():
                    errors.append(f"{binding_file}: gate {gate_id} project manifest missing: {manifest}")
                runner = cfg.get("runner")
                if not runner:
                    errors.append(f"{binding_file}: gate {gate_id} missing project runner")
                elif not (project / str(runner)).exists() and not (overlay.parent / str(runner)).exists():
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
