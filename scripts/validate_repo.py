#!/usr/bin/env python3
"""Validate basic AgentsFlow repository integrity.

v0.1.13 validates:
- YAML/JSON parseability;
- workflow schema and implementation-phase topology;
- workflow references to skills/scripts/templates/packs/review topologies;
- upstream gate contract manifests and generic runner paths;
- behavior binding manifests;
- project-overlay example bindings.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import jsonschema
import yaml

VALID_BINDING_CHECK_TYPES = {
    "test", "script", "bdd_runner", "eval", "trace_assertion", "log_assertion",
    "static_analysis", "dynamic_analysis", "benchmark", "security_scan",
    "manual_evidence", "external_tool",
}

VALID_GATE_INSTRUMENT_TYPES = {
    "tests",
    "deterministic_script",
    "bdd_runner",
    "static_analysis",
    "dynamic_analysis",
    "debugger",
    "trace_analysis",
    "log_analysis",
    "network_traffic_analysis",
    "profiler",
    "fuzzer",
    "benchmark",
    "security_scanner",
    "domain_tool",
    "manual_evidence_check",
    "schema_validation",
    "fusion_protocol_check",
    "review_protocol_check",
}

ROLE_CONTRACT_PREFIXES = ("profiles/reviewer_roles/", ".agentsflow/profiles/reviewer_roles/")
MVP_WORKFLOWS = {
    "project-initialization",
    "big-feature-contract-first",
    "bugfix-regression-capture",
    "review-only-fusion",
    "new-project-spec-first",
}


def parse_yaml(path: Path) -> object:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"YAML parse error in {path}: {exc}") from exc


def parse_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"JSON parse error in {path}: {exc}") from exc


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


def validate_gate_manifest(root: Path, path: Path) -> list[str]:
    errors: list[str] = []
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"Gate {path} is not a mapping"]
    required = ["id", "name", "kind", "purpose", "runner", "inputs", "instruments", "outputs", "result_states", "pass_policy"]
    for key in required:
        if key not in data:
            errors.append(f"{path}: missing required gate field: {key}")
    if data.get("kind") != "gate":
        errors.append(f"{path}: kind must be 'gate'")
    runner = data.get("runner")
    if runner:
        runner_path = root / str(runner)
        if not runner_path.exists():
            errors.append(f"{path}: generic runner path does not exist: {runner}")
    if data.get("binding_level") and data.get("binding_level") != "upstream_gate_contract":
        errors.append(f"{path}: upstream gates should use binding_level=upstream_gate_contract")
    instruments = data.get("instruments", []) or []
    if not isinstance(instruments, list) or not instruments:
        errors.append(f"{path}: instruments must be a non-empty list")
    else:
        for idx, inst in enumerate(instruments):
            if not isinstance(inst, dict):
                errors.append(f"{path}: instrument #{idx} is not a mapping")
                continue
            if "id" not in inst or "type" not in inst:
                errors.append(f"{path}: instrument #{idx} must include id and type")
    pass_policy = data.get("pass_policy", {}) or {}
    if isinstance(pass_policy, dict):
        for key in ["fail_on", "inconclusive_on"]:
            if key not in pass_policy:
                errors.append(f"{path}: pass_policy missing {key}")
    else:
        errors.append(f"{path}: pass_policy must be a mapping")
    return errors


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
    if execution.get("output_format") != "json":
        errors.append(f"{path}: claude-code execution.output_format must be json")
    if execution.get("permission_mode") != "plan":
        errors.append(f"{path}: claude-code execution.permission_mode must be plan")
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


def validate_behavior_binding(path: Path) -> list[str]:
    errors: list[str] = []
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"{path}: behavior binding is not a mapping"]
    for key in ["version", "contract", "bindings"]:
        if key not in data:
            errors.append(f"{path}: missing required field {key}")
    bindings = data.get("bindings", []) or []
    if not isinstance(bindings, list):
        return errors + [f"{path}: bindings must be a list"]
    seen: set[str] = set()
    for idx, item in enumerate(bindings):
        if not isinstance(item, dict):
            errors.append(f"{path}: binding #{idx} must be a mapping")
            continue
        bid = str(item.get("id", f"#{idx}"))
        if bid in seen:
            errors.append(f"{path}: duplicate binding id {bid}")
        seen.add(bid)
        for key in ["id", "scenario", "required", "checks", "gates"]:
            if key not in item:
                errors.append(f"{path}: binding {bid} missing {key}")
        if item.get("required") is True and not item.get("checks"):
            errors.append(f"{path}: required binding {bid} has no checks")
        if item.get("required") is True and not item.get("gates"):
            errors.append(f"{path}: required binding {bid} has no gates")
        for check in item.get("checks", []) or []:
            if not isinstance(check, dict):
                errors.append(f"{path}: binding {bid} check must be a mapping")
                continue
            ctype = check.get("type")
            if ctype not in VALID_BINDING_CHECK_TYPES:
                errors.append(f"{path}: binding {bid} has unknown check type {ctype}")
            if ctype != "manual_evidence" and not (check.get("command") or check.get("target")):
                errors.append(f"{path}: binding {bid} check {check.get('id')} lacks command/target")
    return errors


def validate_behavior_binding_gate_refs(path: Path, known_gates: set[str]) -> list[str]:
    errors: list[str] = []
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return errors
    for item in data.get("bindings", []) or []:
        if not isinstance(item, dict):
            continue
        bid = item.get("id", "<unknown>")
        for gate in item.get("gates", []) or []:
            if isinstance(gate, dict):
                gate_id = gate.get("id") or gate.get("gate")
            else:
                gate_id = gate
            if gate_id and str(gate_id) not in known_gates:
                errors.append(f"{path}: binding {bid} references unknown gate: {gate_id}")
    return errors


def validate_review_manifest_collection(root: Path) -> list[str]:
    errors: list[str] = []
    role_schema = parse_json(root / "schemas" / "reviewer-role.schema.json")
    profile_schema = parse_json(root / "schemas" / "review-profile.schema.json")
    role_names = collect_yaml_manifest_names(root, "profiles/reviewer_roles")

    for role_path in (root / "profiles" / "reviewer_roles").glob("*.yaml"):
        data = parse_yaml(role_path) or {}
        if not isinstance(data, dict):
            errors.append(f"{role_path}: reviewer role must be a mapping")
            continue
        errors.extend(validate_against_schema(role_path, data, role_schema))

    for profile_path in (root / "profiles" / "review_profiles").glob("*.yaml"):
        data = parse_yaml(profile_path) or {}
        if not isinstance(data, dict):
            errors.append(f"{profile_path}: review profile must be a mapping")
            continue
        errors.extend(validate_against_schema(profile_path, data, profile_schema))
        refs = set(data.get("reviewer_role_contracts", []) or [])
        missing = sorted(refs - role_names)
        if missing:
            errors.append(f"{profile_path}: unknown reviewer role contract(s): {', '.join(missing)}")
        if data.get("composition") == "heterogeneous" and int(data.get("max_reviewers", 0)) > 8:
            errors.append(f"{profile_path}: heterogeneous review profile max_reviewers must be <= 8")
        if data.get("primary_gate") is True and int(data.get("min_reviewers", 0)) < 2:
            errors.append(f"{profile_path}: primary review profile must require at least two reviewers")
    return errors


def validate_review_prompt_contract_invariants(
    root: Path,
    path: Path,
    data: dict,
    check_references: bool,
) -> list[str]:
    errors: list[str] = []
    identity = data.get("identity", {}) or {}
    profile = identity.get("review_profile")
    composition = identity.get("composition")
    primary_gate = identity.get("primary_gate")
    reviewers = data.get("reviewer_set", []) or []
    prompts = data.get("rendered_prompts", []) or []
    prompt_policy = data.get("prompt_policy", {}) or {}
    reviewer_ids = [str(item.get("instance_id")) for item in reviewers if isinstance(item, dict)]
    prompt_ids = [str(item.get("reviewer")) for item in prompts if isinstance(item, dict)]

    expected_composition = {
        "homogeneous-dual": "homogeneous",
        "homogeneous-plus-focused": "homogeneous-plus-focused",
        "heterogeneous-variable": "heterogeneous",
        "collision-control": "control",
    }.get(str(profile))
    if expected_composition and composition != expected_composition:
        errors.append(f"{path}: composition must be {expected_composition} for {profile}")
    if sorted(reviewer_ids) != sorted(prompt_ids):
        errors.append(f"{path}: reviewer_set and rendered_prompts must list the same reviewers")
    if len(reviewer_ids) != len(set(reviewer_ids)):
        errors.append(f"{path}: reviewer_set instance ids must be unique")
    base_prompt_ref = (data.get("prompt_components") or {}).get("shared_base_instructions")
    if base_prompt_ref and not (root / str(base_prompt_ref)).exists():
        errors.append(f"{path}: shared_base_instructions does not exist: {base_prompt_ref}")
    for idx, reviewer in enumerate(reviewers):
        if not isinstance(reviewer, dict):
            continue
        if reviewer.get("independent") is not True:
            errors.append(f"{path}: reviewer_set[{idx}].independent must be true")
        role_contract = str(reviewer.get("role_contract", ""))
        if role_contract and not role_contract.startswith(ROLE_CONTRACT_PREFIXES):
            errors.append(f"{path}: reviewer_set[{idx}].role_contract must resolve to reviewer_roles")
        if check_references and role_contract:
            role_path = root / role_contract
            if not role_path.exists():
                errors.append(f"{path}: reviewer role_contract does not exist: {role_contract}")
            else:
                role_data = parse_yaml(role_path) or {}
                if not isinstance(role_data, dict) or role_data.get("kind") != "reviewer_role":
                    errors.append(f"{path}: role_contract must point to a reviewer_role manifest")
                elif role_data.get("name") != reviewer.get("role_id"):
                    errors.append(f"{path}: role_id must match role_contract.name for {reviewer.get('instance_id')}")

    if profile == "homogeneous-dual":
        if primary_gate is not True or len(reviewers) != 2:
            errors.append(f"{path}: homogeneous-dual must be primary and use exactly two reviewers")
        for reviewer in reviewers:
            if isinstance(reviewer, dict) and reviewer.get("role_id") != "generalist":
                errors.append(f"{path}: homogeneous-dual reviewers must use generalist role")
        for key in ["same_prompt", "same_packet", "same_rubric", "same_output_schema"]:
            if prompt_policy.get(key) is not True:
                errors.append(f"{path}: homogeneous-dual prompt_policy.{key} must be true")
        for key in ["schema_hash", "rubric_hash", "role_contract_hash"]:
            values = {str(item.get(key)) for item in prompts if isinstance(item, dict)}
            if len(values) != 1:
                errors.append(f"{path}: homogeneous-dual rendered_prompts must share {key}")
        for key in ["shared_prompt_content_hash", "shared_packet_content_hash"]:
            values = [item.get(key) for item in prompts if isinstance(item, dict)]
            if any(not value for value in values):
                errors.append(f"{path}: homogeneous-dual rendered_prompts must declare {key}")
            elif len(set(str(value) for value in values)) != 1:
                errors.append(f"{path}: homogeneous-dual rendered_prompts must share {key}")
            elif data.get("artifact_scope", "run") == "run":
                for value in values:
                    digest = str(value).removeprefix("sha256:")
                    if not str(value).startswith("sha256:") or len(digest) != 64 or not all(c in "0123456789abcdef" for c in digest):
                        errors.append(f"{path}: run rendered_prompts.{key} must be a concrete sha256")
        packet_shared_values = {
            item.get("shared_packet_content_hash")
            for item in ((data.get("inputs") or {}).get("review_packets") or [])
            if isinstance(item, dict)
        }
        if any(not value for value in packet_shared_values):
            errors.append(f"{path}: homogeneous-dual review_packets must declare shared_packet_content_hash")
        elif len(set(str(value) for value in packet_shared_values)) != 1:
            errors.append(f"{path}: homogeneous-dual review_packets must share shared_packet_content_hash")
        elif data.get("artifact_scope", "run") == "run":
            for value in packet_shared_values:
                digest = str(value).removeprefix("sha256:")
                if not str(value).startswith("sha256:") or len(digest) != 64 or not all(c in "0123456789abcdef" for c in digest):
                    errors.append(f"{path}: run review_packets.shared_packet_content_hash must be a concrete sha256")
    elif profile == "homogeneous-plus-focused":
        if primary_gate is not True or not (3 <= len(reviewers) <= 8):
            errors.append(f"{path}: homogeneous-plus-focused must use three to eight reviewers")
        if "generalist-a" not in reviewer_ids or "generalist-b" not in reviewer_ids:
            errors.append(f"{path}: homogeneous-plus-focused requires generalist-a/generalist-b baseline")
        for key in [
            "baseline_same_prompt",
            "focused_reviewers_require_explicit_focus_zone",
            "focus_zones_may_overlap",
            "all_reviewers_must_report_p0_p1_outside_focus",
        ]:
            if prompt_policy.get(key) is not True:
                errors.append(f"{path}: homogeneous-plus-focused prompt_policy.{key} must be true")
        for reviewer in reviewers:
            if not isinstance(reviewer, dict):
                continue
            if reviewer.get("instance_id") not in {"generalist-a", "generalist-b"} and not reviewer.get("focus_zone"):
                errors.append(f"{path}: focused reviewer {reviewer.get('instance_id')} must have focus_zone")
    elif profile == "heterogeneous-variable":
        if primary_gate is not True or not (3 <= len(reviewers) <= 8):
            errors.append(f"{path}: heterogeneous-variable must use three to eight reviewers")
        for key in ["focus_prompts_required", "focus_zones_may_overlap", "all_reviewers_must_report_p0_p1_outside_focus"]:
            if prompt_policy.get(key) is not True:
                errors.append(f"{path}: heterogeneous-variable prompt_policy.{key} must be true")
        for reviewer in reviewers:
            if isinstance(reviewer, dict) and not reviewer.get("focus_zone"):
                errors.append(f"{path}: heterogeneous reviewer {reviewer.get('instance_id')} must have focus_zone")
    elif profile == "collision-control":
        if primary_gate is not False or len(reviewers) != 1:
            errors.append(f"{path}: collision-control must be non-primary and use exactly one reviewer")
        collision = data.get("collision_control")
        if not isinstance(collision, dict) or collision.get("trigger") != "rejected_blocker_finding_collision":
            errors.append(f"{path}: collision-control requires rejected-blocker collision context")
        else:
            for key in [
                "disputed_finding_id",
                "original_severity",
                "source_reviewer_report",
                "orchestrator_rejection_reason",
                "evidence_references_checked",
            ]:
                if not collision.get(key):
                    errors.append(f"{path}: collision-control missing {key}")
    if data.get("artifact_scope", "run") == "run":
        for prompt in prompts:
            if not isinstance(prompt, dict):
                continue
            for key in ["prompt_hash", "packet_hash", "schema_hash", "rubric_hash", "role_contract_hash"]:
                value = str(prompt.get(key, ""))
                digest = value.removeprefix("sha256:")
                if not value.startswith("sha256:") or len(digest) != 64 or not all(c in "0123456789abcdef" for c in digest):
                    errors.append(f"{path}: run rendered_prompts.{key} must be a concrete sha256")
        for packet in ((data.get("inputs") or {}).get("review_packets") or []):
            if not isinstance(packet, dict):
                continue
            value = str(packet.get("packet_hash", ""))
            digest = value.removeprefix("sha256:")
            if not value.startswith("sha256:") or len(digest) != 64 or not all(c in "0123456789abcdef" for c in digest):
                errors.append(f"{path}: run review_packets.packet_hash must be a concrete sha256")
    return errors


def validate_review_packet_artifact(root: Path, path: Path, check_references: bool) -> list[str]:
    errors: list[str] = []
    schema = parse_json(root / "schemas" / "review-packet.schema.json")
    data = parse_json(path)
    if not isinstance(data, dict):
        return [f"{path}: review packet must be a JSON object"]
    errors.extend(validate_against_schema(path, data, schema))
    context_policy = data.get("context_policy", {}) or {}
    allowed = set(context_policy.get("allowed_context_sources", []) or [])
    if allowed != {"review_packet", "referenced_artifacts"}:
        errors.append(f"{path}: allowed_context_sources must be exactly review_packet and referenced_artifacts")
    composition = str(data.get("composition") or "")
    reviewer_instance = str(data.get("reviewer_instance_id") or "")
    if composition == "heterogeneous" and not data.get("focus_zone"):
        errors.append(f"{path}: heterogeneous review packet must include focus_zone")
    if (
        composition == "homogeneous-plus-focused"
        and reviewer_instance not in {"generalist-a", "generalist-b"}
        and not data.get("focus_zone")
    ):
        errors.append(f"{path}: homogeneous-plus-focused focused reviewer packet must include focus_zone")
    if not check_references:
        return errors

    role_ref = data.get("role_contract")
    if role_ref:
        role_ref_text = str(role_ref)
        if Path(role_ref_text).is_absolute() or ".." in Path(role_ref_text).parts:
            errors.append(f"{path}: role_contract must be a relative non-escaping path")
        if not role_ref_text.startswith(ROLE_CONTRACT_PREFIXES):
            errors.append(f"{path}: role_contract must resolve to profiles/reviewer_roles")
        role_path = root / str(role_ref)
        if not role_path.exists():
            errors.append(f"{path}: role_contract does not exist: {role_ref}")
        else:
            role_data = parse_yaml(role_path) or {}
            if not isinstance(role_data, dict) or role_data.get("kind") != "reviewer_role":
                errors.append(f"{path}: role_contract must point to a reviewer_role manifest")
            elif role_data.get("name") != data.get("reviewer_role"):
                errors.append(f"{path}: reviewer_role must match role_contract.name")
    prompt_contract = data.get("review_prompt_contract", {}) or {}
    prompt_contract_ref = prompt_contract.get("path")
    if prompt_contract_ref and (Path(str(prompt_contract_ref)).is_absolute() or ".." in Path(str(prompt_contract_ref)).parts):
        errors.append(f"{path}: review_prompt_contract.path must be relative and non-escaping")
    prompt_contract_path = root / str(prompt_contract_ref) if prompt_contract_ref else None
    if prompt_contract_ref and not prompt_contract_path.exists():
        errors.append(f"{path}: review_prompt_contract.path does not exist: {prompt_contract_ref}")
    elif prompt_contract_ref and prompt_contract_path:
        contract_schema_ref = prompt_contract.get("schema")
        if contract_schema_ref and (
            Path(str(contract_schema_ref)).is_absolute() or ".." in Path(str(contract_schema_ref)).parts
        ):
            errors.append(f"{path}: review_prompt_contract.schema must be relative and non-escaping")
        contract_schema_path = root / str(contract_schema_ref)
        if not contract_schema_ref or not contract_schema_path.exists():
            errors.append(f"{path}: review_prompt_contract.schema does not exist: {contract_schema_ref}")
        else:
            contract = parse_yaml(prompt_contract_path) or {}
            if not isinstance(contract, dict):
                errors.append(f"{prompt_contract_path}: review prompt contract must be a mapping")
            else:
                contract_schema = parse_json(contract_schema_path)
                if isinstance(contract_schema, dict):
                    errors.extend(validate_against_schema(prompt_contract_path, contract, contract_schema))
                errors.extend(validate_review_prompt_contract_invariants(root, prompt_contract_path, contract, True))
                identity = contract.get("identity", {}) or {}
                for key in ["workflow", "run_id", "review_profile", "composition"]:
                    if str(identity.get(key)) != str(data.get(key)):
                        errors.append(f"{path}: {key} must match review_prompt_contract identity.{key}")
                reviewer_id = str(data.get("reviewer_instance_id") or data.get("reviewer_role") or "")
                reviewer_set = contract.get("reviewer_set", []) or []
                matches = [
                    reviewer
                    for reviewer in reviewer_set
                    if isinstance(reviewer, dict)
                    and (
                        reviewer.get("instance_id") == reviewer_id
                        or (
                            not data.get("reviewer_instance_id")
                            and reviewer.get("role_id") == data.get("reviewer_role")
                        )
                    )
                ]
                if not matches:
                    errors.append(f"{path}: reviewer must exist in review_prompt_contract reviewer_set")
                elif matches[0].get("role_contract") != role_ref:
                    errors.append(f"{path}: role_contract must match review_prompt_contract reviewer role_contract")
    output_schema = data.get("output_schema")
    if output_schema and not (root / str(output_schema)).exists():
        errors.append(f"{path}: output_schema does not exist: {output_schema}")
    return errors


def validate_review_prompt_contract_template(root: Path) -> list[str]:
    schema = parse_json(root / "schemas" / "review-prompt-contract.schema.json")
    path = root / "templates" / "review-prompt-contract.yaml"
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"{path}: review prompt contract template must be a mapping"]
    errors = validate_against_schema(path, data, schema)
    errors.extend(validate_review_prompt_contract_invariants(root, path, data, False))
    example = root / "examples" / "external-reviewers" / "claude-code" / "review-prompt-contract.architecture.yaml"
    if example.exists():
        example_data = parse_yaml(example) or {}
        if not isinstance(example_data, dict):
            errors.append(f"{example}: review prompt contract example must be a mapping")
        else:
            errors.extend(validate_against_schema(example, example_data, schema))
            errors.extend(validate_review_prompt_contract_invariants(root, example, example_data, True))
    return errors


def validate_reviewer_invocation_artifact(root: Path, path: Path) -> list[str]:
    schema = parse_json(root / "schemas" / "reviewer-invocation.schema.json")
    data = parse_json(path)
    if not isinstance(data, dict):
        return [f"{path}: reviewer invocation must be a JSON object"]
    return validate_against_schema(path, data, schema)


def validate_workflow_run_artifact(root: Path, path: Path) -> list[str]:
    schema = parse_json(root / "schemas" / "workflow-run.schema.json")
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"{path}: workflow run metadata must be a mapping"]
    return validate_against_schema(path, data, schema)


def validate_reviewer_report_artifact(root: Path, path: Path) -> list[str]:
    schema = parse_json(root / "schemas" / "reviewer-report.schema.json")
    data = parse_json(path)
    if not isinstance(data, dict):
        return [f"{path}: reviewer report must be a JSON object"]
    return validate_against_schema(path, data, schema)


def validate_project_gate_manifest(
    path: Path,
    project_root: Path,
    binding_extends: object,
    binding_runner: object,
) -> list[str]:
    errors: list[str] = []
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"{path}: project gate manifest must be a mapping"]
    for key in ["extends", "runner", "instruments", "outputs"]:
        if key not in data:
            errors.append(f"{path}: project gate manifest missing {key}")
    if data.get("runner") != binding_runner:
        errors.append(f"{path}: runner must match workflow binding runner")
    if data.get("extends") not in {binding_extends, f".agentsflow/upstream/{binding_extends}"}:
        errors.append(f"{path}: extends must match workflow binding gate extends")
    runner_path = safe_resolve(project_root, data.get("runner"), f"{path}: runner", errors)
    if runner_path and not runner_path.exists():
        errors.append(f"{path}: runner does not exist: {data.get('runner')}")
    instruments = data.get("instruments", []) or []
    if not isinstance(instruments, list) or not instruments:
        errors.append(f"{path}: project gate manifest instruments must be a non-empty list")
    else:
        for idx, instrument in enumerate(instruments):
            if not isinstance(instrument, dict):
                errors.append(f"{path}: instrument #{idx} must be a mapping")
                continue
            if not instrument.get("id") or not instrument.get("type"):
                errors.append(f"{path}: instrument #{idx} must include id and type")
            instrument_type = instrument.get("type")
            if instrument_type not in VALID_GATE_INSTRUMENT_TYPES:
                errors.append(f"{path}: instrument {instrument.get('id')} has unknown type {instrument_type}")
            if instrument_type in {"tests", "deterministic_script"} and not instrument.get("command"):
                errors.append(f"{path}: instrument {instrument.get('id')} must include command")
    return errors


def required_workflow_gates(workflow_path: Path) -> set[str]:
    if not workflow_path.exists():
        return set()
    data = parse_yaml(workflow_path) or {}
    if not isinstance(data, dict):
        return set()
    gates: set[str] = set()
    for phase in data.get("phases", []) or []:
        if isinstance(phase, dict) and phase.get("gate"):
            gates.add(str(phase["gate"]))
    return gates


def validate_test_framed_implementation(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    phases = data.get("phases", []) or []
    if not isinstance(phases, list):
        return errors
    for idx, phase in enumerate(phases):
        if not isinstance(phase, dict) or phase.get("kind") != "implementation":
            continue
        phase_id = phase.get("id", phase.get("name", f"#{idx}"))
        previous = phases[idx - 1] if idx > 0 and isinstance(phases[idx - 1], dict) else {}
        following = phases[idx + 1] if idx + 1 < len(phases) and isinstance(phases[idx + 1], dict) else {}
        valid_previous = previous.get("test_framing") == "red_capture" or (
            previous.get("test_framing") == "baseline_capture"
            and phase.get("change_type") == "refactor"
        )
        if not valid_previous:
            errors.append(
                f"{path}: implementation phase {phase_id} must be immediately preceded by a red-capture phase "
                "with test_framing: red_capture, or by baseline_capture for change_type: refactor"
            )
        elif previous.get("kind") not in {"verification", "gate"} or not previous.get("gate"):
            errors.append(
                f"{path}: implementation phase {phase_id} framing phase must be verification/gate with gate"
            )
        if following.get("test_framing") != "green_verify":
            errors.append(
                f"{path}: implementation phase {phase_id} must be immediately followed by a green-verify phase "
                "with test_framing: green_verify"
            )
        elif following.get("kind") not in {"verification", "gate"} or not following.get("gate"):
            errors.append(
                f"{path}: implementation phase {phase_id} green phase must be verification/gate with gate"
            )
        elif previous.get("gate") and following.get("gate") and previous.get("gate") != following.get("gate"):
            errors.append(
                f"{path}: implementation phase {phase_id} framing phases should use the same gate"
            )
    return errors


def validate_project_initialization_operating_decisions(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("name") != "project-initialization":
        return errors
    outputs = set(data.get("outputs", []) or [])
    uses = data.get("uses", {}) or {}
    skills = set(uses.get("skills", []) or [])
    templates = set(uses.get("templates", []) or [])
    phases = data.get("phases", []) or []
    phase_by_id = {
        phase.get("id"): phase
        for phase in phases
        if isinstance(phase, dict) and phase.get("id")
    }
    if "project-operating-decisions.yaml" not in outputs:
        errors.append(f"{path}: project-initialization must output project-operating-decisions.yaml")
    if "project-operating-decisions-interview" not in skills:
        errors.append(f"{path}: project-initialization must use project-operating-decisions-interview skill")
    if "project-operating-decisions.yaml" not in templates:
        errors.append(f"{path}: project-initialization must use project-operating-decisions.yaml template")
    interview = phase_by_id.get("operating_decisions_interview")
    if not interview:
        errors.append(f"{path}: project-initialization must include operating_decisions_interview phase")
    elif "project-operating-decisions.yaml" not in set(interview.get("outputs", []) or []):
        errors.append(f"{path}: operating_decisions_interview must output project-operating-decisions.yaml")
    overlay = phase_by_id.get("overlay_draft")
    if overlay and "project-operating-decisions.yaml" not in set(overlay.get("inputs", []) or []):
        errors.append(f"{path}: overlay_draft must consume project-operating-decisions.yaml")
    return errors


def validate_project_initialization_human_interaction(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("name") != "project-initialization":
        return errors

    human = data.get("human_interaction", {}) or {}
    if human.get("mode") != "main-agent-mediated":
        errors.append(f"{path}: project-initialization human_interaction.mode must be main-agent-mediated")
    if human.get("reviewers_may_ask_human") is not False:
        errors.append(f"{path}: project-initialization must set reviewers_may_ask_human: false")
    if human.get("pause_state") != "paused_waiting_for_human":
        errors.append(f"{path}: project-initialization pause_state must be paused_waiting_for_human")
    if human.get("question_artifact") != "human-questions.yaml":
        errors.append(f"{path}: project-initialization question_artifact must be human-questions.yaml")
    if human.get("decision_artifact") != "human-decisions.yaml":
        errors.append(f"{path}: project-initialization decision_artifact must be human-decisions.yaml")

    required_pause_phases = {
        "read_project_intake",
        "legacy_adoption_mode_decision",
        "operating_decisions_interview",
        "human_approval",
    }
    declared = set(human.get("allowed_pause_phases", []) or [])
    missing_declared = sorted(required_pause_phases - declared)
    if missing_declared:
        errors.append(f"{path}: human_interaction.allowed_pause_phases missing: {', '.join(missing_declared)}")

    phase_by_id = {
        phase.get("id"): phase
        for phase in data.get("phases", []) or []
        if isinstance(phase, dict) and phase.get("id")
    }
    for phase_id in sorted(required_pause_phases):
        phase = phase_by_id.get(phase_id)
        if not phase:
            errors.append(f"{path}: missing human-interaction phase: {phase_id}")
            continue
        phase_human = phase.get("human_interaction", {}) or {}
        if phase_human.get("can_pause") is not True:
            errors.append(f"{path}: phase {phase_id} must set human_interaction.can_pause: true")
        if phase_human.get("question_artifact") != "human-questions.yaml":
            errors.append(f"{path}: phase {phase_id} must use human-questions.yaml")
        if phase_human.get("decision_artifact") != "human-decisions.yaml":
            errors.append(f"{path}: phase {phase_id} must use human-decisions.yaml")
    return errors


def validate_enabled_review_minimum(
    path: Path,
    review: object,
    context: str,
    reviewer_role_names: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(review, dict) or not review:
        return errors
    topology = review.get("topology")
    if not topology or topology == "none":
        return errors
    topology_rules = {
        "homogeneous-dual": ("homogeneous", 2, 2),
        "homogeneous-plus-focused": ("homogeneous-plus-focused", 3, 8),
        "heterogeneous-variable": ("heterogeneous", 3, 8),
    }
    expected_rule = topology_rules.get(str(topology))
    if topology == "single-reviewer":
        errors.append(
            f"{path}: {context}.topology single-reviewer is not valid for primary review gates; "
            "enabled review gates require at least two reviewers"
        )
    reviewers = review.get("reviewers")
    if not isinstance(reviewers, list):
        errors.append(f"{path}: {context}.reviewers must list at least two reviewers when review is enabled")
    elif len(reviewers) < 2:
        errors.append(f"{path}: {context}.reviewers must include at least two reviewers when review is enabled")
    elif len(reviewers) > 8:
        errors.append(f"{path}: {context}.reviewers must not include more than eight reviewers")
    context_policy = review.get("context_policy")
    if not isinstance(context_policy, dict):
        errors.append(f"{path}: {context}.context_policy is required when review is enabled")
    else:
        if context_policy.get("start_mode") != "fresh_context":
            errors.append(f"{path}: {context}.context_policy.start_mode must be fresh_context")
        if context_policy.get("fork_conversation_context") is not False:
            errors.append(f"{path}: {context}.context_policy.fork_conversation_context must be false")

    composition = review.get("composition")
    if composition not in {"homogeneous", "homogeneous-plus-focused", "heterogeneous"}:
        errors.append(f"{path}: {context}.composition must be homogeneous, homogeneous-plus-focused or heterogeneous")
    if expected_rule:
        expected_composition, min_count, max_count = expected_rule
        if composition != expected_composition:
            errors.append(
                f"{path}: {context}.composition must be {expected_composition} for topology {topology}"
            )
        if isinstance(reviewers, list) and not (min_count <= len(reviewers) <= max_count):
            errors.append(
                f"{path}: topology {topology} requires {min_count}-{max_count} reviewers"
            )
    prompt_policy = review.get("prompt_policy")
    if not isinstance(prompt_policy, dict):
        errors.append(f"{path}: {context}.prompt_policy is required when review is enabled")
    elif composition == "homogeneous":
        for key in ["same_prompt", "same_packet", "same_rubric", "same_output_schema"]:
            if prompt_policy.get(key) is not True:
                errors.append(f"{path}: {context}.prompt_policy.{key} must be true for homogeneous review")
        if isinstance(reviewers, list) and len(reviewers) != 2:
            errors.append(f"{path}: homogeneous review must use exactly two reviewers")
    elif composition == "homogeneous-plus-focused":
        if isinstance(reviewers, list) and len(reviewers) < 3:
            errors.append(f"{path}: homogeneous-plus-focused review must use at least three reviewers")
        if isinstance(reviewers, list):
            baseline_missing = sorted({"generalist-a", "generalist-b"} - set(str(item) for item in reviewers))
            if baseline_missing:
                errors.append(f"{path}: homogeneous-plus-focused missing baseline reviewers: {', '.join(baseline_missing)}")
        if prompt_policy.get("baseline_same_prompt") is not True:
            errors.append(f"{path}: {context}.prompt_policy.baseline_same_prompt must be true")
        if prompt_policy.get("focused_reviewers_require_explicit_focus_zone") is not True:
            errors.append(
                f"{path}: {context}.prompt_policy.focused_reviewers_require_explicit_focus_zone must be true"
            )
        if prompt_policy.get("focus_zones_may_overlap") is not True:
            errors.append(f"{path}: {context}.prompt_policy.focus_zones_may_overlap must be true")
        if prompt_policy.get("all_reviewers_must_report_p0_p1_outside_focus") is not True:
            errors.append(
                f"{path}: {context}.prompt_policy.all_reviewers_must_report_p0_p1_outside_focus must be true"
            )
    elif composition == "heterogeneous":
        if isinstance(reviewers, list) and len(reviewers) < 3:
            errors.append(f"{path}: heterogeneous review must use at least three reviewers")
        if isinstance(reviewers, list) and len(reviewers) > 8:
            errors.append(f"{path}: heterogeneous review must use no more than eight reviewers")
        if prompt_policy.get("focus_prompts_required") is not True:
            errors.append(f"{path}: {context}.prompt_policy.focus_prompts_required must be true")
        if prompt_policy.get("focus_zones_may_overlap") is not True:
            errors.append(f"{path}: {context}.prompt_policy.focus_zones_may_overlap must be true")
        if prompt_policy.get("all_reviewers_must_report_p0_p1_outside_focus") is not True:
            errors.append(
                f"{path}: {context}.prompt_policy.all_reviewers_must_report_p0_p1_outside_focus must be true"
            )

    focus_zones = review.get("focus_zones", []) or []
    if composition in {"homogeneous-plus-focused", "heterogeneous"}:
        if not isinstance(focus_zones, list) or not focus_zones:
            errors.append(f"{path}: {context}.focus_zones must list explicit focused reviewer roles")
        elif reviewer_role_names is not None:
            reviewer_names = set(str(item) for item in reviewers) if isinstance(reviewers, list) else set()
            seen_focus_reviewers: set[str] = set()
            for idx, zone in enumerate(focus_zones):
                if not isinstance(zone, dict):
                    errors.append(f"{path}: {context}.focus_zones[{idx}] must be a mapping")
                    continue
                reviewer = str(zone.get("reviewer", ""))
                if reviewer in seen_focus_reviewers:
                    errors.append(f"{path}: {context}.focus_zones[{idx}] duplicates reviewer: {reviewer}")
                seen_focus_reviewers.add(reviewer)
                if reviewer and reviewer not in reviewer_names:
                    errors.append(f"{path}: {context}.focus_zones[{idx}] references non-reviewer: {reviewer}")
                role = zone.get("role")
                if role not in reviewer_role_names:
                    errors.append(f"{path}: {context}.focus_zones[{idx}] references unknown reviewer role: {role}")
                if not zone.get("primary_focus"):
                    errors.append(f"{path}: {context}.focus_zones[{idx}] must include primary_focus")
            if composition == "heterogeneous" and reviewer_names != seen_focus_reviewers:
                missing = sorted(reviewer_names - seen_focus_reviewers)
                extra = sorted(seen_focus_reviewers - reviewer_names)
                if missing:
                    errors.append(f"{path}: heterogeneous focus_zones missing reviewers: {', '.join(missing)}")
                if extra:
                    errors.append(f"{path}: heterogeneous focus_zones include non-reviewers: {', '.join(extra)}")
            if composition == "homogeneous-plus-focused":
                baseline = {"generalist-a", "generalist-b"}
                focused_reviewers = reviewer_names - baseline
                missing = sorted(focused_reviewers - seen_focus_reviewers)
                if missing:
                    errors.append(
                        f"{path}: homogeneous-plus-focused focus_zones missing focused reviewers: {', '.join(missing)}"
                    )
    return errors


def validate_supported_review_topologies(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    supported = ((data.get("supported_profiles") or {}).get("review_topologies") or [])
    if not isinstance(supported, list):
        return errors
    if "single-reviewer" in supported:
        errors.append(
            f"{path}: supported_profiles.review_topologies must not include single-reviewer; "
            "primary review gates require two or more reviewers"
        )
    return errors


def validate_mvp_review_phase_policy(path: Path, data: dict) -> list[str]:
    if data.get("name") not in MVP_WORKFLOWS:
        return []
    has_review_phase = any(
        isinstance(phase, dict) and phase.get("kind") == "review"
        for phase in data.get("phases", []) or []
    )
    if has_review_phase and not isinstance(data.get("review"), dict):
        return [f"{path}: MVP workflow with review phase must declare top-level review policy"]
    return []


def validate_project_overlay_example(
    root: Path,
    project_rel: str,
    project_schema: dict,
    workflow_binding_schema: dict,
    reviewer_role_names: set[str],
) -> list[str]:
    errors: list[str] = []
    project = root / project_rel
    overlay = project / ".agentsflow"
    if not overlay.exists():
        return [f"{project_rel}: missing .agentsflow overlay"]
    lock_file = overlay / "agentsflow.lock.yaml"
    if not lock_file.exists():
        errors.append(f"{project_rel}: missing .agentsflow/agentsflow.lock.yaml")
    project_yaml = overlay / "project.yaml"
    if not project_yaml.exists():
        errors.append(f"{project_rel}: missing .agentsflow/project.yaml")
    else:
        data = parse_yaml(project_yaml) or {}
        if not isinstance(data, dict):
            errors.append(f"{project_yaml}: project manifest must be a mapping")
        else:
            errors.extend(validate_against_schema(project_yaml, data, project_schema))
    workflow_dir = overlay / "workflows"
    if not workflow_dir.exists():
        errors.append(f"{project_rel}: missing .agentsflow/workflows")
    else:
        binding_files = sorted(workflow_dir.glob("*.binding.yaml"))
        if not binding_files:
            errors.append(f"{project_rel}: no workflow binding files found")
        for binding_file in binding_files:
            binding = parse_yaml(binding_file) or {}
            if not isinstance(binding, dict):
                errors.append(f"{binding_file}: workflow binding must be a mapping")
                continue
            errors.extend(validate_against_schema(binding_file, binding, workflow_binding_schema))
            errors.extend(
                validate_enabled_review_minimum(
                    binding_file,
                    binding.get("review"),
                    "review",
                    reviewer_role_names,
                )
            )
            extends = binding.get("extends")
            extends_path = safe_resolve(root, extends, f"{binding_file}: extends", errors)
            if extends_path and not extends_path.exists():
                errors.append(f"{binding_file}: upstream workflow does not exist: {extends}")
            gates = binding.get("gates", {}) or {}
            if extends_path and extends_path.exists() and isinstance(gates, dict):
                missing_gates = sorted(required_workflow_gates(extends_path) - set(str(key) for key in gates))
                if missing_gates:
                    errors.append(f"{binding_file}: missing project gate binding(s): {', '.join(missing_gates)}")
            for gate_id, cfg in (binding.get("gates", {}) or {}).items():
                if not isinstance(cfg, dict):
                    continue
                upstream = cfg.get("extends")
                upstream_path = safe_resolve(root, upstream, f"{binding_file}: gate {gate_id} extends", errors)
                if upstream_path and not upstream_path.exists():
                    errors.append(f"{binding_file}: gate {gate_id} upstream contract missing: {upstream}")
                elif upstream_path:
                    upstream_data = parse_yaml(upstream_path) or {}
                    if isinstance(upstream_data, dict):
                        upstream_id = str(upstream_data.get("id", upstream_path.stem))
                        if upstream_id != str(gate_id):
                            errors.append(
                                f"{binding_file}: gate {gate_id} extends upstream gate id {upstream_id}"
                            )
                manifest = cfg.get("manifest")
                manifest_path = safe_resolve(project, manifest, f"{binding_file}: gate {gate_id} manifest", errors)
                if manifest_path and not manifest_path.exists():
                    errors.append(f"{binding_file}: gate {gate_id} project manifest missing: {manifest}")
                elif manifest_path:
                    errors.extend(validate_project_gate_manifest(manifest_path, project, upstream, cfg.get("runner")))
                runner = cfg.get("runner")
                runner_path = safe_resolve(project, runner, f"{binding_file}: gate {gate_id} runner", errors)
                if runner_path and not runner_path.exists():
                    errors.append(f"{binding_file}: gate {gate_id} runner missing: {runner}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="repository root")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    errors: list[str] = []

    for p in root.rglob("*.yaml"):
        try:
            parse_yaml(p)
        except ValueError as exc:
            errors.append(str(exc))
    for p in root.rglob("*.yml"):
        try:
            parse_yaml(p)
        except ValueError as exc:
            errors.append(str(exc))
    for p in root.rglob("*.json"):
        try:
            parse_json(p)
        except ValueError as exc:
            errors.append(str(exc))

    skills = collect_names(root, "skills", "skill.yaml")
    packs = collect_names(root, "packs", "pack.yaml")
    scripts = collect_script_names(root)
    templates = {p.name for p in (root / "templates").glob("*") if p.is_file()}
    topologies = collect_active_review_topologies(root)
    reviewer_role_names = collect_yaml_manifest_names(root, "profiles/reviewer_roles")
    gates = collect_gate_manifests(root)
    wf_schema = workflow_schema(root)
    project_schema = parse_json(root / "schemas" / "project-binding.schema.json")
    workflow_binding_schema = parse_json(root / "schemas" / "workflow-binding.schema.json")

    for gate_path in gates.values():
        errors.extend(validate_gate_manifest(root, gate_path))

    for binding in root.rglob("*.bindings.yaml"):
        errors.extend(validate_behavior_binding(binding))
        errors.extend(validate_behavior_binding_gate_refs(binding, set(gates.keys())))

    errors.extend(validate_review_manifest_collection(root))
    errors.extend(validate_review_prompt_contract_template(root))
    errors.extend(validate_review_packet_artifact(root, root / "templates" / "review-packet.json", False))
    errors.extend(
        validate_review_packet_artifact(
            root,
            root / "examples" / "external-reviewers" / "claude-code" / "review-packet.architecture.json",
            True,
        )
    )
    errors.extend(validate_reviewer_invocation_artifact(root, root / "templates" / "reviewer-invocation.json"))
    errors.extend(
        validate_reviewer_invocation_artifact(
            root,
            root / "examples" / "external-reviewers" / "claude-code" / "reviewer-invocation.claude-architecture.json",
        )
    )
    errors.extend(validate_workflow_run_artifact(root, root / "templates" / "workflow-run.yaml"))
    for run_artifact in root.glob("examples/**/Docs/agentsflow/runs/*/run.yaml"):
        errors.extend(validate_workflow_run_artifact(root, run_artifact))
    for reviewer_report in root.glob("examples/**/Docs/agentsflow/runs/*/reviewer-report*.json"):
        errors.extend(validate_reviewer_report_artifact(root, reviewer_report))

    for provider_config in list(root.rglob("external-review-provider.yaml")) + list(root.rglob("claude-code.yaml")):
        errors.extend(validate_external_review_provider(provider_config))

    required_files = [
        "schemas/behavior-binding.schema.json",
        "schemas/project-binding.schema.json",
        "schemas/workflow-binding.schema.json",
        "schemas/review-profile.schema.json",
        "schemas/reviewer-role.schema.json",
        "schemas/review-prompt-contract.schema.json",
        "templates/behavior-bindings.yaml",
        "templates/project.yaml",
        "templates/workflow.binding.yaml",
        "templates/agentsflow.lock.yaml",
        "templates/review-prompt-contract.yaml",
        "templates/project-intake.yaml",
        "templates/research-assignment.unknown-project.md",
        "templates/project-raw-scan.json",
        "templates/project-inventory.json",
        "templates/project-assessment.json",
        "templates/project-operating-decisions.yaml",
        "templates/human-questions.yaml",
        "templates/human-decisions.yaml",
        "templates/initialization-report.md",
        "templates/workflow-run.yaml",
        "schemas/project-intake.schema.json",
        "schemas/project-raw-scan.schema.json",
        "schemas/project-inventory.schema.json",
        "schemas/project-assessment.schema.json",
        "schemas/project-operating-decisions.schema.json",
        "schemas/human-questions.schema.json",
        "schemas/human-decisions.schema.json",
        "schemas/workflow-run.schema.json",
        "docs/project-application-model.md",
        "docs/project-initialization-model.md",
        "docs/review-profile-model.md",
        "docs/review-prompt-contract.md",
        "docs/human-interaction-protocol.md",
        "docs/legacy-agent-system-adoption-model.md",
        "docs/adr/ADR-0015-legacy-adoption-modes.md",
        "templates/legacy-adoption-decision.yaml",
        "templates/legacy-agent-system-inventory.json",
        "templates/agent-instruction-conflicts.md",
        "templates/agent-instruction-migration-plan.md",
        "templates/legacy-backup-manifest.yaml",
        "templates/active-instruction-map.yaml",
        "schemas/legacy-adoption-decision.schema.json",
        "schemas/legacy-agent-system-inventory.schema.json",
        "schemas/active-instruction-map.schema.json",

        "docs/external-reviewer-provider-model.md",
        "docs/adr/ADR-0016-external-reviewer-provider-interface.md",
        "templates/external-review-provider.yaml",
        "templates/review-packet.json",
        "templates/reviewer-invocation.json",
        "schemas/external-review-provider.schema.json",
        "schemas/review-packet.schema.json",
        "schemas/reviewer-invocation.schema.json",
        "schemas/reviewer-report.schema.json",
        "scripts/reviewers/run_external_reviewer.py",
        "scripts/reviewers/providers/claude_code.py",
        "scripts/contracts/run_external_reviewer.yaml",
        "examples/external-reviewers/claude-code/mock-raw-output.json",
        "docs/cmake-fetchcontent-application-pattern.md",
    ]
    for rel in required_files:
        if not (root / rel).exists():
            errors.append(f"missing required file: {rel}")
    if not (root / "docs" / "enforcement-boundary.md").exists():
        errors.append("missing required file: docs/enforcement-boundary.md")

    for project_rel in [
        "examples/project-overlay",
        "examples/e2e/minimal-python-project",
    ]:
        errors.extend(
            validate_project_overlay_example(
                root,
                project_rel,
                project_schema,
                workflow_binding_schema,
                reviewer_role_names,
            )
        )

    for wf in (root / "workflows").glob("*/workflow.yaml"):
        data = parse_yaml(wf) or {}
        if not isinstance(data, dict):
            errors.append(f"Workflow {wf} is not a mapping")
            continue
        errors.extend(validate_against_schema(wf, data, wf_schema))
        errors.extend(validate_test_framed_implementation(wf, data))
        errors.extend(validate_project_initialization_operating_decisions(wf, data))
        errors.extend(validate_project_initialization_human_interaction(wf, data))
        errors.extend(validate_supported_review_topologies(wf, data))
        errors.extend(validate_mvp_review_phase_policy(wf, data))
        uses = data.get("uses", {}) or {}
        for s in uses.get("skills", []) or []:
            if s not in skills:
                errors.append(f"{wf}: missing skill reference: {s}")
        for s in uses.get("scripts", []) or []:
            if s not in scripts:
                errors.append(f"{wf}: missing script reference: {s}")
        for t in uses.get("templates", []) or []:
            if t not in templates:
                errors.append(f"{wf}: missing template reference: {t}")
        for pack in uses.get("packs", []) or []:
            if pack not in packs:
                errors.append(f"{wf}: missing pack reference: {pack}")
        review = data.get("review", {}) or {}
        topology = review.get("topology")
        if topology and topology not in topologies:
            errors.append(f"{wf}: unknown review topology: {topology}")
        errors.extend(validate_enabled_review_minimum(wf, review, "review", reviewer_role_names))
        for gid in review.get("gates", []) or []:
            if gid not in gates:
                errors.append(f"{wf}: missing gate manifest referenced by review.gates: {gid}")
        for phase in data.get("phases", []) or []:
            if not isinstance(phase, dict):
                continue
            gid = phase.get("gate")
            if gid and gid not in gates:
                errors.append(f"{wf}: phase {phase.get('id', phase.get('name'))} references missing gate: {gid}")
            if (phase.get("kind") in {"gate", "verification"} or str(phase.get("id", "")).endswith("_gate")) and not gid:
                errors.append(f"{wf}: gate/verification phase {phase.get('id', phase.get('name'))} must declare a gate manifest via 'gate:'")
            if phase.get("kind") == "review" and phase.get("scripts"):
                errors.append(f"{wf}: review phase {phase.get('id', phase.get('name'))} must not list scripts; use tool exceptions only if explicitly declared")

    if errors:
        print("Repository validation failed:")
        for err in errors:
            print(f"- {err}")
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
