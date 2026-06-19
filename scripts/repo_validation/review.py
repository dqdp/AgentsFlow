from __future__ import annotations

import json
from pathlib import Path

from .collect import collect_yaml_manifest_names
from .common import (
    compare_hash,
    parse_json,
    parse_yaml,
    sha256_file,
    sha256_text,
    validate_against_schema,
)


ROLE_CONTRACT_PREFIXES = ('profiles/reviewer_roles/', '.agentsflow/profiles/reviewer_roles/')
MVP_WORKFLOWS = {
    'project-initialization',
    'big-feature-contract-first',
    'bugfix-regression-capture',
    'review-only-fusion',
    'new-project-spec-first',
}


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


def validate_reviewer_report_artifact(root: Path, path: Path) -> list[str]:
    schema = parse_json(root / "schemas" / "reviewer-report.schema.json")
    data = parse_json(path)
    if not isinstance(data, dict):
        return [f"{path}: reviewer report must be a JSON object"]
    return validate_against_schema(path, data, schema)


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

