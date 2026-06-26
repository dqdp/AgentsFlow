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
    if permissions.get("read_packet_only") is not False:
        errors.append(f"{path}: claude-code permission read_packet_only must be false")
    if permissions.get("read_review_bundle_only") is not True:
        errors.append(f"{path}: claude-code permission read_review_bundle_only must be true")
    for key in ["write_files", "run_tests", "run_verification_instruments", "run_tools"]:
        if permissions.get(key) is not False:
            errors.append(f"{path}: claude-code permission {key} must be false")
    normalization = data.get("normalization", {}) or {}
    if normalization.get("require_schema_validation") is not True:
        errors.append(f"{path}: claude-code normalization.require_schema_validation must be true")
    if not isinstance(normalization.get("preserve_raw_output"), bool):
        errors.append(f"{path}: claude-code normalization.preserve_raw_output must be explicitly true or false")
    execution = data.get("execution", {}) or {}
    if execution.get("command") != "claude":
        errors.append(f"{path}: claude-code execution.command must be claude")
    if execution.get("sandbox_mode") != "require_escalated":
        errors.append(f"{path}: claude-code execution.sandbox_mode must be require_escalated")
    if execution.get("output_format") != "json":
        errors.append(f"{path}: claude-code execution.output_format must be json")
    if execution.get("permission_mode") != "default":
        errors.append(f"{path}: claude-code execution.permission_mode must be default")
    prompt_transport = str(execution.get("prompt_transport", "stdin"))
    tools = str(execution.get("tools", ""))
    if prompt_transport == "file":
        if tools != "Read":
            errors.append(f'{path}: claude-code file prompt transport must set execution.tools to "Read"')
    elif prompt_transport == "stdin":
        if tools != "":
            errors.append(f'{path}: claude-code stdin prompt transport must set execution.tools to ""')
    else:
        errors.append(f"{path}: claude-code execution.prompt_transport must be stdin or file")
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
    if context_policy.get("input_mode") != "review_bundle":
        errors.append(f"{path}: claude-code context_policy.input_mode must be review_bundle")
    inputs = data.get("inputs", {}) or {}
    if inputs.get("review_request_schema") != "schemas/external-review-lite-request.schema.json":
        errors.append(f"{path}: external provider must input schemas/external-review-lite-request.schema.json")
    if "review_packet_schema" in inputs:
        errors.append(f"{path}: external provider must not require review_packet_schema")
    outputs = data.get("outputs", {}) or {}
    if outputs.get("reviewer_report_schema") != "schemas/reviewer-report.schema.json":
        errors.append(f"{path}: external provider must output schemas/reviewer-report.schema.json")
    if outputs.get("invocation_metadata_schema") != "schemas/external-review-lite-invocation.schema.json":
        errors.append(f"{path}: external provider must output schemas/external-review-lite-invocation.schema.json")
    return errors
