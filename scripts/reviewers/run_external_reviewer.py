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
import tempfile
from pathlib import Path
from typing import Any

import yaml

# Allow running as a script from repository root without installing a package.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from providers import claude_code  # noqa: E402


SEVERITIES = {"P0", "P1", "P2", "P3", "NOTE"}
ROLE_CONTRACT_PREFIXES = ("profiles/reviewer_roles/", ".agentsflow/profiles/reviewer_roles/")


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


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


def validate_provider_config(config: dict[str, Any], requested_provider: str) -> None:
    if requested_provider != "claude-code":
        raise ValueError("v0.2 MVP external reviewer wrapper supports --provider claude-code only")
    if config.get("provider") != "claude-code":
        raise ValueError("v0.2 MVP external reviewer wrapper supports provider=claude-code only")
    if requested_provider != config.get("provider"):
        raise ValueError("--provider must match provider config")
    if config.get("kind") != "external_reviewer_provider":
        raise ValueError("provider config kind must be external_reviewer_provider")
    billing = config.get("billing", {}) or {}
    if billing.get("expected_mode") != "subscription-local":
        raise ValueError("Claude provider expected_mode must be subscription-local")
    if billing.get("forbid_api_key_usage") is not True:
        raise ValueError("Claude provider must set forbid_api_key_usage: true")
    required_forbidden_env = {
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_VERTEX",
    }
    fail_env = set(billing.get("fail_if_env_present", []) or [])
    missing_env = sorted(required_forbidden_env - fail_env)
    if missing_env:
        raise ValueError(f"Claude provider fail_if_env_present missing: {', '.join(missing_env)}")
    permissions = config.get("permissions", {}) or {}
    if permissions.get("read_packet_only") is not True:
        raise ValueError("Claude reviewer permission read_packet_only must be true in v0.2 MVP")
    for key in ["write_files", "run_tests", "run_verification_instruments", "run_tools"]:
        if permissions.get(key) is not False:
            raise ValueError(f"Claude reviewer permission {key} must be false in v0.2 MVP")
    normalization = config.get("normalization", {}) or {}
    if normalization.get("require_schema_validation") is not True:
        raise ValueError("external reviewers must set normalization.require_schema_validation: true")
    execution = config.get("execution", {}) or {}
    if execution.get("command") != "claude":
        raise ValueError("external reviewers must set execution.command: claude")
    if execution.get("output_format") != "json":
        raise ValueError("external reviewers must set execution.output_format: json")
    if execution.get("permission_mode") != "plan":
        raise ValueError("external reviewers must set execution.permission_mode: plan")
    if execution.get("use_bare_mode") is not False:
        raise ValueError("external reviewers must set execution.use_bare_mode: false")
    if execution.get("no_session_persistence") is not True:
        raise ValueError("external reviewers must set execution.no_session_persistence: true")
    context_policy = config.get("context_policy", {}) or {}
    if context_policy.get("start_mode") != "fresh_context":
        raise ValueError("external reviewers must set context_policy.start_mode: fresh_context")
    if context_policy.get("fork_conversation_context") is not False:
        raise ValueError("external reviewers must set context_policy.fork_conversation_context: false")
    if context_policy.get("session_persistence") is not False:
        raise ValueError("external reviewers must set context_policy.session_persistence: false")


def enforce_billing_policy(config: dict[str, Any]) -> None:
    billing = config.get("billing", {}) or {}
    for env_name in billing.get("fail_if_env_present", []) or []:
        if str(env_name) in os.environ:
            raise RuntimeError(
                f"Forbidden API-key environment variable detected: {env_name}. "
                "AgentsFlow v0.2 allows subscription-local Claude Code CLI only."
            )


def validate_json_schema(data: dict[str, Any], schema_path: Path, label: str) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("jsonschema is required for reviewer wrapper validation") from exc
    schema = load_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda err: list(err.path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "<root>"
        raise ValueError(f"{label} schema validation failed at {location}: {first.message}")


def resolve_packet_path(ref: str, root: Path) -> Path:
    path = Path(ref)
    if path.is_absolute():
        return path
    return root / path


def resolve_restricted_role_contract(ref: str, root: Path) -> Path:
    path = Path(ref)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("review packet role_contract must be a relative non-escaping path")
    normalized = path.as_posix()
    if not normalized.startswith(ROLE_CONTRACT_PREFIXES):
        raise ValueError(
            "review packet role_contract must be under profiles/reviewer_roles/ "
            "or .agentsflow/profiles/reviewer_roles/"
        )
    return root / path


def is_placeholder_hash(value: object) -> bool:
    return not isinstance(value, str) or "<" in value or not value.startswith("sha256:")


def is_concrete_sha256(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(char in "0123456789abcdef" for char in digest)


def compare_declared_hash(label: str, declared: object, actual: str) -> None:
    if not is_placeholder_hash(declared) and declared != actual:
        raise ValueError(f"{label} hash mismatch: declared {declared}, computed {actual}")


def validate_prompt_contract_invariants(contract: dict[str, Any]) -> None:
    identity = contract.get("identity", {}) or {}
    profile = identity.get("review_profile")
    composition = identity.get("composition")
    primary_gate = identity.get("primary_gate")
    reviewers = contract.get("reviewer_set", []) or []
    prompts = contract.get("rendered_prompts", []) or []
    prompt_policy = contract.get("prompt_policy", {}) or {}
    reviewer_ids = [str(item.get("instance_id")) for item in reviewers if isinstance(item, dict)]
    prompt_ids = [str(item.get("reviewer")) for item in prompts if isinstance(item, dict)]

    expected = {
        "homogeneous-dual": "homogeneous",
        "homogeneous-plus-focused": "homogeneous-plus-focused",
        "heterogeneous-variable": "heterogeneous",
        "collision-control": "control",
    }.get(str(profile))
    if expected and composition != expected:
        raise ValueError(f"review prompt contract composition must be {expected} for {profile}")
    if sorted(reviewer_ids) != sorted(prompt_ids):
        raise ValueError("review prompt contract reviewer_set and rendered_prompts must match")
    if len(reviewer_ids) != len(set(reviewer_ids)):
        raise ValueError("review prompt contract reviewer_set instance ids must be unique")
    if any(item.get("independent") is not True for item in reviewers if isinstance(item, dict)):
        raise ValueError("review prompt contract reviewers must be independent")

    if profile == "homogeneous-dual":
        if primary_gate is not True or len(reviewers) != 2:
            raise ValueError("homogeneous-dual prompt contract must be a primary gate with exactly two reviewers")
        if any(item.get("role_id") != "generalist" for item in reviewers if isinstance(item, dict)):
            raise ValueError("homogeneous-dual reviewers must resolve to the generalist role")
        for key in ["same_prompt", "same_packet", "same_rubric", "same_output_schema"]:
            if prompt_policy.get(key) is not True:
                raise ValueError(f"homogeneous-dual prompt_policy.{key} must be true")
        for key in ["schema_hash", "rubric_hash", "role_contract_hash"]:
            values = {str(item.get(key)) for item in prompts if isinstance(item, dict)}
            if len(values) != 1:
                raise ValueError(f"homogeneous-dual rendered_prompts must have matching {key}")
        for key in ["shared_prompt_content_hash", "shared_packet_content_hash"]:
            values = [item.get(key) for item in prompts if isinstance(item, dict)]
            if any(not value for value in values):
                raise ValueError(f"homogeneous-dual rendered_prompts must declare {key}")
            if len(set(str(value) for value in values)) != 1:
                raise ValueError(f"homogeneous-dual rendered_prompts must have matching {key}")
            if contract.get("artifact_scope", "run") == "run":
                for value in values:
                    if not is_concrete_sha256(value):
                        raise ValueError(f"run homogeneous-dual rendered_prompts.{key} must be concrete sha256")
        packet_shared_values = {
            item.get("shared_packet_content_hash")
            for item in ((contract.get("inputs") or {}).get("review_packets") or [])
            if isinstance(item, dict)
        }
        if any(not value for value in packet_shared_values):
            raise ValueError("homogeneous-dual review_packets must declare shared_packet_content_hash")
        if len(packet_shared_values) != 1:
            raise ValueError("homogeneous-dual review_packets must have matching shared_packet_content_hash")
        if contract.get("artifact_scope", "run") == "run":
            for value in packet_shared_values:
                if not is_concrete_sha256(value):
                    raise ValueError("run homogeneous-dual shared packet hashes must be concrete sha256")
    elif profile == "homogeneous-plus-focused":
        if primary_gate is not True or not (3 <= len(reviewers) <= 8):
            raise ValueError("homogeneous-plus-focused prompt contract must have three to eight reviewers")
        if "generalist-a" not in reviewer_ids or "generalist-b" not in reviewer_ids:
            raise ValueError("homogeneous-plus-focused requires generalist-a and generalist-b baseline reviewers")
        for key in [
            "baseline_same_prompt",
            "focused_reviewers_require_explicit_focus_zone",
            "focus_zones_may_overlap",
            "all_reviewers_must_report_p0_p1_outside_focus",
        ]:
            if prompt_policy.get(key) is not True:
                raise ValueError(f"homogeneous-plus-focused prompt_policy.{key} must be true")
        focused = [item for item in reviewers if isinstance(item, dict) and item.get("instance_id") not in {"generalist-a", "generalist-b"}]
        if any(not item.get("focus_zone") for item in focused):
            raise ValueError("homogeneous-plus-focused focused reviewers must have focus zones")
    elif profile == "heterogeneous-variable":
        if primary_gate is not True or not (3 <= len(reviewers) <= 8):
            raise ValueError("heterogeneous-variable prompt contract must have three to eight reviewers")
        for key in ["focus_prompts_required", "focus_zones_may_overlap", "all_reviewers_must_report_p0_p1_outside_focus"]:
            if prompt_policy.get(key) is not True:
                raise ValueError(f"heterogeneous-variable prompt_policy.{key} must be true")
        if any(not item.get("focus_zone") for item in reviewers if isinstance(item, dict)):
            raise ValueError("heterogeneous-variable reviewers must have focus zones")
    elif profile == "collision-control":
        if primary_gate is not False or len(reviewers) != 1:
            raise ValueError("collision-control prompt contract must be non-primary with exactly one reviewer")
        collision = contract.get("collision_control")
        if not isinstance(collision, dict) or collision.get("trigger") != "rejected_blocker_finding_collision":
            raise ValueError("collision-control prompt contract requires rejected-blocker collision context")
        for key in [
            "disputed_finding_id",
            "original_severity",
            "source_reviewer_report",
            "orchestrator_rejection_reason",
            "evidence_references_checked",
        ]:
            if not collision.get(key):
                raise ValueError(f"collision-control prompt contract missing {key}")

    if contract.get("artifact_scope", "run") == "run":
        for prompt in prompts:
            if not isinstance(prompt, dict):
                continue
            for key in ["prompt_hash", "packet_hash", "schema_hash", "rubric_hash", "role_contract_hash"]:
                if not is_concrete_sha256(prompt.get(key)):
                    raise ValueError(f"run prompt contract rendered_prompts.{key} must be a concrete sha256")
        for packet in ((contract.get("inputs") or {}).get("review_packets") or []):
            if isinstance(packet, dict) and not is_concrete_sha256(packet.get("packet_hash")):
                raise ValueError("run prompt contract review packet hashes must be concrete sha256 values")


def validate_review_packet(
    packet: dict[str, Any],
    root: Path,
    packet_path: Path,
    packet_schema_path: Path,
) -> dict[str, Any]:
    validate_json_schema(packet, packet_schema_path, "review packet")
    required = [
        "agentsflow_version",
        "workflow",
        "run_id",
        "reviewer_role",
        "review_goal",
        "review_profile",
        "composition",
        "prompt_policy",
        "role_contract",
        "review_prompt_contract",
        "context_policy",
        "forbidden_actions",
        "output_schema",
    ]
    missing = [key for key in required if key not in packet]
    if missing:
        raise ValueError(f"review packet missing required fields: {', '.join(missing)}")
    context_policy = packet.get("context_policy", {}) or {}
    if context_policy.get("start_mode") != "fresh_context":
        raise ValueError("review packet must set context_policy.start_mode: fresh_context")
    if context_policy.get("fork_conversation_context") is not False:
        raise ValueError("review packet must set context_policy.fork_conversation_context: false")
    allowed_sources = set(context_policy.get("allowed_context_sources", []) or [])
    if allowed_sources != {"review_packet", "referenced_artifacts"}:
        raise ValueError(
            "review packet allowed_context_sources must be exactly review_packet and referenced_artifacts"
        )
    forbidden_text = " ".join(str(item).lower() for item in packet.get("forbidden_actions", []) or [])
    for phrase in ["modify files", "run tests", "produce patches", "execute scripts", "update evidence"]:
        if phrase not in forbidden_text:
            raise ValueError(f"review packet forbidden_actions must include: {phrase}")
    reviewer_instance = str(packet.get("reviewer_instance_id") or "")
    composition = str(packet.get("composition") or "")
    if composition == "heterogeneous" and not packet.get("focus_zone"):
        raise ValueError("heterogeneous review packet must include focus_zone")
    if (
        composition == "homogeneous-plus-focused"
        and reviewer_instance not in {"generalist-a", "generalist-b"}
        and not packet.get("focus_zone")
    ):
        raise ValueError("homogeneous-plus-focused focused reviewer packet must include focus_zone")

    role_contract_path = resolve_restricted_role_contract(str(packet["role_contract"]), root)
    if not role_contract_path.exists():
        raise ValueError(f"review packet role_contract does not exist: {packet['role_contract']}")
    role_contract = load_yaml(role_contract_path)
    if role_contract.get("kind") != "reviewer_role":
        raise ValueError("review packet role_contract must have kind: reviewer_role")
    if role_contract.get("name") != packet.get("reviewer_role"):
        raise ValueError("review packet reviewer_role must match role_contract.name")

    role_contract_hash = sha256_file(role_contract_path)
    compare_declared_hash("role_contract", packet.get("role_contract_hash"), role_contract_hash)

    prompt_contract = packet.get("review_prompt_contract", {}) or {}
    prompt_contract_path = resolve_packet_path(str(prompt_contract.get("path", "")), root)
    if not prompt_contract_path.exists():
        raise ValueError(
            f"review packet review_prompt_contract.path does not exist: {prompt_contract.get('path')}"
        )
    prompt_contract_schema_ref = prompt_contract.get("schema")
    prompt_contract_schema_path = resolve_packet_path(str(prompt_contract_schema_ref), root)
    if not prompt_contract_schema_path.exists():
        raise ValueError(f"review packet review_prompt_contract.schema does not exist: {prompt_contract_schema_ref}")
    prompt_contract_data = load_yaml(prompt_contract_path)
    validate_json_schema(prompt_contract_data, prompt_contract_schema_path, "review prompt contract")
    validate_prompt_contract_invariants(prompt_contract_data)
    base_prompt_ref = (prompt_contract_data.get("prompt_components") or {}).get("shared_base_instructions")
    if base_prompt_ref and not resolve_packet_path(str(base_prompt_ref), root).exists():
        raise ValueError(f"review prompt contract shared_base_instructions does not exist: {base_prompt_ref}")
    prompt_contract_hash = sha256_file(prompt_contract_path)

    identity = prompt_contract_data.get("identity", {}) or {}
    for key, packet_key in [
        ("workflow", "workflow"),
        ("run_id", "run_id"),
        ("review_profile", "review_profile"),
        ("composition", "composition"),
    ]:
        if str(identity.get(key)) != str(packet.get(packet_key)):
            raise ValueError(f"review packet {packet_key} must match review prompt contract identity.{key}")

    reviewer_role = str(packet.get("reviewer_role") or "")
    reviewer_set = prompt_contract_data.get("reviewer_set", []) or []
    matching_reviewers = [
        item
        for item in reviewer_set
        if isinstance(item, dict)
        and (
            (reviewer_instance and item.get("instance_id") == reviewer_instance)
            or (not reviewer_instance and item.get("role_id") == reviewer_role)
        )
    ]
    if not matching_reviewers:
        raise ValueError("review packet reviewer must exist in review prompt contract reviewer_set")
    if str(matching_reviewers[0].get("role_id")) != reviewer_role:
        raise ValueError("review packet reviewer_role must match prompt contract reviewer role_id")
    if str(matching_reviewers[0].get("role_contract")) != str(packet.get("role_contract")):
        raise ValueError("review packet role_contract must match prompt contract reviewer role_contract")

    rendered_prompts = prompt_contract_data.get("rendered_prompts", []) or []
    selected_prompt_entries = [
        item
        for item in rendered_prompts
        if isinstance(item, dict) and item.get("reviewer") == (reviewer_instance or reviewer_role)
    ]
    if not selected_prompt_entries:
        raise ValueError("review packet reviewer must have a rendered prompt entry")
    selected_prompt = selected_prompt_entries[0]

    packet_hash = sha256_file(packet_path)
    contract_packets = ((prompt_contract_data.get("inputs") or {}).get("review_packets") or [])
    packet_matches = [
        item
        for item in contract_packets
        if isinstance(item, dict)
        and item.get("reviewer") == (reviewer_instance or reviewer_role)
        and resolve_packet_path(str(item.get("path", "")), root).resolve() == packet_path.resolve()
    ]
    if not packet_matches:
        raise ValueError(
            "review packet must be listed in review prompt contract inputs.review_packets with matching reviewer and path"
        )
    if len(packet_matches) > 1:
        raise ValueError("review packet has duplicate entries in review prompt contract inputs.review_packets")
    compare_declared_hash("review packet", packet_matches[0].get("packet_hash"), packet_hash)

    output_schema_path = resolve_packet_path(str(packet.get("output_schema")), root)
    if not output_schema_path.exists():
        raise ValueError(f"review packet output_schema does not exist: {packet.get('output_schema')}")
    schema_hash = sha256_file(output_schema_path)
    rubric_hash = sha256_text(json.dumps(packet.get("prompt_policy", {}), sort_keys=True))
    compare_declared_hash("rendered prompt packet", selected_prompt.get("packet_hash"), packet_hash)
    compare_declared_hash("rendered prompt schema", selected_prompt.get("schema_hash"), schema_hash)
    compare_declared_hash("rendered prompt role_contract", selected_prompt.get("role_contract_hash"), role_contract_hash)
    compare_declared_hash("rendered prompt rubric", selected_prompt.get("rubric_hash"), rubric_hash)

    return {
        "role_contract_hash": role_contract_hash,
        "review_prompt_contract_hash": prompt_contract_hash,
        "rubric_hash": rubric_hash,
        "input_hash": packet_hash,
        "schema_hash": schema_hash,
        "role_contract": role_contract,
        "artifact_scope": str(prompt_contract_data.get("artifact_scope", "run")),
        "selected_prompt": selected_prompt,
    }


def render_prompt(packet: dict[str, Any], role_contract: dict[str, Any]) -> str:
    return (
        "You are an AgentsFlow external read-only reviewer.\n"
        "Start from zero prior conversation context. Do not use or assume any forked orchestrator context. "
        "Review only the provided packet. Do not request repository access. Do not modify files. "
        "Do not run tests. Do not execute scripts. Do not produce patches. Do not update evidence. "
        "Return JSON only, conforming to the requested reviewer-report schema.\n\n"
        "All findings must be candidate-unvalidated. Report missing mandatory evidence. "
        "Report plausible P0/P1 blockers even outside a focused role. "
        "The main/orchestrating agent validates relevance before findings affect workflow decisions.\n\n"
        "Resolved reviewer role contract:\n"
        + yaml.safe_dump(role_contract, sort_keys=False)
        + "\n"
        "Review packet:\n"
        + json.dumps(packet, ensure_ascii=False, indent=2)
    )


def normalize_report(raw: dict[str, Any], packet: dict[str, Any], provider: str) -> dict[str, Any]:
    reviewer = raw.get("reviewer") if isinstance(raw.get("reviewer"), dict) else {}
    raw_provider = reviewer.get("provider")
    if raw_provider and str(raw_provider) != provider:
        raise ValueError("raw reviewer provider must match requested provider")
    raw_role = reviewer.get("role")
    if raw_role and str(raw_role) != str(packet.get("reviewer_role")):
        raise ValueError("raw reviewer role must match review packet reviewer_role")
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
            raise ValueError(f"finding #{idx} has invalid severity: {severity}")
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


def validate_normalized_report_schema(report: dict[str, Any], schema_path: Path) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError(
            "jsonschema is required when normalization.require_schema_validation is true"
        ) from exc
    schema = load_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(report), key=lambda err: list(err.path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "<root>"
        raise ValueError(
            f"normalized reviewer report schema validation failed at {location}: {first.message}"
        )


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
    stderr_path = output_path.with_suffix(".stderr.txt")
    failure_invocation: dict[str, Any] | None = None

    try:
        config = load_yaml(config_path)
        validate_provider_config(config, args.provider)
        enforce_billing_policy(config)
        packet = load_json(packet_path)
        packet_schema_ref = (config.get("inputs", {}) or {}).get("review_packet_schema")
        if not packet_schema_ref:
            raise ValueError("provider config inputs.review_packet_schema is required")
        packet_schema_path = resolve_packet_path(str(packet_schema_ref), Path.cwd())
        packet_hashes = validate_review_packet(packet, Path.cwd(), packet_path, packet_schema_path)
        prompt = render_prompt(packet, packet_hashes["role_contract"])
        prompt_hash = sha256_text(prompt)
        selected_prompt_hash = packet_hashes["selected_prompt"].get("prompt_hash")
        if packet_hashes["artifact_scope"] == "run" or not is_placeholder_hash(selected_prompt_hash):
            compare_declared_hash("rendered prompt", selected_prompt_hash, prompt_hash)
        if not args.mock_response and packet_hashes["artifact_scope"] != "run":
            raise ValueError("live external reviewer invocation requires review prompt contract artifact_scope: run")

        if args.mock_response:
            raw_text = Path(args.mock_response).read_text(encoding="utf-8")
            stderr = ""
            exit_code = 0
            command_display = "mock-response"
        else:
            with tempfile.TemporaryDirectory(prefix="agentsflow-reviewer-") as reviewer_cwd:
                result = claude_code.invoke(config, prompt, cwd=Path(reviewer_cwd))
            raw_text = result.stdout
            stderr = result.stderr
            exit_code = result.exit_code
            command_display = result.command_display

        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(raw_text, encoding="utf-8")
        failure_invocation = {
            "provider": args.provider,
            "reviewer_role": str(packet.get("reviewer_role", "reviewer")),
            "billing_mode": "subscription-local",
            "api_key_usage_forbidden": True,
            "context_policy": {
                "start_mode": "fresh_context",
                "fork_conversation_context": False,
                "session_persistence": False,
                "input_mode": "review_packet",
            },
            "forbidden_env_checked": [
                str(item)
                for item in (config.get("billing", {}) or {}).get("fail_if_env_present", []) or []
            ],
            "command": command_display,
            "permission_mode": str((config.get("execution", {}) or {}).get("permission_mode", "plan")),
            "output_format": str((config.get("execution", {}) or {}).get("output_format", "json")),
            "max_turns": int((config.get("execution", {}) or {}).get("max_turns", 3)),
            "timeout_seconds": int((config.get("execution", {}) or {}).get("timeout_seconds", 600)),
            "input_hash": packet_hashes["input_hash"],
            "prompt_hash": prompt_hash,
            "review_prompt_contract_hash": packet_hashes["review_prompt_contract_hash"],
            "role_contract_hash": packet_hashes["role_contract_hash"],
            "rubric_hash": packet_hashes["rubric_hash"],
            "schema_hash": packet_hashes["schema_hash"],
            "started_at": started.isoformat(),
            "exit_code": exit_code,
            "raw_output_path": str(raw_path),
            "stderr_path": str(stderr_path) if stderr else "",
            "normalized_output_path": str(output_path),
        }

        if exit_code != 0:
            finished = dt.datetime.now(dt.timezone.utc)
            stderr_path.parent.mkdir(parents=True, exist_ok=True)
            stderr_path.write_text(stderr, encoding="utf-8")
            invocation_path.parent.mkdir(parents=True, exist_ok=True)
            invocation = dict(failure_invocation)
            invocation["finished_at"] = finished.isoformat()
            invocation["stderr_path"] = str(stderr_path)
            invocation_path.write_text(json.dumps(invocation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            raise RuntimeError(f"external reviewer provider failed with exit code {exit_code}: {stderr}")

        raw_json = json.loads(raw_text)
        if not isinstance(raw_json, dict):
            raise ValueError("raw provider output must be a JSON object")
        normalized = normalize_report(raw_json, packet, args.provider)
        normalization = config.get("normalization", {}) or {}
        if normalization.get("require_schema_validation") is True:
            schema_ref = (config.get("outputs", {}) or {}).get("reviewer_report_schema")
            if not schema_ref:
                raise ValueError(
                    "require_schema_validation is true but outputs.reviewer_report_schema is missing"
                )
            schema_path = Path(str(schema_ref))
            if not schema_path.is_absolute():
                schema_path = Path.cwd() / schema_path
            validate_normalized_report_schema(normalized, schema_path)
        validate_normalized_report(normalized)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if stderr:
            stderr_path.parent.mkdir(parents=True, exist_ok=True)
            stderr_path.write_text(stderr, encoding="utf-8")

        finished = dt.datetime.now(dt.timezone.utc)
        invocation = dict(failure_invocation)
        invocation["finished_at"] = finished.isoformat()
        invocation["stderr_path"] = str(stderr_path) if stderr else ""
        invocation_path.parent.mkdir(parents=True, exist_ok=True)
        invocation_path.write_text(json.dumps(invocation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"External reviewer report written to {output_path}")
        return 0
    except Exception as exc:  # noqa: BLE001
        if failure_invocation is not None and not invocation_path.exists():
            finished = dt.datetime.now(dt.timezone.utc)
            invocation = dict(failure_invocation)
            invocation["finished_at"] = finished.isoformat()
            invocation["failure_stage"] = "provider_output_processing"
            invocation["failure_message"] = str(exc)
            invocation_path.parent.mkdir(parents=True, exist_ok=True)
            invocation_path.write_text(
                json.dumps(invocation, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        print(f"external reviewer failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
