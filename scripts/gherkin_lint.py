#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from _common import read_text, extract_section, fail, ok

VAGUE = [
    "correctly",
    "properly",
    "as expected",
    "reasonably",
    "appropriate",
    "robustly",
    "everything should work",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Lightweight BDD/Gherkin lint for v0.1 contracts.")
    parser.add_argument("--contract", required=True, help="Path to contract containing Behavioral Scenarios")
    args = parser.parse_args()

    text = read_text(args.contract)
    section = extract_section(text, "Behavioral Scenarios") or text

    if "Scenario:" not in section:
        fail("no Scenario found in Behavioral Scenarios")

    lower = section.lower()
    vague_hits = [w for w in VAGUE if w in lower]
    if vague_hits:
        fail("vague scenario wording found: " + ", ".join(vague_hits))

    scenarios = re.split(r"^\s*Scenario:\s+", section, flags=re.MULTILINE)[1:]
    bad = []
    for i, body in enumerate(scenarios, 1):
        has_given = re.search(r"^\s*Given\s+", body, flags=re.MULTILINE)
        has_when = re.search(r"^\s*When\s+", body, flags=re.MULTILINE)
        has_then = re.search(r"^\s*Then\s+", body, flags=re.MULTILINE)
        if not (has_given and has_when and has_then):
            bad.append(str(i))

    if bad:
        fail("scenarios missing Given/When/Then: " + ", ".join(bad))

    ok(f"gherkin scenarios look structurally valid: {args.contract}")


if __name__ == "__main__":
    main()
