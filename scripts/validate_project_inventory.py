#!/usr/bin/env python3
"""Validate model-produced AgentsFlow project inventory/assessment files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True)
    args = parser.parse_args()
    path = Path(args.inventory)
    errors: list[str] = []
    try:
        data = load_json(path)
    except Exception as exc:
        print(f"Project inventory validation failed:\n- {exc}")
        return 1
    for key in ["version", "project", "domain_identification", "unknowns", "human_questions"]:
        if key not in data:
            errors.append(f"missing required field: {key}")
    project = data.get("project", {})
    if not isinstance(project, dict):
        errors.append("project must be an object")
    domain = data.get("domain_identification", {})
    if not isinstance(domain, dict):
        errors.append("domain_identification must be an object")
    else:
        primary = domain.get("primary_domain")
        if not isinstance(primary, dict):
            errors.append("domain_identification.primary_domain must be an object")
        else:
            for pkey in ["value", "source_type", "observed_evidence", "confidence", "requires_human_confirmation"]:
                if pkey not in primary:
                    errors.append(f"domain_identification.primary_domain: missing {pkey}")
    # Soft provenance check for structured field objects.
    for field, value in project.items() if isinstance(project, dict) else []:
        if isinstance(value, dict) and "value" in value:
            for pkey in ["source_type", "evidence", "confidence", "requires_human_confirmation"]:
                if pkey not in value:
                    errors.append(f"project.{field}: missing provenance/confidence field {pkey}")
    if errors:
        print("Project inventory validation failed:")
        for e in errors:
            print(f"- {e}")
        return 1
    print("Project inventory validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
