#!/usr/bin/env python3
"""Validate AgentsFlow behavior binding manifests.

Minimal v0.1.8 checker: required bindings must have at least one check and at
least one gate. It validates structure and path existence where commands point to
repo-local files conservatively.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from repo_validation.behavior_bindings import validate_behavior_binding


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bindings", required=True)
    args = parser.parse_args()
    path = Path(args.bindings)
    errors = validate_behavior_binding(path)
    if errors:
        print("Behavior binding validation failed:")
        for e in errors:
            print(f"- {e}")
        return 1
    print("Behavior binding validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
