#!/usr/bin/env python3
from __future__ import annotations

import argparse
from _common import read_text, heading_exists, fail, ok

REQUIRED = [
    "Intent",
    "Fixed Decisions",
    "Boundaries",
    "Behavioral Scenarios",
    "Verification Binding",
    "Evidence Required",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Lint v0.1 Markdown task contract structure.")
    parser.add_argument("--contract", required=True, help="Path to *.contract.md")
    args = parser.parse_args()

    text = read_text(args.contract)
    missing = [h for h in REQUIRED if not heading_exists(text, h)]
    if missing:
        fail("missing required sections: " + ", ".join(missing))
    ok(f"contract has required sections: {args.contract}")


if __name__ == "__main__":
    main()
