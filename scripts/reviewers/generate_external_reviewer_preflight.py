#!/usr/bin/env python3
"""Generate deterministic external reviewer preflight evidence."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_external_reviewer import (  # noqa: E402
    enforce_billing_policy,
    validate_provider_config,
    validate_raw_output_retention_policy,
)


DEFAULT_FORBIDDEN_ENV = [
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
]


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def forbidden_env_from_config(config: dict[str, Any]) -> list[str]:
    billing = config.get("billing", {}) or {}
    configured = billing.get("fail_if_env_present")
    if isinstance(configured, list):
        values = [str(item) for item in configured]
    else:
        values = list(DEFAULT_FORBIDDEN_ENV)
    for item in DEFAULT_FORBIDDEN_ENV:
        if item not in values:
            values.append(item)
    return values


def resolve_ref(ref: object, root: Path) -> Path:
    path = Path(str(ref))
    if path.is_absolute():
        return path
    return root / path


def concrete_hash(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(char in "0123456789abcdef" for char in digest)


def assignment_fingerprints(
    contract: dict[str, Any],
    root: Path,
    config_path: Path,
    role_contract_path: Path,
    rubric_source_path: Path,
    output_schema_path: Path,
    review_prompt_contract_path: Path,
    wrapper_path: Path,
    forbidden_env_fingerprint: str,
    execution: dict[str, Any],
) -> list[dict[str, Any]]:
    reviewers = {
        str(item.get("instance_id")): item
        for item in contract.get("reviewer_set", []) or []
        if isinstance(item, dict) and item.get("instance_id")
    }
    rendered_prompts = {
        str(item.get("reviewer")): item
        for item in contract.get("rendered_prompts", []) or []
        if isinstance(item, dict) and item.get("reviewer")
    }
    entries: list[dict[str, Any]] = []
    for assignment in contract.get("reviewer_assignments", []) or []:
        if not isinstance(assignment, dict) or assignment.get("provider") != "claude-code":
            continue
        reviewer = str(assignment.get("reviewer") or "")
        reviewer_def = reviewers.get(reviewer, {}) or {}
        rendered_prompt = rendered_prompts.get(reviewer, {}) or {}
        assignment_config = resolve_ref(assignment.get("provider_config") or config_path, root)
        assignment_role = resolve_ref(reviewer_def.get("role_contract") or role_contract_path, root)
        rubric_hash = rendered_prompt.get("rubric_hash")
        if not concrete_hash(rubric_hash):
            rubric_hash = sha256_file(rubric_source_path)
        entries.append(
            {
                "reviewer": reviewer,
                "provider_config_hash": sha256_file(assignment_config),
                "wrapper_hash": sha256_file(wrapper_path),
                "schema_hash": sha256_file(output_schema_path),
                "prompt_contract_hash": sha256_file(review_prompt_contract_path),
                "role_contract_hash": sha256_file(assignment_role),
                "rubric_hash": str(rubric_hash),
                "forbidden_env_fingerprint": forbidden_env_fingerprint,
                "permission_mode": str(execution["permission_mode"]),
                "sandbox_mode": str(execution["sandbox_mode"]),
                "provider_transport_mode": str(execution.get("prompt_transport", "stdin")),
            }
        )
    return entries


def validate_run_scope_raw_output_retention(
    contract: dict[str, Any],
    root: Path,
    default_config: dict[str, Any],
    default_config_path: Path,
    provider: str,
) -> None:
    if contract.get("artifact_scope", "run") != "run":
        return
    for assignment in contract.get("reviewer_assignments", []) or []:
        if not isinstance(assignment, dict) or assignment.get("provider") != provider:
            continue
        packet_ref = assignment.get("packet_path")
        raw_output_ref = assignment.get("raw_output_path")
        if not packet_ref or not raw_output_ref:
            continue
        assignment_config_path = resolve_ref(assignment.get("provider_config") or default_config_path, root)
        if assignment_config_path.resolve() == default_config_path.resolve():
            assignment_config = default_config
        else:
            assignment_config = load_yaml(assignment_config_path)
            validate_provider_config(assignment_config, provider)
            enforce_billing_policy(assignment_config)
        packet_path = resolve_ref(packet_ref, root)
        packet = load_json(packet_path)
        packet_hashes = {"artifact_scope": str(packet.get("artifact_scope") or contract.get("artifact_scope") or "run")}
        if packet_hashes["artifact_scope"] != "run":
            continue
        raw_output_path = resolve_ref(raw_output_ref, root)
        validate_raw_output_retention_policy(
            assignment_config,
            assignment_config_path,
            provider,
            packet,
            packet_hashes,
            raw_output_path,
        )


def generate_preflight(
    provider: str,
    config_path: Path,
    review_prompt_contract_path: Path,
    role_contract_path: Path,
    rubric_source_path: Path,
    output_schema_path: Path,
    mode: str,
    wrapper_path: Path,
) -> dict[str, Any]:
    if provider != "claude-code":
        raise ValueError("v0.2 external reviewer preflight supports provider claude-code only")
    config = load_yaml(config_path)
    validate_provider_config(config, provider)
    enforce_billing_policy(config)
    execution = config.get("execution", {}) or {}
    forbidden = forbidden_env_from_config(config)
    present = sorted(name for name in forbidden if name in os.environ)
    if present:
        raise RuntimeError(
            "Forbidden Claude API/proxy environment variable(s) present: "
            + ", ".join(present)
        )
    forbidden_payload = {
        "checked": sorted(set(forbidden)),
        "present": [],
    }
    forbidden_env_fingerprint = sha256_text(json.dumps(forbidden_payload, sort_keys=True))
    fingerprint = {
        "provider_config_hash": sha256_file(config_path),
        "wrapper_hash": sha256_file(wrapper_path),
        "schema_hash": sha256_file(output_schema_path),
        "prompt_contract_hash": sha256_file(review_prompt_contract_path),
        "role_contract_hash": sha256_file(role_contract_path),
        "rubric_hash": sha256_file(rubric_source_path),
        "forbidden_env_fingerprint": forbidden_env_fingerprint,
        "permission_mode": str(execution["permission_mode"]),
        "sandbox_mode": str(execution["sandbox_mode"]),
        "provider_transport_mode": str(execution.get("prompt_transport", "stdin")),
    }
    preflight = {
        "version": 1,
        "artifact_kind": "external_reviewer_preflight",
        "artifact_scope": "run",
        "provider": "claude-code",
        "mode": mode,
        "result": "pass",
        "generated_at": now_utc(),
        "live_provider_call": False,
        "fingerprint": fingerprint,
        "forbidden_env": forbidden_payload,
        "blockers": [],
    }
    contract = load_yaml(review_prompt_contract_path)
    validate_run_scope_raw_output_retention(
        contract,
        Path.cwd(),
        config,
        config_path,
        provider,
    )
    fingerprints = assignment_fingerprints(
        contract,
        Path.cwd(),
        config_path,
        role_contract_path,
        rubric_source_path,
        output_schema_path,
        review_prompt_contract_path,
        wrapper_path,
        forbidden_env_fingerprint,
        execution,
    )
    if fingerprints:
        preflight["assignment_fingerprints"] = fingerprints
    return preflight


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--review-prompt-contract", required=True)
    parser.add_argument("--role-contract", required=True)
    parser.add_argument("--rubric-source", required=True)
    parser.add_argument("--output-schema", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=["full", "cached_fingerprint"], default="full")
    parser.add_argument("--wrapper", default="scripts/reviewers/run_external_reviewer.py")
    args = parser.parse_args()

    preflight = generate_preflight(
        args.provider,
        Path(args.config),
        Path(args.review_prompt_contract),
        Path(args.role_contract),
        Path(args.rubric_source),
        Path(args.output_schema),
        args.mode,
        Path(args.wrapper),
    )
    write_json(Path(args.output), preflight)
    print(f"External reviewer preflight written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
