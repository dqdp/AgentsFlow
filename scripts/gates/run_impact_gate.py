#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_gate import main as generic_main  # noqa: E402

if __name__ == '__main__':
    if '--gate' not in sys.argv:
        sys.argv.extend(['--gate', str(ROOT / 'gates' / 'impact_gate.yaml')])
    raise SystemExit(generic_main())
