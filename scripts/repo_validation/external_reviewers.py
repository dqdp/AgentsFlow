from __future__ import annotations

from pathlib import Path

from .common import parse_yaml


def validate_external_review_provider(path: Path) -> list[str]:
    errors: list[str] = []
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"{path}: external reviewer provider config is not a mapping"]
    if data.get("provider") != "claude-code":
        errors.append(f"{path}: v0.2 external reviewer provider must be claude-code")
        return errors
    billing = data.get("billing", {}) or {}
    if billing.get("expected_mode") != "subscription-local":
        errors.append(f"{path}: claude-code expected_mode must be subscription-local")
    if billing.get("forbid_api_key_usage") is not True:
        errors.append(f"{path}: claude-code must set forbid_api_key_usage: true")
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
        errors.append(f"{path}: claude-code fail_if_env_present missing: {', '.join(missing_env)}")
    permissions = data.get("permissions", {}) or {}
    if permissions.get("read_packet_only") is not True:
        errors.append(f"{path}: claude-code permission read_packet_only must be true")
    for key in ["write_files", "run_tests", "run_verification_instruments", "run_tools"]:
        if permissions.get(key) is not False:
            errors.append(f"{path}: claude-code permission {key} must be false")
    normalization = data.get("normalization", {}) or {}
    if normalization.get("require_schema_validation") is not True:
        errors.append(f"{path}: claude-code normalization.require_schema_validation must be true")
    execution = data.get("execution", {}) or {}
    if execution.get("command") != "claude":
        errors.append(f"{path}: claude-code execution.command must be claude")
    if execution.get("sandbox_mode") != "require_escalated":
        errors.append(f"{path}: claude-code execution.sandbox_mode must be require_escalated")
    if execution.get("output_format") != "json":
        errors.append(f"{path}: claude-code execution.output_format must be json")
    if execution.get("permission_mode") != "plan":
        errors.append(f"{path}: claude-code execution.permission_mode must be plan")
    if execution.get("tools") != "":
        errors.append(f'{path}: claude-code execution.tools must be ""')
    if "model" not in execution:
        errors.append(f"{path}: claude-code execution.model must be declared as opus")
    elif execution.get("model") != "opus":
        errors.append(f"{path}: claude-code execution.model must default to opus")
    if "effort" not in execution:
        errors.append(f"{path}: claude-code execution.effort must be declared as max")
    elif execution.get("effort") != "max":
        errors.append(f"{path}: claude-code execution.effort must default to max")
    if execution.get("use_bare_mode") is not False:
        errors.append(f"{path}: claude-code execution.use_bare_mode must be false")
    if execution.get("no_session_persistence") is not True:
        errors.append(f"{path}: claude-code execution.no_session_persistence must be true")
    context_policy = data.get("context_policy", {}) or {}
    if context_policy.get("start_mode") != "fresh_context":
        errors.append(f"{path}: claude-code context_policy.start_mode must be fresh_context")
    if context_policy.get("fork_conversation_context") is not False:
        errors.append(f"{path}: claude-code context_policy.fork_conversation_context must be false")
    if context_policy.get("session_persistence") is not False:
        errors.append(f"{path}: claude-code context_policy.session_persistence must be false")
    outputs = data.get("outputs", {}) or {}
    if outputs.get("reviewer_report_schema") != "schemas/reviewer-report.schema.json":
        errors.append(f"{path}: external provider must output schemas/reviewer-report.schema.json")
    return errors
