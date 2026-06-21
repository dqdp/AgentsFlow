from __future__ import annotations

import hashlib
import json
from pathlib import Path

import jsonschema
import yaml


def parse_yaml(path: Path) -> object:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"YAML parse error in {path}: {exc}") from exc


class UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            mark = key_node.start_mark
            raise ValueError(f"duplicate YAML key {key!r} at line {mark.line + 1}, column {mark.column + 1}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def validate_no_duplicate_yaml_keys(path: Path) -> list[str]:
    try:
        yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except Exception as exc:  # noqa: BLE001
        return [f"{path}: {exc}"]
    return []


def parse_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"JSON parse error in {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def is_concrete_sha256(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(char in "0123456789abcdef" for char in digest)


def compare_hash(path: Path, label: str, declared: object, actual: str, errors: list[str]) -> None:
    if is_concrete_sha256(declared) and declared != actual:
        errors.append(f"{path}: {label} hash mismatch: declared {declared}, computed {actual}")


def workflow_schema(root: Path) -> dict:
    schema = parse_json(root / "schemas" / "workflow.schema.json")
    if not isinstance(schema, dict):
        raise ValueError("schemas/workflow.schema.json is not a mapping")
    phase_schema = parse_json(root / "schemas" / "workflow-phase.schema.json")
    review_cycle_schema = parse_json(root / "schemas" / "review-cycle.schema.json")
    schema = dict(schema)
    properties = dict(schema.get("properties", {}))
    phases = dict(properties.get("phases", {}))
    phases["items"] = phase_schema
    properties["phases"] = phases
    properties["review_cycle"] = review_cycle_schema
    schema["properties"] = properties
    return schema


def schema_error_path(error: jsonschema.ValidationError) -> str:
    parts = [str(part) for part in error.absolute_path]
    return ".".join(parts) if parts else "<root>"


def validate_against_schema(path: Path, data: object, schema: dict) -> list[str]:
    validator = jsonschema.Draft202012Validator(schema)
    errors: list[str] = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        errors.append(f"{path}: schema error at {schema_error_path(error)}: {error.message}")
    return errors


def safe_resolve(base: Path, ref: object, label: str, errors: list[str]) -> Path | None:
    if not ref:
        return None
    ref_path = Path(str(ref))
    if ref_path.is_absolute() or ".." in ref_path.parts:
        errors.append(f"{label} must be a relative non-escaping path: {ref}")
        return None
    resolved_base = base.resolve()
    resolved = (base / ref_path).resolve()
    try:
        resolved.relative_to(resolved_base)
    except ValueError:
        errors.append(f"{label} escapes expected root: {ref}")
        return None
    return resolved
