#!/usr/bin/env python3
"""Validate a project intake / research assignment YAML file."""
from __future__ import annotations

import argparse
from pathlib import Path
import yaml

ALLOWED_MODES = {"unknown-project-discovery", "directed-onboarding", "problem-driven", "migration-driven", "risk-driven"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--intake", required=True)
    args = parser.parse_args()
    path = Path(args.intake)
    errors: list[str] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        print(f"Project intake validation failed:\n- {exc}")
        return 1
    if not isinstance(data, dict):
        errors.append("intake must be a YAML mapping")
    else:
        for key in ["version", "mode", "objective", "analysis_focus", "constraints"]:
            if key not in data:
                errors.append(f"missing required field: {key}")
        if data.get("mode") not in ALLOWED_MODES:
            errors.append(f"unknown mode: {data.get('mode')}")
    if errors:
        print("Project intake validation failed:")
        for e in errors:
            print(f"- {e}")
        return 1
    print("Project intake validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
