#!/usr/bin/env python3
"""Generic deterministic gate runner for AgentsFlow manifests.

v0.1 runner: validates the gate manifest shape and writes a structured report skeleton.
It is intentionally conservative: it does not pretend optional external instruments ran.
Real projects can replace this runner or provide workflow-specific wrappers.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import yaml


def load_yaml(path: Path) -> dict:
    with path.open('r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--gate', required=True, help='Path to gates/<gate_id>.yaml')
    parser.add_argument('--output', default='', help='Optional JSON report path')
    parser.add_argument('--dry-run', action='store_true', help='Do not execute commands; only validate manifest and report planned instruments')
    args = parser.parse_args()

    gate_path = Path(args.gate)
    gate = load_yaml(gate_path)
    required = ['id', 'runner', 'instruments', 'outputs', 'pass_policy']
    missing = [k for k in required if k not in gate]
    status = 'pass' if not missing else 'fail'
    report = {
        'gate_id': gate.get('id', gate_path.stem),
        'status': status,
        'mode': 'dry-run' if args.dry_run else 'manifest-validation-only',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'missing_manifest_fields': missing,
        'planned_instruments': gate.get('instruments', []),
        'required_evidence': gate.get('required_evidence', []),
        'outputs': gate.get('outputs', []),
        'note': 'v0.1 generic runner validates manifest structure and planned instruments. It does not execute project-specific commands unless replaced by a concrete runner.',
    }
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    else:
        print(json.dumps(report, indent=2))
    return 0 if status == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
