from __future__ import annotations

from pathlib import Path

from .common import parse_yaml


def collect_names(root: Path, base: str, manifest: str) -> set[str]:
    names: set[str] = set()
    d = root / base
    if not d.exists():
        return names
    for p in d.iterdir():
        if p.is_dir() and (p / manifest).exists():
            names.add(p.name)
    return names


def collect_script_names(root: Path) -> set[str]:
    names: set[str] = set()
    for p in (root / "scripts" / "contracts").glob("*.yaml"):
        data = parse_yaml(p) or {}
        if isinstance(data, dict):
            names.add(str(data.get("name", p.stem)))
        else:
            names.add(p.stem)
    return names


def collect_gate_manifests(root: Path) -> dict[str, Path]:
    gates: dict[str, Path] = {}
    for p in (root / "gates").glob("*.yaml"):
        data = parse_yaml(p) or {}
        if isinstance(data, dict):
            gid = str(data.get("id", p.stem))
            gates[gid] = p
    return gates


def collect_yaml_manifest_names(root: Path, base: str) -> set[str]:
    names: set[str] = set()
    d = root / base
    if not d.exists():
        return names
    for p in d.glob("*.yaml"):
        data = parse_yaml(p) or {}
        if isinstance(data, dict):
            names.add(str(data.get("name", p.stem)))
        else:
            names.add(p.stem)
    return names


def collect_active_review_topologies(root: Path) -> set[str]:
    names: set[str] = set()
    for path in (root / "profiles" / "review_topologies").glob("*.yaml"):
        data = parse_yaml(path) or {}
        if isinstance(data, dict) and data.get("deprecated") is not True:
            names.add(str(data.get("name", path.stem)))
    return names
