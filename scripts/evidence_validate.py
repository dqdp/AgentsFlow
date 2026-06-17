#!/usr/bin/env python3
from __future__ import annotations

import argparse
from _common import read_text, heading_exists, fail, ok

REQUIRED = [
    "Summary",
    "Changed Files",
    "Scenario Coverage",
    "Verification Commands",
    "Boundary Check",
    "Known Limitations",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate v0.1 evidence report structure.")
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()

    text = read_text(args.evidence)
    missing = [h for h in REQUIRED if not heading_exists(text, h)]
    if missing:
        fail("evidence report missing sections: " + ", ".join(missing))
    ok(f"evidence report has required sections: {args.evidence}")


if __name__ == "__main__":
    main()
