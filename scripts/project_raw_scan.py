#!/usr/bin/env python3
"""Collect observable raw repository facts for AgentsFlow initialization.

This scanner does not attempt to understand the project. It only records
machine-observable evidence that a model/main agent may later structure into
project-inventory.json.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

BUILD_NAMES = {"CMakeLists.txt", "pyproject.toml", "package.json", "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "Makefile"}
AGENT_NAMES = {"AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md"}
DOC_NAMES = {"README.md", "Docs", "docs", "doc", "documentation"}
SOURCE_NAMES = {"src", "source", "lib", "include", "app"}
TEST_NAMES = {"test", "tests", "spec", "specs"}


def rel(p: Path, root: Path) -> str:
    return str(p.relative_to(root)).replace("\\", "/")


def git_status(root: Path) -> str:
    try:
        out = subprocess.run(["git", "status", "--short"], cwd=root, text=True, capture_output=True, timeout=5)
        if out.returncode != 0:
            return "git-status-unavailable"
        return out.stdout.strip() or "clean"
    except Exception:
        return "git-status-unavailable"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="")
    parser.add_argument("--max-files", type=int, default=2000)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    files = []
    for p in root.rglob("*"):
        if any(part in {".git", ".pytest_cache", "__pycache__", "node_modules", "build", "dist"} for part in p.parts):
            continue
        if p.is_file():
            files.append(rel(p, root))
            if len(files) >= args.max_files:
                break
    top = [p.name + ("/" if p.is_dir() else "") for p in root.iterdir() if p.name != ".git"]
    report = {
        "version": 1,
        "scan_mode": "raw-observed-facts",
        "repository_root": str(root),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "observed_files": sorted(files),
        "top_level_entries": sorted(top),
        "candidate_build_files": sorted([f for f in files if Path(f).name in BUILD_NAMES]),
        "candidate_ci_files": sorted([f for f in files if f.startswith(".github/workflows/") or "/.github/workflows/" in f]),
        "candidate_docs_roots": sorted([x for x in top if x.rstrip("/") in DOC_NAMES]),
        "candidate_source_roots": sorted([x for x in top if x.rstrip("/") in SOURCE_NAMES]),
        "candidate_test_roots": sorted([x for x in top if x.rstrip("/") in TEST_NAMES]),
        "candidate_agent_instruction_files": sorted([f for f in files if Path(f).name in AGENT_NAMES or ".cursor" in f]),
        "candidate_markdown_history_files": sorted([f for f in files if f.lower().endswith(".md") and any(token in f.lower() for token in ["history", "plan", "implementation", "migration", "postmortem", "runbook", "adr", "decision", "report"])]),
        "git_status": git_status(root),
        "notes": ["Raw scan only. Model-produced inventory must add provenance/confidence for inferred fields."],
    }
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
