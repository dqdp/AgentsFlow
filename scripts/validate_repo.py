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
import hashlib
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
    if data.get("id") in {"project_initialization_gate", "target_workflow_readiness_gate"}:
        gate_id = str(data.get("id"))
        inputs = set(str(item) for item in data.get("inputs", []) or [])
        if "project-documentation-disposition.yaml" not in inputs:
            errors.append(
                f"{path}: {gate_id} inputs must include project-documentation-disposition.yaml"
            )
        required_evidence = set(str(item) for item in data.get("required_evidence", []) or [])
        if not any("project-documentation-disposition.yaml" in item for item in required_evidence):
            errors.append(
                f"{path}: {gate_id} required_evidence must include project-documentation-disposition.yaml"
            )
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
        if data.get("name") == "collision-control":
            if data.get("primary_gate") is not False:
                errors.append(f"{profile_path}: collision-control must not be a primary gate")
            if data.get("min_reviewers") != 2 or data.get("max_reviewers") != 2:
                errors.append(f"{profile_path}: collision-control must require exactly two reviewers")
            if data.get("trigger") != "rejected_or_downgraded_blocker_collision":
                errors.append(f"{profile_path}: collision-control trigger must be rejected_or_downgraded_blocker_collision")
    return errors


def validate_upstream_review_cycle_policy(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    review_cycle = data.get("review_cycle")
    if not isinstance(review_cycle, dict):
        return errors
    if "max_review_cycles" in review_cycle:
        errors.append(f"{path}: upstream workflow review_cycle must not hardcode max_review_cycles")
    if review_cycle.get("max_review_cycles_required") is True:
        errors.append(f"{path}: upstream workflow review_cycle must not require max_review_cycles")
    if review_cycle.get("max_review_cycles_source") != "project_policy_or_workflow_binding":
        errors.append(
            f"{path}: review_cycle.max_review_cycles_source must be project_policy_or_workflow_binding"
        )
    if review_cycle.get("max_review_cycles_absent_means") != "unlimited":
        errors.append(f"{path}: review_cycle.max_review_cycles_absent_means must be unlimited")
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
        if primary_gate is not False or len(reviewers) != 2:
            errors.append(f"{path}: collision-control must be non-primary and use exactly two reviewers")
        collision = data.get("collision_control")
        if not isinstance(collision, dict) or collision.get("trigger") != "rejected_or_downgraded_blocker_collision":
            errors.append(f"{path}: collision-control requires rejected/downgraded blocker collision context")
        else:
            for key in [
                "collision_batch_id",
                "control_reviewer_count",
                "disputed_findings",
                "orchestrator_collision_reason",
                "evidence_references_checked",
            ]:
                if not collision.get(key):
                    errors.append(f"{path}: collision-control missing {key}")
            if collision.get("control_reviewer_count") != 2:
                errors.append(f"{path}: collision-control control_reviewer_count must be 2")
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


def validate_review_prompt_contract_run_references(root: Path, path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("artifact_scope", "run") != "run":
        return errors

    def resolve_existing(ref: object, label: str, *, required: bool = True) -> Path | None:
        if not ref:
            if required:
                errors.append(f"{path}: {label} is required")
            return None
        ref_path = Path(str(ref))
        if ref_path.is_absolute() or ".." in ref_path.parts:
            errors.append(f"{path}: {label} must be relative and non-escaping: {ref}")
            return None
        resolved = root / ref_path
        if not resolved.exists():
            errors.append(f"{path}: {label} does not exist: {ref}")
            return None
        return resolved

    inputs = data.get("inputs", {}) or {}
    packet_schema_path = resolve_existing(inputs.get("review_packet_schema"), "inputs.review_packet_schema")
    output_schema_path = resolve_existing(inputs.get("output_schema"), "inputs.output_schema")
    review_subjects: list[tuple[str, object]] = []
    if inputs.get("task_contract"):
        review_subjects.append(("inputs.task_contract", inputs.get("task_contract")))
    if inputs.get("reviewed_artifact"):
        review_subjects.append(("inputs.reviewed_artifact", inputs.get("reviewed_artifact")))
    reviewed_artifacts = inputs.get("reviewed_artifacts")
    if reviewed_artifacts:
        if isinstance(reviewed_artifacts, list):
            for idx, artifact in enumerate(reviewed_artifacts):
                if isinstance(artifact, dict):
                    review_subjects.append((f"inputs.reviewed_artifacts[{idx}].path", artifact.get("path")))
                else:
                    review_subjects.append((f"inputs.reviewed_artifacts[{idx}]", artifact))
        else:
            errors.append(f"{path}: inputs.reviewed_artifacts must be a list")
    if not review_subjects:
        errors.append(
            f"{path}: one of inputs.task_contract, inputs.reviewed_artifact or inputs.reviewed_artifacts is required"
        )
    for label, ref in review_subjects:
        resolve_existing(ref, label)
    if inputs.get("verification_gate_report"):
        resolve_existing(inputs.get("verification_gate_report"), "inputs.verification_gate_report")
    if inputs.get("evidence_report"):
        resolve_existing(inputs.get("evidence_report"), "inputs.evidence_report")

    reviewers = {
        str(item.get("instance_id")): item
        for item in data.get("reviewer_set", []) or []
        if isinstance(item, dict) and item.get("instance_id")
    }
    rendered_by_reviewer = {
        str(item.get("reviewer")): item
        for item in data.get("rendered_prompts", []) or []
        if isinstance(item, dict) and item.get("reviewer")
    }
    packet_reviewers: set[str] = set()
    packet_hash_by_reviewer: dict[str, str] = {}
    seen_packet_paths: dict[Path, str] = {}
    for idx, packet in enumerate(inputs.get("review_packets", []) or []):
        if not isinstance(packet, dict):
            continue
        reviewer = str(packet.get("reviewer", ""))
        if reviewer in packet_reviewers:
            errors.append(f"{path}: inputs.review_packets duplicate reviewer: {reviewer}")
        packet_reviewers.add(reviewer)
        if reviewer not in reviewers:
            errors.append(f"{path}: inputs.review_packets[{idx}] reviewer not in reviewer_set: {reviewer}")
        if reviewer not in rendered_by_reviewer:
            errors.append(f"{path}: inputs.review_packets[{idx}] reviewer missing rendered prompt: {reviewer}")
        packet_path = resolve_existing(packet.get("path"), f"inputs.review_packets[{idx}].path")
        packet_schema_ref = packet.get("schema")
        packet_schema_ref_path = resolve_existing(packet_schema_ref, f"inputs.review_packets[{idx}].schema")
        if packet_schema_path and packet_schema_ref_path and packet_schema_ref_path.resolve() != packet_schema_path.resolve():
            errors.append(f"{path}: inputs.review_packets[{idx}].schema must match inputs.review_packet_schema")
        if packet_path:
            resolved_packet_path = packet_path.resolve()
            if resolved_packet_path in seen_packet_paths:
                errors.append(
                    f"{path}: inputs.review_packets duplicate path for reviewers {seen_packet_paths[resolved_packet_path]} and {reviewer}"
                )
            seen_packet_paths[resolved_packet_path] = reviewer
            packet_hash = sha256_file(packet_path)
            packet_hash_by_reviewer[reviewer] = packet_hash
            compare_hash(path, f"inputs.review_packets[{idx}].packet_hash", packet.get("packet_hash"), packet_hash, errors)
            packet_data = parse_json(packet_path)
            if isinstance(packet_data, dict):
                if str(packet_data.get("reviewer_instance_id")) != reviewer:
                    errors.append(f"{path}: packet {packet.get('path')} reviewer_instance_id must be {reviewer}")
            else:
                errors.append(f"{path}: packet {packet.get('path')} must be a JSON object")
    if set(reviewers) != packet_reviewers:
        missing = sorted(set(reviewers) - packet_reviewers)
        extra = sorted(packet_reviewers - set(reviewers))
        if missing:
            errors.append(f"{path}: inputs.review_packets missing reviewers: {', '.join(missing)}")
        if extra:
            errors.append(f"{path}: inputs.review_packets contains unknown reviewers: {', '.join(extra)}")

    output_schema_hash = sha256_file(output_schema_path) if output_schema_path else ""
    rubric_hash = sha256_text(json.dumps(data.get("prompt_policy", {}) or {}, sort_keys=True))
    for idx, prompt in enumerate(data.get("rendered_prompts", []) or []):
        if not isinstance(prompt, dict):
            continue
        reviewer = str(prompt.get("reviewer", ""))
        reviewer_def = reviewers.get(reviewer)
        if not reviewer_def:
            errors.append(f"{path}: rendered_prompts[{idx}] reviewer not in reviewer_set: {reviewer}")
            continue
        prompt_path = resolve_existing(prompt.get("prompt_path"), f"rendered_prompts[{idx}].prompt_path")
        if prompt_path:
            compare_hash(path, f"rendered_prompts[{idx}].prompt_hash", prompt.get("prompt_hash"), sha256_file(prompt_path), errors)
        packet_hash = packet_hash_by_reviewer.get(reviewer)
        if packet_hash:
            compare_hash(path, f"rendered_prompts[{idx}].packet_hash", prompt.get("packet_hash"), packet_hash, errors)
        if output_schema_hash:
            compare_hash(path, f"rendered_prompts[{idx}].schema_hash", prompt.get("schema_hash"), output_schema_hash, errors)
        compare_hash(path, f"rendered_prompts[{idx}].rubric_hash", prompt.get("rubric_hash"), rubric_hash, errors)
        role_path = resolve_existing(reviewer_def.get("role_contract"), f"reviewer_set.{reviewer}.role_contract")
        if role_path:
            compare_hash(path, f"rendered_prompts[{idx}].role_contract_hash", prompt.get("role_contract_hash"), sha256_file(role_path), errors)
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
                contract_packets = ((contract.get("inputs") or {}).get("review_packets") or [])
                packet_matches = [
                    packet
                    for packet in contract_packets
                    if isinstance(packet, dict)
                    and packet.get("reviewer") == reviewer_id
                    and (root / str(packet.get("path", ""))).resolve() == path.resolve()
                ]
                if not packet_matches:
                    errors.append(
                        f"{path}: review packet must be listed in review_prompt_contract inputs.review_packets with matching reviewer and path"
                    )
                elif len(packet_matches) > 1:
                    errors.append(f"{path}: review packet has duplicate entries in review_prompt_contract inputs.review_packets")
                elif contract.get("artifact_scope") == "run":
                    compare_hash(
                        path,
                        "review_prompt_contract packet_hash",
                        packet_matches[0].get("packet_hash"),
                        sha256_file(path),
                        errors,
                    )
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


def validate_evidence_probe_report_artifact(root: Path, path: Path) -> list[str]:
    errors: list[str] = []
    schema = parse_json(root / "schemas" / "evidence-probe-report.schema.json")
    data = parse_json(path)
    if not isinstance(data, dict):
        return [f"{path}: evidence probe report must be a JSON object"]
    errors.extend(validate_against_schema(path, data, schema))
    allowed_ids = {
        str(item.get("id"))
        for item in data.get("allowed_instruments", []) or []
        if isinstance(item, dict) and item.get("id")
    }
    for idx, command in enumerate(data.get("commands_run", []) or []):
        if not isinstance(command, dict):
            continue
        instrument_id = str(command.get("instrument_id", ""))
        if not instrument_id:
            errors.append(f"{path}: commands_run[{idx}].instrument_id is required")
        elif instrument_id not in allowed_ids:
            errors.append(
                f"{path}: commands_run[{idx}].instrument_id is not declared in allowed_instruments: {instrument_id}"
            )
    return errors


def _collect_artifact_paths(value: object, prefix: str) -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(prefix, value)]
    if isinstance(value, list):
        paths: list[tuple[str, str]] = []
        for idx, item in enumerate(value):
            paths.extend(_collect_artifact_paths(item, f"{prefix}[{idx}]"))
        return paths
    if isinstance(value, dict):
        paths = []
        for key, item in value.items():
            if prefix == "artifacts" and key == "root" and isinstance(item, str):
                continue
            paths.extend(_collect_artifact_paths(item, f"{prefix}.{key}"))
        return paths
    return []


def _collect_phase_status_artifact_paths(value: object, prefix: str) -> list[tuple[str, str]]:
    artifact_keys = {
        "artifact",
        "artifacts",
        "artifact_ref",
        "artifact_refs",
        "artifact_path",
        "artifact_paths",
        "behavior_binding",
        "behavior_bindings",
        "bundle",
        "bundles",
        "contract",
        "contract_ref",
        "contract_refs",
        "decision_packet",
        "decision_packets",
        "evidence",
        "evidence_artifacts",
        "evidence_bundle",
        "evidence_bundles",
        "evidence_ref",
        "evidence_refs",
        "evidence_report",
        "evidence_reports",
        "final_report",
        "gate_report",
        "gate_reports",
        "output",
        "output_ref",
        "output_refs",
        "outputs",
        "packet",
        "packets",
        "path",
        "plan",
        "report",
        "report_ref",
        "report_refs",
        "report_summaries",
        "report_summary",
        "reports",
        "ref",
        "refs",
        "review_packet",
        "review_packets",
        "review_packet_summary",
        "review_packet_summaries",
        "review_prompt_contract",
        "reviewer_report",
        "reviewer_reports",
        "reviewer_report_summaries",
        "reviewer_report_summary",
    }

    def is_artifact_key(key: str) -> bool:
        if key in artifact_keys:
            return True
        tokens = tuple(token for token in key.split("_") if token)
        if not tokens:
            return False
        terminal_artifact_tokens = {
            "artifact",
            "artifacts",
            "binding",
            "bindings",
            "contract",
            "contracts",
            "evidence",
            "evidences",
            "output",
            "outputs",
            "packet",
            "packets",
            "path",
            "paths",
            "plan",
            "plans",
            "report",
            "reports",
        }
        if tokens[-1] in terminal_artifact_tokens:
            return True
        qualified_terminal_tokens = {
            "bundle",
            "bundles",
            "draft",
            "drafts",
            "ref",
            "refs",
            "summary",
            "summaries",
        }
        artifact_qualifier_tokens = terminal_artifact_tokens | {"bundle", "bundles"}
        return tokens[-1] in qualified_terminal_tokens and any(
            token in artifact_qualifier_tokens for token in tokens[:-1]
        )

    if isinstance(value, list):
        paths: list[tuple[str, str]] = []
        for idx, item in enumerate(value):
            paths.extend(_collect_phase_status_artifact_paths(item, f"{prefix}[{idx}]"))
        return paths
    if isinstance(value, dict):
        paths = []
        for key, item in value.items():
            child_prefix = f"{prefix}.{key}"
            if is_artifact_key(key):
                paths.extend(_collect_artifact_paths(item, child_prefix))
            elif isinstance(item, (dict, list)):
                paths.extend(_collect_phase_status_artifact_paths(item, child_prefix))
        return paths
    return []


def _collect_workflow_run_artifact_paths(data: dict) -> list[tuple[str, str]]:
    paths: list[tuple[str, str]] = []
    artifacts = data.get("artifacts", {}) or {}
    if isinstance(artifacts, dict):
        paths.extend(_collect_artifact_paths(artifacts, "artifacts"))
    phase_evidence = data.get("phase_evidence")
    if phase_evidence is not None:
        paths.extend(_collect_artifact_paths(phase_evidence, "phase_evidence"))
    phase_status = data.get("phase_status", []) or []
    paths.extend(_collect_phase_status_artifact_paths(phase_status, "phase_status"))
    return paths


def _is_draft_safe_artifact_label(label: str) -> bool:
    if not label.startswith("artifacts."):
        return False
    artifact_ref = label.removeprefix("artifacts.")
    top_level_slot = artifact_ref.split(".", 1)[0].split("[", 1)[0]
    slot_tokens = tuple(token for token in top_level_slot.lower().split("_") if token)
    if "not" in slot_tokens or "nondraft" in slot_tokens:
        return False
    return "draft" in slot_tokens


def validate_workflow_run_phase_guard(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    phase_guard = data.get("phase_guard")
    if not isinstance(phase_guard, dict):
        return errors

    current_phase = str(phase_guard.get("current_phase", "")).strip()
    allowed_outputs = {
        str(item)
        for item in phase_guard.get("allowed_outputs", []) or []
        if isinstance(item, str)
    }
    draft_artifacts = {
        str(item)
        for item in phase_guard.get("draft_artifacts", []) or []
        if isinstance(item, str)
    }
    draft_allowed_overlap = sorted(allowed_outputs & draft_artifacts)
    if draft_allowed_overlap:
        errors.append(
            f"{path}: phase_guard allowed_outputs and draft_artifacts must not overlap: "
            f"{', '.join(draft_allowed_overlap)}"
        )
    forbidden_outputs: dict[str, dict] = {}
    for item in phase_guard.get("forbidden_outputs_until_phase_exit", []) or []:
        if isinstance(item, dict) and item.get("path"):
            forbidden_outputs[str(item["path"])] = item

    for label, artifact_path in _collect_workflow_run_artifact_paths(data):
        if artifact_path in forbidden_outputs:
            forbidden = forbidden_outputs[artifact_path]
            errors.append(
                f"{path}: {label} path {artifact_path} is forbidden in current phase "
                f"{current_phase} until phase {forbidden.get('until_phase')}: {forbidden.get('reason')}"
            )
            continue
        if artifact_path in draft_artifacts and _is_draft_safe_artifact_label(label):
            continue
        if artifact_path in draft_artifacts:
            draft_allowed = ", ".join(sorted(draft_artifacts)) if draft_artifacts else "<none>"
            errors.append(
                f"{path}: {label} path {artifact_path} is a draft artifact in current phase "
                f"{current_phase}; draft artifacts may only appear in draft-labeled top-level artifacts, "
                f"not evidence/output/report ledger fields. draft artifacts: {draft_allowed}"
            )
            continue
        if artifact_path in allowed_outputs:
            continue
        allowed = ", ".join(sorted(allowed_outputs)) if allowed_outputs else "<none>"
        errors.append(
            f"{path}: {label} path {artifact_path} is not allowed in current phase "
            f"{current_phase}; allowed outputs: {allowed}"
        )
    return errors


def validate_workflow_run_artifact(root: Path, path: Path) -> list[str]:
    schema = parse_json(root / "schemas" / "workflow-run.schema.json")
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"{path}: workflow run metadata must be a mapping"]
    errors = validate_against_schema(path, data, schema)
    errors.extend(validate_workflow_run_phase_guard(path, data))
    return errors


def validate_project_documentation_disposition_artifact(root: Path, path: Path) -> list[str]:
    schema = parse_json(root / "schemas" / "project-documentation-disposition.schema.json")
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"{path}: project documentation disposition must be a mapping"]
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


def required_workflow_gates(workflow_path: Path, selected_strictness: object) -> set[str]:
    if not workflow_path.exists():
        return set()
    data = parse_yaml(workflow_path) or {}
    if not isinstance(data, dict):
        return set()
    gates: set[str] = set()
    for phase in data.get("phases", []) or []:
        if not isinstance(phase, dict) or not phase.get("gate"):
            continue
        applies = phase.get("applies_to_strictness")
        if not applies:
            gates.add(str(phase["gate"]))
            continue
        if str(selected_strictness) in {str(item) for item in applies or []}:
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
    mode_outputs = data.get("mode_gated_outputs", {}) or {}
    onboarding_outputs = set(mode_outputs.get("adoption-onboarding", []) or [])
    if "project-operating-decisions.yaml" not in onboarding_outputs:
        errors.append(f"{path}: adoption-onboarding outputs must include project-operating-decisions.yaml")
    if "project-operating-decisions-interview" not in skills:
        errors.append(f"{path}: project-initialization must use project-operating-decisions-interview skill")
    if "project-operating-decisions.yaml" not in templates:
        errors.append(f"{path}: project-initialization must use project-operating-decisions.yaml template")
    if "project-documentation-disposition.yaml" not in templates:
        errors.append(f"{path}: project-initialization must use project-documentation-disposition.yaml template")
    interview = phase_by_id.get("operating_decisions_interview")
    if not interview:
        errors.append(f"{path}: project-initialization must include operating_decisions_interview phase")
    else:
        interview_applies = set(str(item) for item in interview.get("applies_to_intent_modes", []) or [])
        if interview_applies != {"adoption-onboarding"}:
            errors.append(f"{path}: operating_decisions_interview must apply only to adoption-onboarding")
        if "project-operating-decisions.yaml" not in set(interview.get("outputs", []) or []):
            errors.append(f"{path}: operating_decisions_interview must output project-operating-decisions.yaml")
    target_decisions = phase_by_id.get("target_workflow_context_decision_packet")
    if not isinstance(target_decisions, dict):
        errors.append(f"{path}: project-initialization must include target_workflow_context_decision_packet phase")
    else:
        applies = set(str(item) for item in target_decisions.get("applies_to_intent_modes", []) or [])
        if applies != {"prepare-workflow"}:
            errors.append(f"{path}: target_workflow_context_decision_packet must apply only to prepare-workflow")
        outputs = set(str(item) for item in target_decisions.get("outputs", []) or [])
        if "target workflow human decision packet" not in outputs:
            errors.append(f"{path}: target_workflow_context_decision_packet must output target workflow human decision packet")
        human = target_decisions.get("human_interaction", {}) or {}
        if human.get("response_artifact") == "project-operating-decisions.yaml":
            errors.append(f"{path}: target_workflow_context_decision_packet must not write project-operating-decisions.yaml")
        inputs = set(str(item) for item in target_decisions.get("inputs", []) or [])
        if "project-documentation-disposition.yaml" not in inputs:
            errors.append(f"{path}: target_workflow_context_decision_packet must consume project-documentation-disposition.yaml")
    overlay = phase_by_id.get("overlay_draft")
    if overlay:
        inputs = set(overlay.get("inputs", []) or [])
        has_operating_decisions = any(str(item).startswith("project-operating-decisions.yaml") for item in inputs)
        has_existing_policy = any("existing project policy/workflow binding" in str(item) for item in inputs)
        if not has_operating_decisions:
            errors.append(f"{path}: overlay_draft must consume project-operating-decisions.yaml for onboarding")
        if not has_existing_policy:
            errors.append(f"{path}: overlay_draft must allow existing project policy/workflow binding for prepare-workflow")
        if "project-documentation-disposition.yaml" not in inputs:
            errors.append(f"{path}: overlay_draft must consume project-documentation-disposition.yaml")
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
        "documentation_disposition_decision",
        "read_project_intake",
        "legacy_adoption_mode_decision",
        "operating_decisions_interview",
        "target_workflow_context_decision_packet",
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


def validate_project_initialization_intent_mode_policy(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("name") != "project-initialization":
        return errors

    intent_modes = data.get("intent_modes", {}) or {}
    supported = set(str(item) for item in intent_modes.get("supported", []) or [])
    required_modes = {
        "unknown-discovery",
        "adoption-onboarding",
        "prepare-workflow",
        "legacy-cleanup",
        "risk-domain-assessment",
    }
    missing = sorted(required_modes - supported)
    if intent_modes.get("required") is not True:
        errors.append(f"{path}: project-initialization intent_modes.required must be true")
    if intent_modes.get("prepare_workflow_requires_target_workflow") is not True:
        errors.append(f"{path}: prepare-workflow must require target_workflow")
    if missing:
        errors.append(f"{path}: intent_modes.supported missing: {', '.join(missing)}")
    outputs = set(str(item) for item in data.get("outputs", []) or [])
    mode_outputs = {
        str(mode): [str(item) for item in outputs_for_mode or []]
        for mode, outputs_for_mode in (data.get("mode_gated_outputs", {}) or {}).items()
    }

    def mode_has(mode: str, text: str) -> bool:
        return any(text in item for item in mode_outputs.get(mode, []))

    def mode_missing(mode: str, required_texts: list[str]) -> list[str]:
        return [text for text in required_texts if not mode_has(mode, text)]

    onboarding_only_output_patterns = [
        ".agentsflow/agentsflow.lock.yaml",
        ".agentsflow/project.yaml",
        "project-operating-decisions.yaml",
        "project-documentation-disposition.yaml",
        "workflow bindings",
        "workflow bindings draft",
        "project-bound gate drafts",
        "initialization-report.md",
        "legacy-agent-system-inventory.json",
        "legacy-adoption-decision.yaml",
        "active-instruction-map.yaml",
    ]
    leaked_outputs = sorted(
        item
        for item in outputs
        if any(pattern in item for pattern in onboarding_only_output_patterns)
    )
    if leaked_outputs:
        errors.append(
            f"{path}: top-level outputs must be mode-neutral; move mode-specific outputs to mode_gated_outputs: "
            + ", ".join(leaked_outputs)
        )
    required_mode_outputs = {
        "unknown-discovery": [
            "project-raw-scan.json",
            "project-inventory.json",
            "project-assessment.architecture.json",
            "project-assessment.verification.json",
            "project-assessment.adversarial.json",
            "project-assessment.json",
            "human-questions.yaml",
        ],
        "adoption-onboarding": [
            "project-documentation-disposition.yaml",
            "project-operating-decisions.yaml",
            ".agentsflow/project.yaml draft",
            "workflow bindings draft",
            "project-bound gate drafts",
            "active-instruction-map.yaml draft",
            "legacy-agent-system-inventory.json when legacy artifacts are in scope",
            "legacy-adoption-decision.yaml when legacy artifacts are in scope",
            "agent-instruction-migration-plan.md when legacy artifacts are in scope",
            "legacy-backup-manifest.yaml when legacy artifacts are in scope",
            "initialization-report.md",
        ],
        "prepare-workflow": [
            "project-documentation-disposition.yaml",
            "target workflow binding draft",
            "target workflow gate readiness report",
            "target workflow human decision packet",
            "finding-validation-report.md",
            "review-cycle-report.md",
        ],
        "legacy-cleanup": [
            "project-documentation-disposition.yaml",
            "legacy-agent-system-inventory.json",
            "legacy-adoption-decision.yaml",
            "agent-instruction-migration-plan.md",
            "active-instruction-map.yaml draft",
        ],
        "risk-domain-assessment": [
            "domain-identification section",
            "project-assessment.architecture.json",
            "project-assessment.verification.json",
            "project-assessment.adversarial.json",
            "project-assessment.json",
            "human domain-expertise questions",
        ],
    }
    for mode, required_texts in required_mode_outputs.items():
        missing_mode_outputs = mode_missing(mode, required_texts)
        if missing_mode_outputs:
            errors.append(
                f"{path}: mode_gated_outputs.{mode} missing: {', '.join(missing_mode_outputs)}"
            )
    forbidden_mode_outputs = {
        "unknown-discovery": [
            ".agentsflow/project.yaml",
            "workflow bindings",
            "project-bound gate",
            "project-operating-decisions.yaml",
            "initialization-report.md",
            "active-instruction-map.yaml",
        ],
        "prepare-workflow": [
            ".agentsflow/project.yaml",
            "project-operating-decisions.yaml",
            "workflow bindings draft",
            "project-bound gate drafts",
            "initialization-report.md",
            "active-instruction-map.yaml",
        ],
        "risk-domain-assessment": [
            ".agentsflow/project.yaml",
            "workflow bindings",
            "project-bound gate",
            "project-operating-decisions.yaml",
            "initialization-report.md",
            "active-instruction-map.yaml",
        ],
    }
    for mode, forbidden_texts in forbidden_mode_outputs.items():
        forbidden_present = [
            item
            for item in mode_outputs.get(mode, [])
            if any(forbidden_text in item for forbidden_text in forbidden_texts)
        ]
        if forbidden_present:
            errors.append(
                f"{path}: mode_gated_outputs.{mode} must not include activation outputs: "
                + ", ".join(forbidden_present)
            )

    phase_policy = data.get("intent_mode_phase_policy", {}) or {}
    unknown_policy = phase_policy.get("unknown-discovery", {}) or {}
    risk_policy = phase_policy.get("risk-domain-assessment", {}) or {}
    prepare_policy = phase_policy.get("prepare-workflow", {}) or {}
    must_not_require = set(str(item) for item in unknown_policy.get("must_not_require", []) or [])
    risk_must_not_require = set(str(item) for item in risk_policy.get("must_not_require", []) or [])
    mode_specific_activation_phases = [
        "operating_decisions_interview",
        "overlay_draft",
        "project_initialization_gate",
        "documentation_disposition_decision",
        "target_workflow_context_decision_packet",
        "target_workflow_readiness_gate",
        "initialization_review",
        "finding_validation",
        "human_approval",
    ]
    for phase_id in mode_specific_activation_phases:
        if phase_id not in must_not_require:
            errors.append(f"{path}: unknown-discovery must not require {phase_id}")
    for phase_id in [
        "overlay_draft",
        "project_initialization_gate",
        "documentation_disposition_decision",
        "target_workflow_context_decision_packet",
        "target_workflow_readiness_gate",
        "initialization_review",
        "finding_validation",
        "human_approval",
    ]:
        if phase_id not in risk_must_not_require:
            errors.append(f"{path}: risk-domain-assessment must not require {phase_id}")
    if prepare_policy.get("requires_target_workflow") is not True:
        errors.append(f"{path}: prepare-workflow phase policy must require target_workflow")
    if prepare_policy.get("requires_sufficient_operating_context") is not True:
        errors.append(f"{path}: prepare-workflow phase policy must require sufficient operating context")
    if prepare_policy.get("target_workflow_context_decision_packet") != "conditional_when_target_workflow_policy_is_missing":
        errors.append(f"{path}: prepare-workflow phase policy must use target_workflow_context_decision_packet for missing context")
    if "operating_decisions_interview" in prepare_policy:
        errors.append(f"{path}: prepare-workflow phase policy must not use operating_decisions_interview")
    prepare_requires = set(str(item) for item in prepare_policy.get("requires", []) or [])
    prepare_conditional_requires = set(str(item) for item in prepare_policy.get("conditional_requires", []) or [])
    if "target_workflow_context_decision_packet" in prepare_requires:
        errors.append(f"{path}: prepare-workflow must not require target_workflow_context_decision_packet unconditionally")
    if "target_workflow_context_decision_packet" not in prepare_conditional_requires:
        errors.append(f"{path}: prepare-workflow conditional_requires must include target_workflow_context_decision_packet")

    phase_by_id = {
        phase.get("id"): phase
        for phase in data.get("phases", []) or []
        if isinstance(phase, dict) and phase.get("id")
    }
    for phase_id in [
        "documentation_disposition_decision",
        "operating_decisions_interview",
        "overlay_draft",
        "project_initialization_gate",
        "target_workflow_context_decision_packet",
        "target_workflow_readiness_gate",
        "initialization_review",
        "finding_validation",
        "human_approval",
    ]:
        phase = phase_by_id.get(phase_id)
        if not isinstance(phase, dict):
            continue
        applies = set(str(item) for item in phase.get("applies_to_intent_modes", []) or [])
        if not applies:
            errors.append(f"{path}: phase {phase_id} must declare applies_to_intent_modes")
        if "unknown-discovery" in applies:
            errors.append(f"{path}: phase {phase_id} must not apply to unknown-discovery by default")
        if "risk-domain-assessment" in applies:
            errors.append(f"{path}: phase {phase_id} must not apply to risk-domain-assessment by default")
    attach = phase_by_id.get("attach_or_verify_upstream")
    if isinstance(attach, dict):
        attach_applies = set(str(item) for item in attach.get("applies_to_intent_modes", []) or [])
        if not attach_applies:
            errors.append(f"{path}: attach_or_verify_upstream must declare applies_to_intent_modes")
        for mode in ["unknown-discovery", "risk-domain-assessment"]:
            if mode in attach_applies:
                errors.append(f"{path}: attach_or_verify_upstream must not apply to {mode} by default")
    for phase_id in ["operating_decisions_interview", "human_approval"]:
        phase = phase_by_id.get(phase_id, {}) or {}
        human = phase.get("human_interaction", {}) or {}
        if human.get("required") is True:
            errors.append(f"{path}: phase {phase_id} human_interaction.required must be conditional")

    expected_mode_phases = {
        "documentation_disposition_decision": {
            "adoption-onboarding",
            "legacy-cleanup",
            "prepare-workflow",
        },
        "legacy_agent_system_discovery": {"adoption-onboarding", "legacy-cleanup"},
        "project_initialization_gate": {"adoption-onboarding"},
        "target_workflow_context_decision_packet": {"prepare-workflow"},
        "target_workflow_readiness_gate": {"prepare-workflow"},
        "initialization_review": {"adoption-onboarding", "prepare-workflow"},
        "finding_validation": {"adoption-onboarding", "prepare-workflow"},
    }
    for phase_id, expected_modes in expected_mode_phases.items():
        phase = phase_by_id.get(phase_id)
        if not isinstance(phase, dict):
            errors.append(f"{path}: project-initialization must include {phase_id} phase")
            continue
        applies = set(str(item) for item in phase.get("applies_to_intent_modes", []) or [])
        if applies != expected_modes:
            errors.append(
                f"{path}: phase {phase_id} must apply exactly to: {', '.join(sorted(expected_modes))}"
            )

    project_gate = phase_by_id.get("project_initialization_gate", {}) or {}
    if project_gate.get("gate") != "project_initialization_gate":
        errors.append(f"{path}: project_initialization_gate phase must bind project_initialization_gate")
    target_gate = phase_by_id.get("target_workflow_readiness_gate", {}) or {}
    if target_gate.get("kind") != "gate":
        errors.append(f"{path}: target_workflow_readiness_gate phase must be kind gate")
    if target_gate.get("gate") != "target_workflow_readiness_gate":
        errors.append(f"{path}: target_workflow_readiness_gate phase must bind target_workflow_readiness_gate")

    initialization_review = phase_by_id.get("initialization_review", {}) or {}
    if initialization_review.get("kind") != "review":
        errors.append(f"{path}: initialization_review phase must be kind review")
    review_runs_after = set(str(item) for item in initialization_review.get("runs_after", []) or [])
    for required_gate_phase in ["project_initialization_gate", "target_workflow_readiness_gate"]:
        if required_gate_phase not in review_runs_after:
            errors.append(f"{path}: initialization_review must run after {required_gate_phase}")
    if initialization_review.get("runs_after_policy") != "after_applicable_intent_mode_gate":
        errors.append(f"{path}: initialization_review must use after_applicable_intent_mode_gate runs_after_policy")

    documentation_disposition = phase_by_id.get("documentation_disposition_decision", {}) or {}
    if documentation_disposition.get("kind") != "decision":
        errors.append(f"{path}: documentation_disposition_decision phase must be kind decision")
    doc_outputs = set(str(item) for item in documentation_disposition.get("outputs", []) or [])
    if "project-documentation-disposition.yaml" not in doc_outputs:
        errors.append(
            f"{path}: documentation_disposition_decision must output project-documentation-disposition.yaml"
        )
    doc_inputs = set(str(item) for item in documentation_disposition.get("inputs", []) or [])
    for required_input in [
        "documentation-history-index.md",
        "project-inventory.json",
        "project-assessment.json",
    ]:
        if required_input not in doc_inputs:
            errors.append(f"{path}: documentation_disposition_decision must consume {required_input}")
    doc_runs_after = set(str(item) for item in documentation_disposition.get("runs_after", []) or [])
    for required_phase in ["documentation_and_history_discovery", "expert_assessment"]:
        if required_phase not in doc_runs_after:
            errors.append(f"{path}: documentation_disposition_decision must run after {required_phase}")

    legacy_decision = phase_by_id.get("legacy_adoption_mode_decision", {}) or {}
    legacy_inputs = set(str(item) for item in legacy_decision.get("inputs", []) or [])
    if "project-documentation-disposition.yaml" not in legacy_inputs:
        errors.append(f"{path}: legacy_adoption_mode_decision must consume project-documentation-disposition.yaml")

    finding_validation = phase_by_id.get("finding_validation", {}) or {}
    if finding_validation.get("kind") != "finding_validation":
        errors.append(f"{path}: finding_validation phase must be kind finding_validation")
    validation_runs_after = set(str(item) for item in finding_validation.get("runs_after", []) or [])
    if "initialization_review" not in validation_runs_after:
        errors.append(f"{path}: finding_validation phase must run after initialization_review")

    human_approval = phase_by_id.get("human_approval", {}) or {}
    human_runs_after = set(str(item) for item in human_approval.get("runs_after", []) or [])
    for required_phase in ["finding_validation", "legacy_migration_or_quarantine_plan"]:
        if required_phase not in human_runs_after:
            errors.append(f"{path}: human_approval must run after {required_phase} when applicable")
    if human_approval.get("runs_after_policy") != "after_applicable_intent_mode_preapproval_phase":
        errors.append(f"{path}: human_approval must use after_applicable_intent_mode_preapproval_phase runs_after_policy")

    phase_order = {
        str(phase.get("id")): index
        for index, phase in enumerate(data.get("phases", []) or [])
        if isinstance(phase, dict) and phase.get("id")
    }
    ordered_backbone = [
        "raw_project_scan",
        "structured_project_inventory",
        "domain_identification",
        "expert_assessment",
    ]
    for before, after in zip(ordered_backbone, ordered_backbone[1:]):
        if before in phase_order and after in phase_order and phase_order[before] >= phase_order[after]:
            errors.append(f"{path}: {before} must appear before {after}")
    for legacy_phase in ["legacy_adoption_mode_decision", "legacy_migration_or_quarantine_plan"]:
        if (
            legacy_phase in phase_order
            and "expert_assessment" in phase_order
            and phase_order[legacy_phase] <= phase_order["expert_assessment"]
        ):
            errors.append(f"{path}: {legacy_phase} must run after expert_assessment")

    forbidden_phase_outputs_by_mode = {
        "prepare-workflow": ["project-operating-decisions.yaml"],
        "unknown-discovery": [
            "project-operating-decisions.yaml",
            "project.yaml draft",
            "workflow bindings draft",
            "project-bound gate drafts",
            "active-instruction-map.yaml",
        ],
        "risk-domain-assessment": [
            "project-operating-decisions.yaml",
            "project.yaml draft",
            "workflow bindings draft",
            "project-bound gate drafts",
            "active-instruction-map.yaml",
        ],
    }
    for phase in data.get("phases", []) or []:
        if not isinstance(phase, dict):
            continue
        applies = set(str(item) for item in phase.get("applies_to_intent_modes", []) or [])
        if not applies and phase_policy.get("phases_without_applies_to_intent_modes_apply_to_all") is True:
            applies = supported
        phase_outputs = [str(item) for item in phase.get("outputs", []) or []]
        phase_human = phase.get("human_interaction", {}) or {}
        response_artifact = str(phase_human.get("response_artifact", ""))
        for mode, forbidden_patterns in forbidden_phase_outputs_by_mode.items():
            if mode not in applies:
                continue
            forbidden_present = [
                item
                for item in [*phase_outputs, response_artifact]
                if any(pattern in item for pattern in forbidden_patterns)
            ]
            if forbidden_present:
                errors.append(
                    f"{path}: phase {phase.get('id')} must not produce {mode} forbidden artifact(s): "
                    + ", ".join(sorted(set(forbidden_present)))
                )

    review = data.get("review", {}) or {}
    if isinstance(review, dict) and review.get("topology") not in {None, "none"}:
        gates = set(str(item) for item in review.get("gates", []) or [])
        for gate_id in ["project_initialization_gate", "target_workflow_readiness_gate"]:
            if gate_id not in gates:
                errors.append(f"{path}: project-initialization review.gates must include {gate_id}")
    return errors


def validate_big_feature_plan_gate_policy(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("name") != "big-feature-contract-first":
        return errors
    phases = [
        phase
        for phase in data.get("phases", []) or []
        if isinstance(phase, dict)
    ]
    phase_by_id = {str(phase.get("id")): phase for phase in phases if phase.get("id")}
    technical_plan = phase_by_id.get("technical_plan")
    plan_gate = phase_by_id.get("plan_gate")
    red_capture = phase_by_id.get("red_capture")
    required_plan_artifacts = {
        "repository-grounding-report.md",
        "plan.md",
        "task-breakdown.md",
        "decision-contract.md",
    }
    if not isinstance(technical_plan, dict):
        errors.append(f"{path}: big-feature-contract-first must include technical_plan phase before plan_gate")
    else:
        outputs = set(str(item) for item in technical_plan.get("outputs", []) or [])
        missing_outputs = sorted(required_plan_artifacts - outputs)
        if missing_outputs:
            errors.append(f"{path}: technical_plan phase missing outputs: {', '.join(missing_outputs)}")
        applies = set(str(item) for item in technical_plan.get("applies_to_strictness", []) or [])
        if applies != {"L3", "L4"}:
            errors.append(f"{path}: technical_plan phase must apply exactly to strictness L3 and L4")
    if not isinstance(plan_gate, dict):
        errors.append(f"{path}: big-feature-contract-first must include plan_gate phase")
    else:
        if plan_gate.get("kind") not in {"gate", "verification"}:
            errors.append(f"{path}: plan_gate phase must be kind gate or verification")
        if plan_gate.get("gate") != "plan_gate":
            errors.append(f"{path}: plan_gate phase must bind gate plan_gate")
        applies = set(str(item) for item in plan_gate.get("applies_to_strictness", []) or [])
        if applies != {"L3", "L4"}:
            errors.append(f"{path}: plan_gate phase must apply exactly to strictness L3 and L4")
        runs_after = set(str(item) for item in plan_gate.get("runs_after", []) or [])
        if "technical_plan" not in runs_after:
            errors.append(f"{path}: plan_gate phase must run after technical_plan")
    if isinstance(red_capture, dict):
        runs_after = set(str(item) for item in red_capture.get("runs_after", []) or [])
        if "plan_gate" not in runs_after:
            errors.append(f"{path}: red_capture phase must run after plan_gate")
        if red_capture.get("runs_after_policy") != "after_applicable_strictness_gate":
            errors.append(f"{path}: red_capture phase must use after_applicable_strictness_gate runs_after_policy")
    review_gates = set(str(item) for item in ((data.get("review", {}) or {}).get("gates", []) or []))
    if "plan_gate" not in review_gates:
        errors.append(f"{path}: review.gates must include plan_gate")
    concrete_gates = set(str(item) for item in data.get("concrete_gates", []) or [])
    if "plan_gate" not in concrete_gates:
        errors.append(f"{path}: concrete_gates must include plan_gate")
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


def validate_required_review_gate_order(path: Path, data: dict) -> list[str]:
    required_by_workflow = {
        "big-feature-contract-first": {
            "review_phase": "review",
            "gate_phase": "verification_gate",
            "gate": "verification_gate",
        },
        "review-only-fusion": {
            "review_phase": "independent_review",
            "gate_phase": "evidence_gate",
            "gate": "evidence_gate",
        },
        "new-project-spec-first": {
            "review_phase": "spec_review",
            "gate_phase": "spec_review_gate",
            "gate": "spec_review_gate",
        },
        "bugfix-regression-capture": {
            "review_phase": "review",
            "gate_phase": "regression_verification_gate",
            "gate": "regression_gate",
        },
    }
    rule = required_by_workflow.get(str(data.get("name")))
    if not rule:
        return []
    errors: list[str] = []
    phases = [
        phase
        for phase in data.get("phases", []) or []
        if isinstance(phase, dict)
    ]
    phase_by_id = {str(phase.get("id")): phase for phase in phases if phase.get("id")}
    gate_phase = phase_by_id.get(rule["gate_phase"])
    review_phase = phase_by_id.get(rule["review_phase"])
    if not gate_phase:
        errors.append(f"{path}: workflow {data.get('name')} must include phase {rule['gate_phase']}")
    else:
        if gate_phase.get("kind") not in {"verification", "gate"}:
            errors.append(f"{path}: phase {rule['gate_phase']} must be kind verification or gate")
        if gate_phase.get("gate") != rule["gate"]:
            errors.append(f"{path}: phase {rule['gate_phase']} must bind gate {rule['gate']}")
    if not review_phase:
        errors.append(f"{path}: workflow {data.get('name')} must include review phase {rule['review_phase']}")
    else:
        if review_phase.get("kind") != "review":
            errors.append(f"{path}: phase {rule['review_phase']} must be kind review")
        runs_after = set(str(item) for item in review_phase.get("runs_after", []) or [])
        if rule["gate_phase"] not in runs_after:
            errors.append(
                f"{path}: review phase {rule['review_phase']} must run after {rule['gate_phase']}"
            )
    if gate_phase and review_phase:
        gate_index = phases.index(gate_phase)
        review_index = phases.index(review_phase)
        if gate_index >= review_index:
            errors.append(f"{path}: phase {rule['gate_phase']} must appear before {rule['review_phase']}")
    return errors


def validate_review_fusion_validation_order(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("name") not in MVP_WORKFLOWS:
        return errors
    phases = [
        phase
        for phase in data.get("phases", []) or []
        if isinstance(phase, dict)
    ]
    validation_phase = next((phase for phase in phases if phase.get("kind") == "finding_validation"), None)
    review_phases = [phase for phase in phases if phase.get("kind") == "review"]
    post_gate_review_phases = [
        phase for phase in review_phases if phase.get("runs_after")
    ]
    fusion_phases = [phase for phase in phases if phase.get("kind") == "fusion"]
    if not post_gate_review_phases and not fusion_phases:
        return errors
    if validation_phase is None:
        errors.append(f"{path}: MVP workflow with post-gate review or fusion must include finding_validation phase")
        return errors
    if fusion_phases and not review_phases:
        errors.append(f"{path}: MVP workflow with fusion phase must include review phase")
        return errors
    first_review_index = min(phases.index(phase) for phase in (post_gate_review_phases or review_phases))
    validation_index = phases.index(validation_phase)
    validation_runs_after = set(str(item) for item in validation_phase.get("runs_after", []) or [])
    if fusion_phases:
        first_fusion_index = min(phases.index(phase) for phase in fusion_phases)
        if not (first_review_index < first_fusion_index < validation_index):
            errors.append(f"{path}: review/fusion/validation order must be review -> fusion -> finding_validation")
        fusion_ids = {str(phase.get("id")) for phase in fusion_phases if phase.get("id")}
        if fusion_ids and not (fusion_ids & validation_runs_after):
            errors.append(f"{path}: finding_validation phase must run after fusion")
    else:
        if not (first_review_index < validation_index):
            errors.append(f"{path}: review/validation order must be review -> finding_validation")
        review_ids_for_validation = {str(phase.get("id")) for phase in post_gate_review_phases if phase.get("id")}
        if review_ids_for_validation and not (review_ids_for_validation & validation_runs_after):
            errors.append(f"{path}: finding_validation phase must run after review")
    review_ids = {str(phase.get("id")) for phase in review_phases if phase.get("id")}
    for fusion in fusion_phases:
        runs_after = set(str(item) for item in fusion.get("runs_after", []) or [])
        if review_ids and not (review_ids & runs_after):
            errors.append(f"{path}: fusion phase {fusion.get('id')} must run after review")
    return errors


def validate_mvp_review_materiality_policy(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("name") not in MVP_WORKFLOWS:
        return errors
    review_cycle = data.get("review_cycle")
    if not isinstance(review_cycle, dict):
        return errors
    do_not_rerun = set(str(item) for item in review_cycle.get("do_not_rerun_on", []) or [])
    if "nonblocking_findings_only" in do_not_rerun:
        errors.append(f"{path}: do_not_rerun_on must not use ambiguous nonblocking_findings_only")
    if "nonblocking_findings_with_non_material_fixes_only" not in do_not_rerun:
        errors.append(f"{path}: do_not_rerun_on must include nonblocking_findings_with_non_material_fixes_only")
    materiality = review_cycle.get("materiality_classification")
    if not isinstance(materiality, dict):
        errors.append(f"{path}: review_cycle.materiality_classification is required")
        return errors
    if materiality.get("required_after_review_fixes") is not True:
        errors.append(f"{path}: materiality_classification.required_after_review_fixes must be true")
    if materiality.get("material_triggers_take_precedence_over_do_not_rerun") is not True:
        errors.append(
            f"{path}: materiality_classification.material_triggers_take_precedence_over_do_not_rerun must be true"
        )
    if not materiality.get("material_if_changes"):
        errors.append(f"{path}: materiality_classification.material_if_changes is required")
    if not materiality.get("non_material_if_only"):
        errors.append(f"{path}: materiality_classification.non_material_if_only is required")
    controls = data.get("review_control_rules", {}) or {}
    if controls.get("post_fix_materiality_classification_required") is not True:
        errors.append(f"{path}: review_control_rules.post_fix_materiality_classification_required must be true")
    return errors


def validate_phase_scripts_declared(path: Path, data: dict) -> list[str]:
    uses_scripts = set((data.get("uses") or {}).get("scripts", []) or [])
    missing: set[str] = set()
    for phase in data.get("phases", []) or []:
        if not isinstance(phase, dict):
            continue
        for script in phase.get("scripts", []) or []:
            if script not in uses_scripts:
                missing.add(str(script))
    if missing:
        return [f"{path}: phase scripts missing from uses.scripts: {', '.join(sorted(missing))}"]
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
                missing_gates = sorted(
                    required_workflow_gates(extends_path, binding.get("strictness"))
                    - set(str(key) for key in gates)
                )
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
        errors.extend(validate_no_duplicate_yaml_keys(p))
        try:
            parse_yaml(p)
        except ValueError as exc:
            errors.append(str(exc))
    for p in root.rglob("*.yml"):
        errors.extend(validate_no_duplicate_yaml_keys(p))
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
    errors.extend(validate_evidence_probe_report_artifact(root, root / "templates" / "evidence-probe-report.json"))
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
    for documentation_disposition in [
        root / "templates" / "project-documentation-disposition.yaml",
        root / "examples" / "project-initialization" / "project-documentation-disposition.yaml",
    ]:
        errors.extend(validate_project_documentation_disposition_artifact(root, documentation_disposition))
    run_artifact_patterns = [
        "Docs/agentsflow/runs/*/run.yaml",
        "examples/**/Docs/agentsflow/runs/*/run.yaml",
    ]
    for run_artifact in {
        path
        for pattern in run_artifact_patterns
        for path in root.glob(pattern)
    }:
        errors.extend(validate_workflow_run_artifact(root, run_artifact))
    for prompt_contract in root.glob("examples/**/Docs/agentsflow/runs/*/review-prompt-contract.yaml"):
        schema = parse_json(root / "schemas" / "review-prompt-contract.schema.json")
        data = parse_yaml(prompt_contract) or {}
        if not isinstance(data, dict):
            errors.append(f"{prompt_contract}: review prompt contract must be a mapping")
        else:
            errors.extend(validate_against_schema(prompt_contract, data, schema))
            errors.extend(validate_review_prompt_contract_invariants(root, prompt_contract, data, True))
            errors.extend(validate_review_prompt_contract_run_references(root, prompt_contract, data))
    for review_packet in root.glob("examples/**/Docs/agentsflow/runs/*/review-packets/*.json"):
        if review_packet.name == "shared-content.json":
            continue
        errors.extend(validate_review_packet_artifact(root, review_packet, True))
    for reviewer_report in root.glob("examples/**/Docs/agentsflow/runs/*/reviewer-report*.json"):
        errors.extend(validate_reviewer_report_artifact(root, reviewer_report))
    for probe_report in root.glob("examples/**/Docs/agentsflow/runs/*/evidence-probe-report*.json"):
        errors.extend(validate_evidence_probe_report_artifact(root, probe_report))

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
        "templates/evidence-probe-report.json",
        "templates/project-intake.yaml",
        "templates/research-assignment.unknown-project.md",
        "templates/project-raw-scan.json",
        "templates/project-inventory.json",
        "templates/project-assessment.json",
        "templates/project-operating-decisions.yaml",
        "templates/project-documentation-disposition.yaml",
        "templates/human-questions.yaml",
        "templates/human-decisions.yaml",
        "templates/initialization-report.md",
        "templates/workflow-run.yaml",
        "schemas/project-intake.schema.json",
        "schemas/project-raw-scan.schema.json",
        "schemas/project-inventory.schema.json",
        "schemas/project-assessment.schema.json",
        "schemas/project-operating-decisions.schema.json",
        "schemas/project-documentation-disposition.schema.json",
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
        "schemas/evidence-probe-report.schema.json",
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
        errors.extend(validate_project_initialization_intent_mode_policy(wf, data))
        errors.extend(validate_big_feature_plan_gate_policy(wf, data))
        errors.extend(validate_supported_review_topologies(wf, data))
        errors.extend(validate_upstream_review_cycle_policy(wf, data))
        errors.extend(validate_mvp_review_phase_policy(wf, data))
        errors.extend(validate_required_review_gate_order(wf, data))
        errors.extend(validate_review_fusion_validation_order(wf, data))
        errors.extend(validate_mvp_review_materiality_policy(wf, data))
        errors.extend(validate_phase_scripts_declared(wf, data))
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
