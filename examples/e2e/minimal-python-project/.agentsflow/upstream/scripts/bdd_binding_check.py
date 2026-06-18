#!/usr/bin/env python3
"""Minimal pinned-upstream behavior binding checker for the e2e fixture."""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

VALID_CHECK_TYPES = {
    "test",
    "script",
    "bdd_runner",
    "eval",
    "trace_assertion",
    "log_assertion",
    "static_analysis",
    "dynamic_analysis",
    "benchmark",
    "security_scan",
    "manual_evidence",
    "external_tool",
}


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    data = load_yaml(path)
    for key in ["version", "contract", "bindings"]:
        if key not in data:
            errors.append(f"{path}: missing required field {key}")
    bindings = data.get("bindings", []) or []
    if not isinstance(bindings, list):
        return errors + [f"{path}: bindings must be a list"]
    ids: set[str] = set()
    for idx, item in enumerate(bindings):
        if not isinstance(item, dict):
            errors.append(f"{path}: binding #{idx} must be a mapping")
            continue
        bid = str(item.get("id", f"#{idx}"))
        if bid in ids:
            errors.append(f"{path}: duplicate binding id {bid}")
        ids.add(bid)
        for key in ["id", "scenario", "required", "checks", "gates"]:
            if key not in item:
                errors.append(f"{path}: binding {bid} missing {key}")
        required = bool(item.get("required", False))
        checks = item.get("checks", []) or []
        gates = item.get("gates", []) or []
        if required and not checks:
            errors.append(f"{path}: required binding {bid} has no checks")
        if required and not gates:
            errors.append(f"{path}: required binding {bid} has no gates")
        if not isinstance(checks, list):
            errors.append(f"{path}: binding {bid} checks must be a list")
            continue
        for cidx, check in enumerate(checks):
            if not isinstance(check, dict):
                errors.append(f"{path}: binding {bid} check #{cidx} must be a mapping")
                continue
            ctype = check.get("type")
            if ctype not in VALID_CHECK_TYPES:
                errors.append(f"{path}: binding {bid} check {check.get('id', cidx)} has unknown type {ctype}")
            if ctype != "manual_evidence" and not (check.get("command") or check.get("target")):
                errors.append(f"{path}: binding {bid} check {check.get('id', cidx)} needs command or target")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bindings", required=True)
    args = parser.parse_args()
    errors = validate(Path(args.bindings))
    if errors:
        print("Behavior binding validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Behavior binding validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
