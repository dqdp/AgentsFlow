#!/usr/bin/env python3
"""Validate a project intake / research assignment YAML file."""
from __future__ import annotations

import argparse
from pathlib import Path
import yaml

ALLOWED_MODES = {"unknown-project-discovery", "directed-onboarding", "problem-driven", "migration-driven", "risk-driven"}
ALLOWED_INTENT_MODES = {
    "unknown-discovery",
    "adoption-onboarding",
    "prepare-workflow",
    "legacy-cleanup",
    "risk-domain-assessment",
}


def known_mvp_user_workflow_ids(root: Path) -> set[str]:
    workflow_ids: set[str] = set()
    workflows_dir = root / "workflows"
    if not workflows_dir.exists():
        return workflow_ids
    for workflow_path in workflows_dir.glob("*/workflow.yaml"):
        try:
            data = yaml.safe_load(workflow_path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if (
            isinstance(data, dict)
            and isinstance(data.get("name"), str)
            and data.get("mvp_status") == "v0.2-mvp"
        ):
            workflow_ids.add(data["name"])
    return workflow_ids


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--intake", required=True)
    args = parser.parse_args()
    path = Path(args.intake)
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        print(f"Project intake validation failed:\n- {exc}")
        return 1
    if not isinstance(data, dict):
        errors.append("intake must be a YAML mapping")
    else:
        for key in ["version", "mode", "intent_mode", "objective", "analysis_focus", "constraints"]:
            if key not in data:
                errors.append(f"missing required field: {key}")
        if data.get("mode") not in ALLOWED_MODES:
            errors.append(f"unknown mode: {data.get('mode')}")
        if data.get("intent_mode") not in ALLOWED_INTENT_MODES:
            errors.append(f"unknown intent_mode: {data.get('intent_mode')}")
        target_workflow = data.get("target_workflow")
        if data.get("intent_mode") == "prepare-workflow" and (
            not isinstance(target_workflow, str) or not target_workflow.strip()
        ):
            errors.append("target_workflow must be a non-empty string when intent_mode is prepare-workflow")
        elif data.get("intent_mode") == "prepare-workflow":
            known_workflows = known_mvp_user_workflow_ids(root)
            if target_workflow not in known_workflows:
                errors.append(
                    "target_workflow must match a v0.2 MVP user workflow id when intent_mode is prepare-workflow"
                )
    if errors:
        print("Project intake validation failed:")
        for e in errors:
            print(f"- {e}")
        return 1
    print("Project intake validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
