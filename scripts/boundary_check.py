#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from _common import read_text, extract_section, fail, ok


def normalize_prefix(line: str) -> str | None:
    line = line.strip()
    if not line.startswith("- "):
        return None
    value = line[2:].strip().strip("`")
    value = value.replace("**", "")
    if value.endswith("/"):
        return value
    if value.endswith("*"):
        return value.rstrip("*")
    return value


def extract_subsection_lines(section: str, subsection: str) -> list[str]:
    marker = f"### {subsection}"
    idx = section.find(marker)
    if idx < 0:
        return []
    rest = section[idx + len(marker):]
    next_idx = rest.find("### ")
    if next_idx >= 0:
        rest = rest[:next_idx]
    return [line for line in rest.splitlines() if line.strip().startswith("- ")]


def main() -> None:
    parser = argparse.ArgumentParser(description="Check changed files against contract boundaries.")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--changed-files", required=True, help="Text file with one changed path per line")
    args = parser.parse_args()

    text = read_text(args.contract)
    boundaries = extract_section(text, "Boundaries")
    allowed = [normalize_prefix(l) for l in extract_subsection_lines(boundaries, "Allowed Paths")]
    forbidden = [normalize_prefix(l) for l in extract_subsection_lines(boundaries, "Forbidden Paths Without Approval")]
    allowed = [p for p in allowed if p]
    forbidden = [p for p in forbidden if p]

    changed = [line.strip() for line in Path(args.changed_files).read_text(encoding="utf-8").splitlines() if line.strip()]

    violations = []
    for path in changed:
        if any(path.startswith(prefix) for prefix in forbidden):
            violations.append(f"forbidden path touched: {path}")
        if allowed and not any(path.startswith(prefix) for prefix in allowed):
            violations.append(f"outside allowed paths: {path}")

    if violations:
        fail("boundary violations:\n" + "\n".join(f"- {v}" for v in violations))

    ok(f"changed files respect contract boundaries: {len(changed)} file(s)")


if __name__ == "__main__":
    main()
