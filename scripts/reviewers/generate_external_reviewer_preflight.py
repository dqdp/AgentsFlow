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

from run_external_reviewer import enforce_billing_policy, validate_provider_config  # noqa: E402


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
    fingerprint = {
        "provider_config_hash": sha256_file(config_path),
        "wrapper_hash": sha256_file(wrapper_path),
        "schema_hash": sha256_file(output_schema_path),
        "prompt_contract_hash": sha256_file(review_prompt_contract_path),
        "role_contract_hash": sha256_file(role_contract_path),
        "rubric_hash": sha256_file(rubric_source_path),
        "forbidden_env_fingerprint": sha256_text(json.dumps(forbidden_payload, sort_keys=True)),
        "permission_mode": str(execution["permission_mode"]),
        "sandbox_mode": str(execution["sandbox_mode"]),
        "provider_transport_mode": str(execution.get("prompt_transport", "stdin")),
    }
    return {
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
