#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from _common import read_text, fail, ok

REQUIRED_KEYS = ["name:", "version:", "modules:", "paths:", "required_tests:"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Lightweight impact-map structure check.")
    parser.add_argument("--impact-map", required=True)
    args = parser.parse_args()

    text = read_text(args.impact_map)
    missing = [k for k in REQUIRED_KEYS if k not in text]
    if missing:
        fail("impact map missing keys: " + ", ".join(missing))

    if not re.search(r"required_tests:\s*\n\s+-", text):
        fail("impact map must list at least one required test")

    ok(f"impact map has required structure: {args.impact_map}")


if __name__ == "__main__":
    main()
