#!/usr/bin/env python3
"""Run an AgentsFlow external reviewer provider.

MVP scope:
- Claude Code CLI provider only;
- subscription-local mode only;
- API-key based Claude usage is forbidden;
- review packet in, normalized reviewer report out;
- raw provider output and invocation metadata are persisted as evidence.
"""
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

# Allow running as a script from repository root without installing a package.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from providers import claude_code  # noqa: E402


SEVERITIES = {"P0", "P1", "P2", "P3", "NOTE"}


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


def validate_provider_config(config: dict[str, Any]) -> None:
    if config.get("provider") != "claude-code":
        raise ValueError("v0.2 MVP external reviewer wrapper supports provider=claude-code only")
    if config.get("kind") != "external_reviewer_provider":
        raise ValueError("provider config kind must be external_reviewer_provider")
    billing = config.get("billing", {}) or {}
    if billing.get("expected_mode") != "subscription-local":
        raise ValueError("Claude provider expected_mode must be subscription-local")
    if billing.get("forbid_api_key_usage") is not True:
        raise ValueError("Claude provider must set forbid_api_key_usage: true")
    fail_env = set(billing.get("fail_if_env_present", []) or [])
    if "ANTHROPIC_API_KEY" not in fail_env:
        raise ValueError("Claude provider must fail if ANTHROPIC_API_KEY is present")
    permissions = config.get("permissions", {}) or {}
    for key in ["write_files", "run_tests", "run_verification_instruments", "run_tools"]:
        if permissions.get(key) is not False:
            raise ValueError(f"Claude reviewer permission {key} must be false in v0.2 MVP")


def enforce_billing_policy(config: dict[str, Any]) -> None:
    billing = config.get("billing", {}) or {}
    for env_name in billing.get("fail_if_env_present", []) or []:
        if os.environ.get(str(env_name)):
            raise RuntimeError(
                f"Forbidden API-key environment variable detected: {env_name}. "
                "AgentsFlow v0.2 allows subscription-local Claude Code CLI only."
            )


def validate_review_packet(packet: dict[str, Any]) -> None:
    required = [
        "agentsflow_version",
        "workflow",
        "run_id",
        "reviewer_role",
        "review_goal",
        "forbidden_actions",
        "output_schema",
    ]
    missing = [key for key in required if key not in packet]
    if missing:
        raise ValueError(f"review packet missing required fields: {', '.join(missing)}")


def render_prompt(packet: dict[str, Any]) -> str:
    return (
        "You are an AgentsFlow external read-only reviewer.\n"
        "Review only the provided packet. Do not request repository access. Do not modify files. "
        "Do not run tests. Return JSON only, conforming to the requested reviewer-report schema.\n\n"
        "All findings must be candidate-unvalidated.\n\n"
        "Review packet:\n"
        + json.dumps(packet, ensure_ascii=False, indent=2)
    )


def normalize_report(raw: dict[str, Any], packet: dict[str, Any], provider: str) -> dict[str, Any]:
    reviewer = raw.get("reviewer") if isinstance(raw.get("reviewer"), dict) else {}
    report = {
        "reviewer": {
            "id": str(reviewer.get("id") or f"{provider}-{packet.get('reviewer_role', 'reviewer')}"),
            "provider": str(reviewer.get("provider") or provider),
            "role": str(reviewer.get("role") or packet.get("reviewer_role", "reviewer")),
            **({"model": reviewer.get("model")} if reviewer.get("model") else {}),
        },
        "summary": str(raw.get("summary") or "No summary provided."),
        "findings": [],
        "requests_for_additional_verification": raw.get("requests_for_additional_verification", []) or [],
        "self_declared_limitations": raw.get("self_declared_limitations", []) or [],
    }
    findings = raw.get("findings", []) or []
    if not isinstance(findings, list):
        raise ValueError("reviewer report findings must be a list")
    for idx, finding in enumerate(findings, start=1):
        if not isinstance(finding, dict):
            raise ValueError(f"finding #{idx} must be an object")
        severity = str(finding.get("severity", "P3"))
        if severity not in SEVERITIES:
            severity = "P3"
        evidence = finding.get("evidence", [])
        if isinstance(evidence, str):
            evidence = [evidence]
        if not isinstance(evidence, list):
            evidence = []
        report["findings"].append(
            {
                "id": str(finding.get("id") or f"F-{idx:03d}"),
                "severity": severity,
                "category": str(finding.get("category", "external-review")),
                "title": str(finding.get("title") or finding.get("claim") or "Untitled finding"),
                "evidence": [str(item) for item in evidence],
                "why_it_matters": str(finding.get("why_it_matters", "")),
                "recommendation": str(finding.get("recommendation", "")),
                "status": "candidate-unvalidated",
            }
        )
    return report


def validate_normalized_report(report: dict[str, Any]) -> None:
    for key in ["reviewer", "summary", "findings"]:
        if key not in report:
            raise ValueError(f"normalized reviewer report missing {key}")
    reviewer = report["reviewer"]
    if not isinstance(reviewer, dict) or not all(k in reviewer for k in ["id", "provider", "role"]):
        raise ValueError("normalized reviewer report has invalid reviewer object")
    if not isinstance(report["findings"], list):
        raise ValueError("normalized reviewer report findings must be a list")
    for finding in report["findings"]:
        if finding.get("status") != "candidate-unvalidated":
            raise ValueError("all external-reviewer findings must be candidate-unvalidated")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="claude-code")
    ap.add_argument("--config", required=True)
    ap.add_argument("--input", required=True, help="review-packet.json")
    ap.add_argument("--output", required=True, help="normalized reviewer-report.json")
    ap.add_argument("--raw-output", help="raw provider output path")
    ap.add_argument("--invocation-output", help="reviewer invocation metadata path")
    ap.add_argument("--mock-response", help="read provider raw JSON from this path instead of invoking CLI")
    args = ap.parse_args()

    started = dt.datetime.now(dt.timezone.utc)
    config_path = Path(args.config)
    packet_path = Path(args.input)
    output_path = Path(args.output)
    raw_path = Path(args.raw_output) if args.raw_output else output_path.with_suffix(".raw.json")
    invocation_path = Path(args.invocation_output) if args.invocation_output else output_path.with_suffix(".invocation.json")

    try:
        config = load_yaml(config_path)
        validate_provider_config(config)
        enforce_billing_policy(config)
        packet = load_json(packet_path)
        validate_review_packet(packet)
        prompt = render_prompt(packet)

        if args.mock_response:
            raw_text = Path(args.mock_response).read_text(encoding="utf-8")
            stderr = ""
            exit_code = 0
            command_display = "mock-response"
        else:
            result = claude_code.invoke(config, prompt, cwd=Path.cwd())
            raw_text = result.stdout
            stderr = result.stderr
            exit_code = result.exit_code
            command_display = result.command_display

        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(raw_text, encoding="utf-8")

        if exit_code != 0:
            raise RuntimeError(f"external reviewer provider failed with exit code {exit_code}: {stderr}")

        raw_json = json.loads(raw_text)
        if not isinstance(raw_json, dict):
            raise ValueError("raw provider output must be a JSON object")
        normalized = normalize_report(raw_json, packet, args.provider)
        validate_normalized_report(normalized)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        finished = dt.datetime.now(dt.timezone.utc)
        invocation = {
            "provider": args.provider,
            "reviewer_role": str(packet.get("reviewer_role", "reviewer")),
            "billing_mode": "subscription-local",
            "api_key_usage_forbidden": True,
            "api_key_env_detected": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "command": command_display,
            "permission_mode": str((config.get("execution", {}) or {}).get("permission_mode", "plan")),
            "output_format": str((config.get("execution", {}) or {}).get("output_format", "json")),
            "max_turns": int((config.get("execution", {}) or {}).get("max_turns", 3)),
            "timeout_seconds": int((config.get("execution", {}) or {}).get("timeout_seconds", 600)),
            "input_hash": sha256_text(packet_path.read_text(encoding="utf-8")),
            "prompt_hash": sha256_text(prompt),
            "schema_hash": sha256_text(str(packet.get("output_schema", ""))),
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "exit_code": exit_code,
            "raw_output_path": str(raw_path),
            "normalized_output_path": str(output_path),
        }
        invocation_path.parent.mkdir(parents=True, exist_ok=True)
        invocation_path.write_text(json.dumps(invocation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"External reviewer report written to {output_path}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"external reviewer failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
