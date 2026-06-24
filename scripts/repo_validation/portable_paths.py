from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .common import parse_json, parse_yaml


SKIP_DIRS = {
    ".agentsflow",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
}

SKIP_PATH_PREFIXES = {
    ("run-artifacts", "agentsflow"),
}

PATH_KEYS = {
    "cwd",
    "path",
    "paths",
    "provider_config",
    "root",
    "workdir",
    "working_directory",
}


def _is_path_key(key: object) -> bool:
    name = str(key).lower()
    return (
        name in PATH_KEYS
        or name.endswith("_path")
        or name.endswith("_paths")
        or name.endswith("_root")
    )


def _is_repo_local_absolute(value: str, root: Path) -> bool:
    try:
        Path(value).resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def _iter_structured_files(root: Path) -> list[Path]:
    if (root / ".git").exists():
        result = subprocess.run(
            ["git", "ls-files", "*.json", "*.yaml", "*.yml"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return sorted(
                root / line
                for line in result.stdout.splitlines()
                if line and not any(part in SKIP_DIRS for part in Path(line).parts)
                and not any(Path(line).parts[: len(prefix)] == prefix for prefix in SKIP_PATH_PREFIXES)
            )
    return sorted(
        path
        for suffix in ("*.json", "*.yaml", "*.yml")
        for path in root.rglob(suffix)
        if not any(part in SKIP_DIRS for part in path.parts)
        and not any(path.relative_to(root).parts[: len(prefix)] == prefix for prefix in SKIP_PATH_PREFIXES)
    )


def _walk_path_values(data: Any, trail: tuple[object, ...] = ()) -> list[tuple[str, str]]:
    errors: list[tuple[str, str]] = []
    if isinstance(data, dict):
        for key, value in data.items():
            current_trail = (*trail, key)
            if _is_path_key(key) and isinstance(value, str):
                errors.append((".".join(str(part) for part in current_trail), value))
            errors.extend(_walk_path_values(value, current_trail))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            errors.extend(_walk_path_values(value, (*trail, index)))
    return errors


def validate_portable_structured_paths(root: Path) -> list[str]:
    errors: list[str] = []
    root = root.resolve()
    for path in _iter_structured_files(root):
        try:
            data = parse_json(path) if path.suffix == ".json" else parse_yaml(path)
        except ValueError:
            continue
        for key_path, value in _walk_path_values(data):
            if Path(value).is_absolute() and _is_repo_local_absolute(value, root):
                errors.append(
                    f"{path}: {key_path} must be repository-relative, not host-absolute: {value}"
                )
    return errors
