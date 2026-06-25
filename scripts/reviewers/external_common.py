from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from providers import claude_code  # noqa: E402
from repo_validation.common import (  # noqa: E402
    parse_json_mapping as load_json,
    raise_schema_validation_error,
    sha256_text,
)


SEVERITIES = {"P0", "P1", "P2", "P3", "NOTE"}
DEFAULT_CLAUDE_MODEL = claude_code.DEFAULT_MODEL
DEFAULT_CLAUDE_EFFORT = claude_code.DEFAULT_EFFORT
ALLOWED_CLAUDE_EFFORTS = {"low", "medium", "high", "xhigh", "max"}


def strip_json_markdown_fence(value: str) -> str:
    text = value.strip()
    decoder = json.JSONDecoder()

    def decode_report_object(candidate: str) -> str | None:
        for idx, char in enumerate(candidate):
            if char != "{":
                continue
            try:
                parsed, end = decoder.raw_decode(candidate[idx:])
            except json.JSONDecodeError:
                continue
            if is_reviewer_report_like(parsed):
                return candidate[idx : idx + end].strip()
        return None

    def decode_first_object(candidate: str) -> str | None:
        for idx, char in enumerate(candidate):
            if char != "{":
                continue
            try:
                _, end = decoder.raw_decode(candidate[idx:])
            except json.JSONDecodeError:
                continue
            return candidate[idx : idx + end].strip()
        return None

    if not text.startswith("```"):
        for marker in ("```json", "```"):
            if marker in text:
                extracted = decode_report_object(text.split(marker, 1)[1])
                if extracted:
                    return extracted
        extracted = decode_report_object(text)
        if extracted:
            return extracted
        extracted = decode_first_object(text) if text.startswith("{") else None
        if extracted:
            return extracted
        return text
    lines = text.splitlines()
    if not lines or not lines[0].strip().startswith("```"):
        return text
    extracted = decode_report_object("\n".join(lines[1:]))
    if extracted:
        return extracted
    return text


def is_reviewer_report_like(raw: object) -> bool:
    if not isinstance(raw, dict):
        return False
    if not isinstance(raw.get("summary"), str):
        return False
    if not isinstance(raw.get("findings"), list):
        return False
    reviewer = raw.get("reviewer")
    if isinstance(reviewer, dict):
        return True
    return any(
        [
            isinstance(raw.get("review_context"), dict),
            bool(raw.get("reviewer_role")),
            bool(raw.get("provider")),
        ]
    )


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
    if permissions.get("write_files") is not False:
        raise ValueError("Claude reviewer permission write_files must be false in v0.2 MVP")
    if permissions.get("run_tests") is not False:
        raise ValueError("Claude reviewer permission run_tests must be false in v0.2 MVP")
    if permissions.get("run_verification_instruments") is not False:
        raise ValueError("Claude reviewer permission run_verification_instruments must be false in v0.2 MVP")
    if permissions.get("run_tools") is not False:
        raise ValueError("Claude reviewer permission run_tools must be false in v0.2 MVP")
    normalization = config.get("normalization", {}) or {}
    if normalization.get("require_schema_validation") is not True:
        raise ValueError("external reviewers must set normalization.require_schema_validation: true")
    execution = config.get("execution", {}) or {}
    if execution.get("command") != "claude":
        raise ValueError("external reviewers must set execution.command: claude")
    if execution.get("sandbox_mode") != "require_escalated":
        raise ValueError("Claude Code external reviewers must set execution.sandbox_mode: require_escalated")
    if execution.get("output_format") != "json":
        raise ValueError("external reviewers must set execution.output_format: json")
    if execution.get("permission_mode") != "default":
        raise ValueError("external reviewers must set execution.permission_mode: default")
    if execution.get("model") != DEFAULT_CLAUDE_MODEL:
        raise ValueError("external reviewers must default execution.model to opus")
    if execution.get("effort") != DEFAULT_CLAUDE_EFFORT:
        raise ValueError("external reviewers must default execution.effort to max")
    if str(execution.get("effort")) not in ALLOWED_CLAUDE_EFFORTS:
        raise ValueError("external reviewers execution.effort must be one of low, medium, high, xhigh, max")
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
    forbidden_env = [str(item) for item in billing.get("fail_if_env_present", []) or []]
    for env_name in forbidden_env:
        if env_name in os.environ:
            raise RuntimeError(
                f"Forbidden API-key environment variable detected: {env_name}. "
                "AgentsFlow v0.2 allows subscription-local Claude Code CLI only."
            )
    for settings_path, env_name in find_forbidden_claude_settings_env(forbidden_env, Path.cwd()):
        raise RuntimeError(
            f"Forbidden Claude API/proxy setting detected in {settings_path}: env.{env_name}. "
            "AgentsFlow v0.2 allows subscription-local Claude Code CLI only."
        )


def claude_settings_paths(root: Path) -> list[Path]:
    candidates: list[Path] = []
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if config_dir:
        config_root = Path(config_dir).expanduser()
        candidates.extend([config_root / "settings.json", config_root / "__settings.json"])
    user_root = Path.home() / ".claude"
    candidates.extend([user_root / "settings.json", user_root / "__settings.json"])
    candidates.extend([root / ".claude" / "settings.json", root / ".claude" / "settings.local.json"])
    if sys.platform == "darwin":
        managed_root = Path("/Library/Application Support/ClaudeCode")
    elif os.name == "nt":
        managed_root = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "ClaudeCode"
    else:
        managed_root = Path("/etc/claude-code")
    candidates.append(managed_root / "managed-settings.json")
    dropin_root = managed_root / "managed-settings.d"
    if dropin_root.exists():
        candidates.extend(sorted(dropin_root.glob("*.json")))
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key not in seen:
            unique.append(path)
            seen.add(key)
    return unique


def find_forbidden_claude_settings_env(forbidden_env: list[str], root: Path) -> list[tuple[Path, str]]:
    forbidden = set(forbidden_env)
    hits: list[tuple[Path, str]] = []
    for path in claude_settings_paths(root):
        if not path.is_file():
            continue
        try:
            data = load_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        env = data.get("env")
        if not isinstance(env, dict):
            continue
        for env_name in sorted(forbidden.intersection(str(key) for key in env.keys())):
            hits.append((path, env_name))
    return hits


def provider_output_diagnostic(raw: object) -> dict[str, Any]:
    diagnostic: dict[str, Any] = {"top_level_type": type(raw).__name__}
    if not isinstance(raw, dict):
        return diagnostic
    diagnostic["top_level_keys"] = sorted(str(key) for key in raw.keys())
    diagnostic["is_reviewer_report_like"] = is_reviewer_report_like(raw)
    if raw.get("type") == "result" and "result" in raw:
        result = raw.get("result")
        diagnostic["claude_envelope"] = {
            "subtype": raw.get("subtype"),
            "is_error": raw.get("is_error"),
            "result_type": type(result).__name__,
        }
        if isinstance(result, str):
            diagnostic["claude_envelope"]["result_length"] = len(result)
            diagnostic["claude_envelope"]["result_hash"] = sha256_text(result)
            try:
                parsed = json.loads(strip_json_markdown_fence(result))
            except json.JSONDecodeError:
                diagnostic["claude_envelope"]["embedded_reviewer_report_json"] = False
            else:
                diagnostic["claude_envelope"]["embedded_reviewer_report_json"] = is_reviewer_report_like(parsed)
        elif isinstance(result, dict):
            diagnostic["claude_envelope"]["embedded_reviewer_report_json"] = is_reviewer_report_like(result)
    return diagnostic


def require_reviewer_report_shape(raw: dict[str, Any], provider_name: str) -> None:
    if not is_reviewer_report_like(raw):
        raise ValueError(f"{provider_name} provider result must contain reviewer-report JSON")


def extract_provider_reviewer_report(raw: dict[str, Any], provider: str) -> dict[str, Any]:
    if provider != "claude-code":
        return raw
    if raw.get("type") != "result" or "result" not in raw:
        require_reviewer_report_shape(raw, "Claude Code")
        return raw
    result = raw.get("result")
    if raw.get("is_error") is True:
        raise ValueError(f"Claude Code provider returned an error result: {str(result).strip()}")
    if isinstance(result, dict):
        require_reviewer_report_shape(result, "Claude Code")
        return result
    if not isinstance(result, str) or not result.strip():
        raise ValueError("Claude Code provider result must contain reviewer-report JSON")
    try:
        parsed = json.loads(strip_json_markdown_fence(result))
    except json.JSONDecodeError as exc:
        raise ValueError("Claude Code provider result must contain reviewer-report JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Claude Code provider result must contain a JSON object")
    require_reviewer_report_shape(parsed, "Claude Code")
    return parsed


def normalization_method(raw: dict[str, Any], provider: str) -> str:
    if provider == "claude-code" and raw.get("type") == "result":
        return "deterministic-extraction"
    return "native-json"


def provider_failure_detail(raw_text: str, stderr: str) -> str:
    if stderr.strip():
        return stderr.strip()
    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError:
        return raw_text.strip()
    if isinstance(raw, dict):
        result = raw.get("result")
        if result:
            return str(result).strip()
    return raw_text.strip()


def provider_invocation_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    model_usage = raw.get("modelUsage")
    if isinstance(model_usage, dict):
        metadata["provider_model_usage"] = model_usage
        metadata["provider_models_used"] = sorted(str(key) for key in model_usage.keys())
    if "total_cost_usd" in raw:
        metadata["provider_total_cost_usd"] = raw.get("total_cost_usd")
    usage = raw.get("usage")
    if isinstance(usage, dict):
        if "service_tier" in usage:
            metadata["provider_service_tier"] = usage.get("service_tier")
        if "speed" in usage:
            metadata["provider_speed"] = usage.get("speed")
    if "service_tier" in raw and "provider_service_tier" not in metadata:
        metadata["provider_service_tier"] = raw.get("service_tier")
    if "speed" in raw and "provider_speed" not in metadata:
        metadata["provider_speed"] = raw.get("speed")
    return metadata


def normalize_additional_verification_requests(value: object) -> list[dict[str, Any]]:
    if not value:
        return []
    if not isinstance(value, list):
        raise ValueError("requests_for_additional_verification must be a list")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(value, start=1):
        if isinstance(item, dict):
            normalized.append(item)
        elif isinstance(item, str):
            normalized.append({"id": f"REQUEST-{index:03d}", "request": item})
        else:
            raise ValueError(f"requests_for_additional_verification #{index} must be an object or string")
    return normalized


def normalize_report(raw: dict[str, Any], packet: dict[str, Any], provider: str) -> dict[str, Any]:
    reviewer = raw.get("reviewer") if isinstance(raw.get("reviewer"), dict) else {}
    reviewer_instance = str(packet.get("reviewer_instance_id") or packet.get("reviewer_role") or "reviewer")
    raw_provider = reviewer.get("provider")
    if raw_provider and str(raw_provider) != provider:
        raise ValueError("raw reviewer provider must match requested provider")
    raw_role = reviewer.get("role")
    if raw_role and str(raw_role) != str(packet.get("reviewer_role")):
        raise ValueError("raw reviewer role must match review packet reviewer_role")
    report = {
        "reviewer": {
            "id": str(reviewer.get("id") or f"{provider}-{reviewer_instance}"),
            "provider": str(reviewer.get("provider") or provider),
            "role": str(reviewer.get("role") or packet.get("reviewer_role", "reviewer")),
            **({"model": reviewer.get("model")} if reviewer.get("model") else {}),
        },
        "review_context": {
            "run_id": str(packet.get("run_id", "")),
            "material_change_id": str(packet.get("material_change_id", "")),
            "review_packet_path": str(packet.get("review_packet_path", "")),
            "reviewer_instance_id": reviewer_instance,
        },
        "summary": str(raw.get("summary") or "No summary provided."),
        "findings": [],
        "requests_for_additional_verification": normalize_additional_verification_requests(
            raw.get("requests_for_additional_verification", []) or []
        ),
        "self_declared_limitations": raw.get("self_declared_limitations", []) or [],
    }

    def normalize_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        return str(value)

    optional_finding_fields = [
        "validated_severity",
        "blocker_path",
        "acceptance_impact",
        "mandatory_evidence_gap",
        "validation_rationale",
        "calibration_reason",
        "no_blocker_path_reason",
    ]
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
        normalized_finding = {
            "id": str(finding.get("id") or f"F-{idx:03d}"),
            "severity": severity,
            "category": str(
                finding.get("category")
                or finding.get("focus_area")
                or finding.get("risk_surface")
                or "external-review"
            ),
            "title": normalize_text(finding.get("title") or finding.get("claim") or "Untitled finding"),
            "evidence": [str(item) for item in evidence],
            "why_it_matters": normalize_text(
                finding.get("why_it_matters")
                or finding.get("rationale")
                or finding.get("description")
                or ""
            ),
            "recommendation": normalize_text(finding.get("recommendation") or finding.get("suggested_action") or ""),
            "status": "candidate-unvalidated",
        }
        for field in optional_finding_fields:
            if field in finding:
                value = finding[field]
                normalized_finding[field] = normalize_text(value) if field != "mandatory_evidence_gap" else bool(value)
        report["findings"].append(normalized_finding)
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
    raise_schema_validation_error(report, load_json(schema_path), "normalized reviewer report")


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()
