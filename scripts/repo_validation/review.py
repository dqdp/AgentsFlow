from __future__ import annotations

import json
from pathlib import Path

import yaml

from reviewers.prompt_rendering import render_review_prompt

from .collect import collect_yaml_manifest_names
from .common import (
    compare_hash,
    is_concrete_sha256,
    parse_json,
    parse_yaml,
    sha256_file,
    sha256_text,
    validate_against_schema,
)


ROLE_CONTRACT_PREFIXES = ('profiles/reviewer_roles/', '.agentsflow/profiles/reviewer_roles/')
SUPPORTED_REVIEW_PROVIDERS = {"internal-agent", "claude-code"}
V0_2_SUPPORTED_TARGET_WORKFLOWS = {
    'big-feature-contract-first',
}
V0_2_UTILITY_WORKFLOWS = {
    'review-only-fusion',
}
V0_2_REVIEW_CONTROL_WORKFLOWS = (
    V0_2_SUPPORTED_TARGET_WORKFLOWS | V0_2_UTILITY_WORKFLOWS
)
VERIFICATION_GATE_RESULT_STATES = {
    "pass",
    "pass_with_notes",
    "fail",
    "inconclusive",
    "needs_human_decision",
    "blocked",
}


def _is_agentsflow_run_artifact_path(path: Path) -> bool:
    parts = path.parts
    return any(
        parts[index : index + 3] == ("Docs", "agentsflow", "runs")
        for index in range(len(parts) - 2)
    )


def _agentsflow_run_dir(path: Path) -> Path | None:
    parts = path.resolve().parts
    for index in range(len(parts) - 3):
        if parts[index : index + 3] == ("Docs", "agentsflow", "runs"):
            return Path(*parts[: index + 4])
    return None


def _is_within_path(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _is_run_scope_artifact(path: Path, data: dict) -> bool:
    return data.get("artifact_scope", "run") == "run" or _is_agentsflow_run_artifact_path(path)


def _strip_fragment(ref: object) -> str:
    return str(ref).split("#", 1)[0]


def _is_placeholder_ref(ref: object) -> bool:
    text = str(ref)
    return ("<" in text and ">" in text) or "YYYY-MM-DD-task-slug" in text


def _allows_placeholder_verification_refs(path: Path, data: dict) -> bool:
    return (
        not _is_agentsflow_run_artifact_path(path)
        and data.get("artifact_scope") in {"example", "template"}
    )


def _resolve_review_packet_ref(root: Path, packet_path: Path, ref: object) -> Path | None:
    text = _strip_fragment(ref).strip()
    if not text:
        return None
    ref_path = Path(text)
    if ref_path.is_absolute() or ".." in ref_path.parts:
        return None

    candidates = [root / ref_path, packet_path.parent / ref_path]
    if packet_path.parent.name == "review-packets":
        candidates.append(packet_path.parent.parent / ref_path)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def _is_verification_gate_report_artifact(path: Path) -> bool:
    normalized_name = path.name.replace("_", "-")
    if "verification-gate-report" not in normalized_name:
        return False
    if path.suffix == ".md":
        try:
            first_line = path.read_text(encoding="utf-8").splitlines()[0].strip()
        except (IndexError, OSError, UnicodeDecodeError):
            return False
        return first_line == "# Verification Gate Report"
    if path.suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            return False
        if not isinstance(data, dict):
            return False
        return (
            data.get("kind") == "verification_gate_report"
            and data.get("result_state") in VERIFICATION_GATE_RESULT_STATES
            and isinstance(data.get("checks"), list)
            and bool(data["checks"])
        )
    return False


def _resolve_verification_gate_report_ref(root: Path, packet_path: Path, ref: object) -> Path | None:
    resolved = _resolve_review_packet_ref(root, packet_path, ref)
    if not resolved or not _is_verification_gate_report_artifact(resolved):
        return None
    return resolved


def _validate_same_run_verification_gate_report_ref(
    anchor_path: Path,
    report_path: Path,
    ref: object,
    label: str,
    errors: list[str],
) -> None:
    run_dir = _agentsflow_run_dir(anchor_path)
    if run_dir and not _is_within_path(report_path, run_dir):
        errors.append(
            f"{anchor_path}: {label} must reference a verification gate report artifact in the same run directory: {ref}"
        )


def _review_packet_refs_match(root: Path, packet_path: Path, left: object, right: object) -> bool:
    left_text = str(left).strip()
    right_text = str(right).strip()
    if left_text == right_text:
        return True
    left_resolved = _resolve_review_packet_ref(root, packet_path, left_text)
    right_resolved = _resolve_review_packet_ref(root, packet_path, right_text)
    return bool(left_resolved and right_resolved and left_resolved == right_resolved)


def _verification_gate_refs_match(
    root: Path,
    packet_path: Path,
    left: object,
    right: object,
    *,
    allow_placeholders: bool = False,
) -> bool:
    left_text = str(left).strip()
    right_text = str(right).strip()
    if allow_placeholders and left_text == right_text and _is_placeholder_ref(left_text):
        return True
    left_resolved = _resolve_verification_gate_report_ref(root, packet_path, left_text)
    right_resolved = _resolve_verification_gate_report_ref(root, packet_path, right_text)
    return bool(left_resolved and right_resolved and left_resolved == right_resolved)


def _provider_models_include_family(provider_models: object, model_family: str) -> bool:
    family = str(model_family).lower()
    if not family or not isinstance(provider_models, list):
        return False
    return any(family in str(model).lower() for model in provider_models)


def _require_concrete_hash(path: Path, label: str, declared: object, actual: str, errors: list[str]) -> None:
    if not is_concrete_sha256(declared):
        errors.append(f"{path}: {label} must be a concrete sha256")
        return
    if declared != actual:
        errors.append(f"{path}: {label} hash mismatch: declared {declared}, computed {actual}")


def _render_expected_review_prompt(packet: dict, role_contract: dict) -> str:
    return render_review_prompt(packet, role_contract)


def _validate_latest_green_gate_ref(
    root: Path,
    packet_path: Path,
    data: dict,
    errors: list[str],
    expected_ref: object | None = None,
    expected_label: str = "verification_gate_report.path",
) -> None:
    freshness = data.get("evidence_freshness")
    if not isinstance(freshness, dict):
        return
    latest_green_gate = freshness.get("latest_green_gate")
    if not latest_green_gate:
        return

    allow_placeholders = _allows_placeholder_verification_refs(packet_path, data)
    if expected_ref:
        if not _verification_gate_refs_match(
            root,
            packet_path,
            latest_green_gate,
            expected_ref,
            allow_placeholders=allow_placeholders,
        ):
            errors.append(
                f"{packet_path}: evidence_freshness.latest_green_gate must match {expected_label}"
            )
        if not (allow_placeholders and _is_placeholder_ref(expected_ref)):
            expected_resolved = _resolve_verification_gate_report_ref(root, packet_path, expected_ref)
            if not expected_resolved:
                errors.append(f"{packet_path}: {expected_label} must reference a verification gate report artifact: {expected_ref}")
            else:
                _validate_same_run_verification_gate_report_ref(
                    packet_path,
                    expected_resolved,
                    expected_ref,
                    expected_label,
                    errors,
                )

    if not (allow_placeholders and _is_placeholder_ref(latest_green_gate)):
        latest_resolved = _resolve_verification_gate_report_ref(root, packet_path, latest_green_gate)
        if not latest_resolved:
            errors.append(
                f"{packet_path}: evidence_freshness.latest_green_gate must reference a verification gate report artifact: {latest_green_gate}"
            )
        else:
            _validate_same_run_verification_gate_report_ref(
                packet_path,
                latest_resolved,
                latest_green_gate,
                "evidence_freshness.latest_green_gate",
                errors,
            )


def _validate_failure_path_matrix_surface_coverage(path: Path, data: dict, errors: list[str]) -> None:
    profile = data.get("risk_surface_profile")
    if not isinstance(profile, dict):
        return
    selected_values = profile.get("selected_risk_surfaces", []) or []
    blank_selected = [
        str(index)
        for index, surface in enumerate(selected_values)
        if isinstance(surface, str) and not surface.strip()
    ]
    if blank_selected:
        errors.append(
            f"{path}: risk_surface_profile.selected_risk_surfaces must not contain blank entries: {', '.join(blank_selected)}"
        )
    selected = {
        surface.strip()
        for surface in selected_values
        if isinstance(surface, str) and surface.strip()
    }

    matrix = data.get("failure_path_matrix")
    rows = matrix.get("rows", []) if isinstance(matrix, dict) else []
    blank_row_surfaces: list[str] = []
    if isinstance(rows, list):
        blank_row_surfaces = [
            str(index)
            for index, row in enumerate(rows)
            if isinstance(row, dict)
            and isinstance(row.get("risk_surface"), str)
            and not row.get("risk_surface", "").strip()
        ]
        if blank_row_surfaces:
            errors.append(
                f"{path}: failure_path_matrix.rows risk_surface must not be blank: {', '.join(blank_row_surfaces)}"
            )
    if not selected:
        return
    if not isinstance(rows, list) or not rows:
        errors.append(
            f"{path}: failure_path_matrix.rows must include coverage rows when selected_risk_surfaces is non-empty"
        )
        return
    covered = {
        row.get("risk_surface", "").strip()
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("risk_surface"), str) and row.get("risk_surface", "").strip()
    }
    missing = sorted(selected - covered)
    if missing:
        errors.append(
            f"{path}: failure_path_matrix.rows must cover selected risk surface(s): {', '.join(missing)}"
        )


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
    provider_policy = data.get("provider_policy", {}) or {}
    assignments = data.get("reviewer_assignments", []) or []
    run_scope_artifact = _is_run_scope_artifact(path, data)
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

    if assignments:
        if not isinstance(assignments, list):
            errors.append(f"{path}: reviewer_assignments must be a list")
            assignments = []
        assignment_reviewers: list[str] = []
        provider_model_families: set[str] = set()
        for idx, assignment in enumerate(assignments):
            if not isinstance(assignment, dict):
                errors.append(f"{path}: reviewer_assignments[{idx}] must be an object")
                continue
            reviewer = str(assignment.get("reviewer", ""))
            provider = str(assignment.get("provider", ""))
            model_family = str(assignment.get("model_family", ""))
            assignment_reviewers.append(reviewer)
            if provider not in SUPPORTED_REVIEW_PROVIDERS:
                errors.append(f"{path}: reviewer_assignments[{idx}].provider is unsupported: {provider}")
            if not model_family:
                errors.append(f"{path}: reviewer_assignments[{idx}].model_family is required")
            provider_model_families.add(f"{provider}/{model_family}")
            for key in ["packet_path", "report_path"]:
                if not assignment.get(key):
                    errors.append(f"{path}: reviewer_assignments[{idx}].{key} is required")
            if provider == "claude-code":
                for key in ["provider_config", "raw_output_path", "invocation_metadata_path"]:
                    if not assignment.get(key):
                        errors.append(f"{path}: claude-code reviewer assignment {reviewer} missing {key}")
        if len(assignment_reviewers) != len(set(assignment_reviewers)):
            errors.append(f"{path}: reviewer_assignments reviewers must be unique")
        if sorted(assignment_reviewers) != sorted(reviewer_ids):
            errors.append(f"{path}: reviewer_assignments must cover reviewer_set exactly")
        if provider_policy.get("allow_external_reviewers") is False:
            external = [
                assignment.get("reviewer")
                for assignment in assignments
                if isinstance(assignment, dict) and assignment.get("provider") != "internal-agent"
            ]
            if external:
                errors.append(f"{path}: provider_policy disallows external reviewers but has external assignments")
        if provider_policy.get("require_model_diversity") is True:
            minimum = int(provider_policy.get("min_distinct_provider_model_families", 2))
            if len(provider_model_families) < minimum:
                errors.append(f"{path}: model diversity requirement is not satisfied by reviewer_assignments")
    elif provider_policy.get("require_model_diversity") is True:
        errors.append(f"{path}: model diversity requires reviewer_assignments")

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
            elif run_scope_artifact:
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
        elif run_scope_artifact:
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
    if run_scope_artifact:
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
    run_path_artifact = _is_agentsflow_run_artifact_path(path)
    if run_path_artifact and data.get("artifact_scope", "run") != "run":
        errors.append(f"{path}: review prompt contract under Docs/agentsflow/runs must declare artifact_scope: run")
    if data.get("artifact_scope", "run") != "run" and not run_path_artifact:
        return errors

    def resolve_existing(
        ref: object,
        label: str,
        *,
        required: bool = True,
        file_required: bool = False,
        verification_gate_report: bool = False,
    ) -> Path | None:
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
        if file_required and not resolved.is_file():
            errors.append(f"{path}: {label} must be a file artifact: {ref}")
            return None
        if verification_gate_report and not _is_verification_gate_report_artifact(resolved):
            errors.append(f"{path}: {label} must reference a verification gate report artifact: {ref}")
            return None
        if verification_gate_report:
            _validate_same_run_verification_gate_report_ref(path, resolved, ref, label, errors)
        return resolved

    inputs = data.get("inputs", {}) or {}
    provider_policy = data.get("provider_policy", {}) or {}
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
        resolve_existing(
            inputs.get("verification_gate_report"),
            "inputs.verification_gate_report",
            file_required=True,
            verification_gate_report=True,
        )
    evidence_report_path: Path | None = None
    if inputs.get("evidence_report"):
        evidence_report_path = resolve_existing(inputs.get("evidence_report"), "inputs.evidence_report", file_required=True)
    artifact_preparation_report_path: Path | None = None
    if inputs.get("artifact_preparation_report"):
        artifact_preparation_report_path = resolve_existing(
            inputs.get("artifact_preparation_report"),
            "inputs.artifact_preparation_report",
            file_required=True,
        )
    review_invocation_set_path: Path | None = None
    has_review_invocation_set_ref = bool(inputs.get("review_invocation_set"))
    if has_review_invocation_set_ref:
        review_invocation_set_path = resolve_existing(
            inputs.get("review_invocation_set"),
            "inputs.review_invocation_set",
            file_required=True,
        )
    if (
        evidence_report_path
        and review_invocation_set_path
        and evidence_report_path.resolve() == review_invocation_set_path.resolve()
    ):
        errors.append(f"{path}: inputs.evidence_report must not match inputs.review_invocation_set")

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
    packet_path_by_reviewer: dict[str, Path] = {}
    packet_paths: list[Path] = []
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
            packet_paths.append(packet_path)
            if resolved_packet_path in seen_packet_paths:
                errors.append(
                    f"{path}: inputs.review_packets duplicate path for reviewers {seen_packet_paths[resolved_packet_path]} and {reviewer}"
                )
            seen_packet_paths[resolved_packet_path] = reviewer
            packet_hash = sha256_file(packet_path)
            packet_hash_by_reviewer[reviewer] = packet_hash
            packet_path_by_reviewer[reviewer] = packet_path
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
    assignments = data.get("reviewer_assignments", []) or []
    external_assignment_present = any(
        isinstance(item, dict) and item.get("provider") == "claude-code"
        for item in assignments
    )
    invocation_set: dict | None = None
    invocation_reviewers: dict[str, dict] = {}
    if assignments:
        if _is_run_scope_artifact(path, data) and not artifact_preparation_report_path:
            errors.append(f"{path}: reviewer_assignments require inputs.artifact_preparation_report")
        invocation_evidence_path = review_invocation_set_path
        if not invocation_evidence_path:
            errors.append(f"{path}: reviewer_assignments require inputs.review_invocation_set evidence")
        else:
            invocation_set_schema = parse_json(root / "schemas" / "review-invocation-set.schema.json")
            invocation_set_data = parse_json(invocation_evidence_path)
            if not isinstance(invocation_set_data, dict):
                errors.append(f"{invocation_evidence_path}: review_invocation_set evidence must be a JSON object")
            else:
                invocation_set = invocation_set_data
                errors.extend(validate_against_schema(invocation_evidence_path, invocation_set, invocation_set_schema))
                if invocation_set.get("status") != "completed":
                    errors.append(f"{invocation_evidence_path}: review_invocation_set status must be completed")
                if external_assignment_present and invocation_set.get("runner_scheduling") != "external-first-async":
                    errors.append(
                        f"{invocation_evidence_path}: external reviewer assignments require "
                        "review_invocation_set.runner_scheduling external-first-async"
                    )
                invocation_reviewers = {
                    str(item.get("reviewer")): item
                    for item in invocation_set.get("reviewers", []) or []
                    if isinstance(item, dict) and item.get("reviewer")
                }
                if sorted(invocation_reviewers) != sorted(reviewers):
                    errors.append(
                        f"{invocation_evidence_path}: review_invocation_set reviewers must cover reviewer_set exactly"
                    )
    reviewer_report_schema = parse_json(root / "schemas" / "reviewer-report.schema.json")
    reviewer_invocation_schema = parse_json(root / "schemas" / "reviewer-invocation.schema.json")
    output_schema_hash = sha256_file(output_schema_path) if output_schema_path else ""
    review_prompt_contract_hash = sha256_file(path)
    rubric_hash = sha256_text(json.dumps(data.get("prompt_policy", {}) or {}, sort_keys=True))

    def resolve_assignment_output(ref: object, label: str) -> Path | None:
        return resolve_existing(ref, label, file_required=True)

    def resolve_invocation_set_ref(ref: object, label: str) -> Path | None:
        if not ref:
            errors.append(f"{path}: {label} is required")
            return None
        ref_path = Path(str(ref))
        if ref_path.is_absolute():
            resolved = ref_path
            if not _is_within_path(resolved, root):
                errors.append(f"{path}: {label} must be inside repository root: {ref}")
                return None
        elif ".." in ref_path.parts:
            errors.append(f"{path}: {label} must be relative and non-escaping: {ref}")
            return None
        else:
            resolved = root / ref_path
        if not resolved.exists():
            errors.append(f"{path}: {label} does not exist: {ref}")
            return None
        if not resolved.is_file():
            errors.append(f"{path}: {label} must be a file artifact: {ref}")
            return None
        return resolved

    def require_invocation_hash(
        invocation_path: Path,
        invocation_data: dict,
        key: str,
        expected: str,
        reviewer: str,
    ) -> None:
        declared = invocation_data.get(key)
        if not is_concrete_sha256(declared):
            errors.append(f"{invocation_path}: {key} is required to bind completed external evidence for {reviewer}")
            return
        if declared != expected:
            errors.append(
                f"{invocation_path}: {key} must match current review artifact for {reviewer}: "
                f"declared {declared}, computed {expected}"
            )

    if assignments and artifact_preparation_report_path:
        if invocation_set:
            if not invocation_set.get("artifact_preparation_report"):
                errors.append(
                    f"{artifact_preparation_report_path}: review_invocation_set must declare artifact_preparation_report"
                )
            else:
                invocation_preparation_ref = resolve_invocation_set_ref(
                    invocation_set.get("artifact_preparation_report"),
                    "review_invocation_set.artifact_preparation_report",
                )
                if invocation_preparation_ref and invocation_preparation_ref.resolve() != artifact_preparation_report_path.resolve():
                    errors.append(
                        f"{artifact_preparation_report_path}: review_invocation_set artifact_preparation_report must match inputs.artifact_preparation_report"
                    )
            _require_concrete_hash(
                artifact_preparation_report_path,
                "review_invocation_set.artifact_preparation_report_hash",
                invocation_set.get("artifact_preparation_report_hash"),
                sha256_file(artifact_preparation_report_path),
                errors,
            )
        preparation_schema = parse_json(root / "schemas" / "review-artifact-preparation.schema.json")
        preparation_data = parse_json(artifact_preparation_report_path)
        if not isinstance(preparation_data, dict):
            errors.append(f"{artifact_preparation_report_path}: review_artifact_preparation evidence must be a JSON object")
        else:
            errors.extend(validate_against_schema(artifact_preparation_report_path, preparation_data, preparation_schema))
            if preparation_data.get("status") != "completed":
                errors.append(f"{artifact_preparation_report_path}: review_artifact_preparation status must be completed")
            prep_contract = preparation_data.get("review_prompt_contract", {}) or {}
            prep_contract_path_ref = resolve_invocation_set_ref(
                prep_contract.get("path"),
                f"{artifact_preparation_report_path}.review_prompt_contract.path",
            )
            if prep_contract_path_ref and prep_contract_path_ref.resolve() != path.resolve():
                errors.append(f"{artifact_preparation_report_path}: review_prompt_contract.path must match current contract")
            _require_concrete_hash(
                artifact_preparation_report_path,
                "review_prompt_contract.hash",
                prep_contract.get("hash"),
                review_prompt_contract_hash,
                errors,
            )
            prep_assignments = {
                str(item.get("reviewer")): item
                for item in preparation_data.get("reviewer_assignments", []) or []
                if isinstance(item, dict) and item.get("reviewer")
            }
            if sorted(prep_assignments) != sorted(reviewers):
                errors.append(
                    f"{artifact_preparation_report_path}: reviewer_assignments must cover reviewer_set exactly"
                )
            generated = preparation_data.get("generated_artifacts", {}) or {}
            prep_invocation = generated.get("review_invocation_set", {}) or {}
            if review_invocation_set_path:
                prep_invocation_path = resolve_invocation_set_ref(
                    prep_invocation.get("path"),
                    f"{artifact_preparation_report_path}.generated_artifacts.review_invocation_set.path",
                )
                if prep_invocation_path and prep_invocation_path.resolve() != review_invocation_set_path.resolve():
                    errors.append(
                        f"{artifact_preparation_report_path}: generated_artifacts.review_invocation_set.path must match inputs.review_invocation_set"
                    )
            prep_packets = {
                str(item.get("reviewer")): item
                for item in generated.get("review_packets", []) or []
                if isinstance(item, dict) and item.get("reviewer")
            }
            if sorted(prep_packets) != sorted(reviewers):
                errors.append(f"{artifact_preparation_report_path}: generated review_packets must cover reviewer_set exactly")
            for reviewer, packet_entry in prep_packets.items():
                packet_ref = resolve_invocation_set_ref(
                    packet_entry.get("path"),
                    f"{artifact_preparation_report_path}.generated_artifacts.review_packets[{reviewer}].path",
                )
                current_packet = packet_path_by_reviewer.get(reviewer)
                if packet_ref and current_packet and packet_ref.resolve() != current_packet.resolve():
                    errors.append(
                        f"{artifact_preparation_report_path}: review_artifact_preparation review packet path must match contract for {reviewer}"
                    )
                if current_packet:
                    _require_concrete_hash(
                        artifact_preparation_report_path,
                        f"review_artifact_preparation review packet hash for {reviewer}",
                        packet_entry.get("hash"),
                        sha256_file(current_packet),
                        errors,
                    )
            prep_prompts = {
                str(item.get("reviewer")): item
                for item in generated.get("rendered_prompts", []) or []
                if isinstance(item, dict) and item.get("reviewer")
            }
            if sorted(prep_prompts) != sorted(reviewers):
                errors.append(f"{artifact_preparation_report_path}: generated rendered_prompts must cover reviewer_set exactly")
            for reviewer, prompt_entry in prep_prompts.items():
                current_prompt = rendered_by_reviewer.get(reviewer) or {}
                prompt_ref = resolve_invocation_set_ref(
                    prompt_entry.get("path"),
                    f"{artifact_preparation_report_path}.generated_artifacts.rendered_prompts[{reviewer}].path",
                )
                current_prompt_path = root / str(current_prompt.get("prompt_path", ""))
                if prompt_ref and current_prompt.get("prompt_path") and prompt_ref.resolve() != current_prompt_path.resolve():
                    errors.append(
                        f"{artifact_preparation_report_path}: review_artifact_preparation rendered prompt path must match contract for {reviewer}"
                    )
                if current_prompt.get("prompt_path") and current_prompt_path.exists():
                    _require_concrete_hash(
                        artifact_preparation_report_path,
                        f"review_artifact_preparation rendered prompt hash for {reviewer}",
                        prompt_entry.get("hash"),
                        sha256_file(current_prompt_path),
                        errors,
                    )
            for idx, artifact in enumerate(preparation_data.get("input_artifacts", []) or []):
                if not isinstance(artifact, dict):
                    continue
                artifact_path = resolve_invocation_set_ref(
                    artifact.get("path"),
                    f"{artifact_preparation_report_path}.input_artifacts[{idx}].path",
                )
                if artifact_path:
                    _require_concrete_hash(
                        artifact_preparation_report_path,
                        f"input_artifacts[{idx}].hash",
                        artifact.get("hash"),
                        sha256_file(artifact_path),
                        errors,
                    )

    completed_provider_model_families: set[str] = set()
    assignment_report_paths: dict[Path, str] = {}
    invocation_report_paths: dict[Path, str] = {}
    for idx, assignment in enumerate(assignments):
        if not isinstance(assignment, dict):
            continue
        reviewer = str(assignment.get("reviewer", ""))
        provider = str(assignment.get("provider", ""))
        model_family = str(assignment.get("model_family", ""))
        evidence_model_family: str | None = None
        assignment_packet = assignment.get("packet_path")
        packet_path = packet_path_by_reviewer.get(reviewer)
        if assignment_packet and packet_path:
            ref = Path(str(assignment_packet))
            if ref.is_absolute() or ".." in ref.parts:
                errors.append(f"{path}: reviewer_assignments[{idx}].packet_path must be relative and non-escaping")
            elif (root / ref).resolve() != packet_path.resolve():
                errors.append(
                    f"{path}: reviewer_assignments[{idx}].packet_path must match inputs.review_packets for {reviewer}"
                )
        if assignment.get("provider_config"):
            provider_config = Path(str(assignment.get("provider_config")))
            if provider_config.is_absolute() or ".." in provider_config.parts:
                errors.append(f"{path}: reviewer_assignments[{idx}].provider_config must be relative and non-escaping")
            elif not (root / provider_config).exists():
                errors.append(f"{path}: reviewer_assignments[{idx}].provider_config does not exist: {provider_config}")
        report_path = resolve_assignment_output(
            assignment.get("report_path"), f"reviewer_assignments[{idx}].report_path"
        )
        if assignment.get("report_path") and Path(str(assignment.get("report_path"))).suffix != ".json":
            errors.append(f"{path}: reviewer_assignments[{idx}].report_path must be a JSON reviewer report")
            report_path = None
        if report_path:
            resolved_report_path = report_path.resolve()
            if resolved_report_path in assignment_report_paths:
                errors.append(
                    f"{path}: reviewer_assignments report_path must be unique; "
                    f"{reviewer} reuses report for {assignment_report_paths[resolved_report_path]}"
                )
            else:
                assignment_report_paths[resolved_report_path] = reviewer
            report_data = parse_json(report_path)
            errors.extend(validate_against_schema(report_path, report_data, reviewer_report_schema))
            if isinstance(report_data, dict):
                report_reviewer = report_data.get("reviewer", {}) or {}
                if isinstance(report_reviewer, dict):
                    report_reviewer_id = str(report_reviewer.get("id") or "")
                    if reviewer not in report_reviewer_id:
                        errors.append(f"{report_path}: reviewer.id must include assigned reviewer {reviewer}")
                    report_model = str(report_reviewer.get("model") or "")
                    if provider and str(report_reviewer.get("provider")) != provider:
                        errors.append(f"{report_path}: reviewer.provider must match assignment provider for {reviewer}")
                    if str(report_reviewer.get("role")) != str((reviewers.get(reviewer) or {}).get("role_id")):
                        errors.append(f"{report_path}: reviewer.role must match reviewer_set role for {reviewer}")
                    if provider == "internal-agent" and provider_policy.get("require_model_diversity") is True:
                        if not report_model:
                            errors.append(
                                f"{report_path}: reviewer.model is required to prove model diversity for {reviewer}"
                            )
                        elif report_model != model_family:
                            errors.append(
                                f"{report_path}: reviewer.model must match assignment model_family for {reviewer}"
                            )
                        else:
                            evidence_model_family = report_model
        if provider == "claude-code":
            raw_output_path = resolve_assignment_output(
                assignment.get("raw_output_path"), f"reviewer_assignments[{idx}].raw_output_path"
            )
            if raw_output_path:
                parse_json(raw_output_path)
            invocation_metadata_path = resolve_assignment_output(
                assignment.get("invocation_metadata_path"),
                f"reviewer_assignments[{idx}].invocation_metadata_path",
            )
            if invocation_metadata_path:
                invocation_data = parse_json(invocation_metadata_path)
                errors.extend(validate_against_schema(invocation_metadata_path, invocation_data, reviewer_invocation_schema))
                if isinstance(invocation_data, dict):
                    if str(invocation_data.get("execution_mode") or "") != "real":
                        errors.append(
                            f"{invocation_metadata_path}: execution_mode must be real for completed external evidence"
                        )
                    if invocation_data.get("exit_code") != 0:
                        errors.append(f"{invocation_metadata_path}: exit_code must be 0 for completed external evidence")
                    if packet_path:
                        require_invocation_hash(
                            invocation_metadata_path,
                            invocation_data,
                            "input_hash",
                            packet_hash_by_reviewer.get(reviewer, ""),
                            reviewer,
                        )
                    rendered_prompt = rendered_by_reviewer.get(reviewer) or {}
                    prompt_hash = str(rendered_prompt.get("prompt_hash") or "")
                    if prompt_hash:
                        require_invocation_hash(
                            invocation_metadata_path,
                            invocation_data,
                            "prompt_hash",
                            prompt_hash,
                            reviewer,
                        )
                    require_invocation_hash(
                        invocation_metadata_path,
                        invocation_data,
                        "review_prompt_contract_hash",
                        review_prompt_contract_hash,
                        reviewer,
                    )
                    role_ref = (reviewers.get(reviewer) or {}).get("role_contract")
                    role_path = resolve_existing(role_ref, f"reviewer_set.{reviewer}.role_contract")
                    if role_path:
                        require_invocation_hash(
                            invocation_metadata_path,
                            invocation_data,
                            "role_contract_hash",
                            sha256_file(role_path),
                            reviewer,
                        )
                    if output_schema_hash:
                        require_invocation_hash(
                            invocation_metadata_path,
                            invocation_data,
                            "schema_hash",
                            output_schema_hash,
                            reviewer,
                        )
                    require_invocation_hash(
                        invocation_metadata_path,
                        invocation_data,
                        "rubric_hash",
                        rubric_hash,
                        reviewer,
                    )
                    raw_output_path_ref = resolve_invocation_set_ref(
                        invocation_data.get("raw_output_path"), f"{invocation_metadata_path}.raw_output_path"
                    )
                    if raw_output_path and raw_output_path_ref and raw_output_path_ref.resolve() != raw_output_path.resolve():
                        errors.append(f"{invocation_metadata_path}: raw_output_path must match assignment for {reviewer}")
                    if raw_output_path:
                        require_invocation_hash(
                            invocation_metadata_path,
                            invocation_data,
                            "raw_output_hash",
                            sha256_file(raw_output_path),
                            reviewer,
                        )
                    normalized_output_path_ref = resolve_invocation_set_ref(
                        invocation_data.get("normalized_output_path"), f"{invocation_metadata_path}.normalized_output_path"
                    )
                    if report_path and normalized_output_path_ref and normalized_output_path_ref.resolve() != report_path.resolve():
                        errors.append(f"{invocation_metadata_path}: normalized_output_path must match assignment for {reviewer}")
                    if report_path:
                        require_invocation_hash(
                            invocation_metadata_path,
                            invocation_data,
                            "normalized_output_hash",
                            sha256_file(report_path),
                            reviewer,
                        )
                    if provider_policy.get("require_model_diversity") is True:
                        requested_model = str(invocation_data.get("requested_model") or "")
                        if not requested_model:
                            errors.append(
                                f"{invocation_metadata_path}: requested_model is required to prove model diversity for {reviewer}"
                            )
                        elif requested_model != model_family:
                            errors.append(
                                f"{invocation_metadata_path}: requested_model must match assignment model_family for {reviewer}"
                            )
                        elif not _provider_models_include_family(invocation_data.get("provider_models_used"), model_family):
                            errors.append(
                                f"{invocation_metadata_path}: provider_models_used must include assignment model_family for {reviewer}"
                            )
                        else:
                            evidence_model_family = requested_model
        invocation_entry = invocation_reviewers.get(reviewer)
        if invocation_entry:
            for key, expected in [("provider", provider), ("model_family", model_family)]:
                if str(invocation_entry.get(key)) != expected:
                    errors.append(f"{path}: review_invocation_set reviewer {reviewer} {key} must match assignment")
            invocation_report_path_ref = resolve_invocation_set_ref(
                invocation_entry.get("report_path"), f"review_invocation_set.reviewers[{reviewer}].report_path"
            )
            if invocation_report_path_ref:
                resolved_invocation_report = invocation_report_path_ref.resolve()
                if resolved_invocation_report in invocation_report_paths:
                    errors.append(
                        f"{path}: review_invocation_set report_path must be unique; "
                        f"{reviewer} reuses report for {invocation_report_paths[resolved_invocation_report]}"
                    )
                else:
                    invocation_report_paths[resolved_invocation_report] = reviewer
            if report_path and invocation_report_path_ref and invocation_report_path_ref.resolve() != report_path.resolve():
                errors.append(f"{path}: review_invocation_set reviewer {reviewer} report_path must match assignment")
            if provider == "claude-code":
                for key in ["raw_output_path", "invocation_metadata_path"]:
                    resolve_invocation_set_ref(
                        invocation_entry.get(key), f"review_invocation_set.reviewers[{reviewer}].{key}"
                    )
                if str(invocation_entry.get("execution_mode") or "") != "real":
                    errors.append(
                        f"{path}: review_invocation_set reviewer {reviewer} execution_mode must be real for completed external evidence"
                    )
            if provider_policy.get("require_model_diversity") is True and evidence_model_family:
                completed_provider_model_families.add(f"{provider}/{evidence_model_family}")
            elif provider_policy.get("require_model_diversity") is not True:
                completed_provider_model_families.add(f"{provider}/{model_family}")

    if invocation_set and provider_policy.get("require_model_diversity") is True:
        minimum = int(provider_policy.get("min_distinct_provider_model_families", 2))
        invocation_families = set(str(item) for item in invocation_set.get("provider_model_families", []) or [])
        if len(completed_provider_model_families) < minimum or not completed_provider_model_families.issubset(invocation_families):
            errors.append(
                f"{path}: review_invocation_set does not prove the required provider/model diversity"
            )

    identity = data.get("identity", {}) or {}
    if identity.get("review_profile") == "homogeneous-dual" and packet_paths:
        for packet_path in packet_paths:
            if not (packet_path.parent / "shared-content.json").exists():
                errors.append(f"{path}: homogeneous-dual run review packet missing sibling shared-content.json: {packet_path}")
        shared_content_paths = {
            packet_path.parent / "shared-content.json"
            for packet_path in packet_paths
            if (packet_path.parent / "shared-content.json").exists()
        }
        if len(shared_content_paths) != 1:
            errors.append(
                f"{path}: homogeneous-dual run review packets must have exactly one sibling shared-content.json"
            )
        else:
            shared_content_path = next(iter(shared_content_paths))
            shared_content_hash = sha256_file(shared_content_path)
            shared_content = parse_json(shared_content_path)
            if not isinstance(shared_content, dict):
                errors.append(f"{shared_content_path}: shared packet content must be a JSON object")
                shared_content = {}
            excluded_envelope_fields = set(str(item) for item in (shared_content.get("excluded_envelope_fields", []) or []))
            allowed_excluded_envelope_fields = {"reviewer_instance_id", "provider"}
            unexpected_excluded_fields = sorted(excluded_envelope_fields - allowed_excluded_envelope_fields)
            if unexpected_excluded_fields:
                errors.append(
                    f"{shared_content_path}: excluded_envelope_fields may only contain envelope fields: "
                    f"{', '.join(sorted(allowed_excluded_envelope_fields))}; unexpected: {', '.join(unexpected_excluded_fields)}"
                )

            def shared_packet_payload(packet_data: dict, *, sidecar: bool = False) -> dict:
                return {
                    key: value
                    for key, value in packet_data.items()
                    if key not in excluded_envelope_fields
                    and not (sidecar and key == "excluded_envelope_fields")
                }

            expected_shared_packet = shared_packet_payload(shared_content, sidecar=True)
            for idx, packet in enumerate(inputs.get("review_packets", []) or []):
                if isinstance(packet, dict):
                    compare_hash(
                        path,
                        f"inputs.review_packets[{idx}].shared_packet_content_hash",
                        packet.get("shared_packet_content_hash"),
                        shared_content_hash,
                        errors,
                    )
                    packet_path = root / str(packet.get("path", ""))
                    packet_data = parse_json(packet_path) if packet_path.exists() else None
                    if isinstance(packet_data, dict):
                        if "excluded_envelope_fields" in packet_data:
                            errors.append(
                                f"{path}: inputs.review_packets[{idx}] must not contain reserved shared-content metadata field excluded_envelope_fields"
                            )
                        if shared_packet_payload(packet_data) != expected_shared_packet:
                            errors.append(
                                f"{path}: inputs.review_packets[{idx}] content must match shared-content.json except excluded envelope fields"
                            )
            for idx, prompt in enumerate(data.get("rendered_prompts", []) or []):
                if isinstance(prompt, dict):
                    compare_hash(
                        path,
                        f"rendered_prompts[{idx}].shared_packet_content_hash",
                        prompt.get("shared_packet_content_hash"),
                        shared_content_hash,
                        errors,
                    )

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
        packet_path = packet_path_by_reviewer.get(reviewer)
        if prompt_path and role_path and packet_path:
            packet_data = parse_json(packet_path)
            role_data = parse_yaml(role_path)
            if isinstance(packet_data, dict) and isinstance(role_data, dict):
                expected_prompt = _render_expected_review_prompt(packet_data, role_data)
                actual_prompt = prompt_path.read_text(encoding="utf-8")
                if actual_prompt != expected_prompt:
                    errors.append(
                        f"{path}: rendered_prompts[{idx}].prompt_path content must match current packet and role contract"
                    )
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
    _validate_failure_path_matrix_surface_coverage(path, data, errors)
    if not check_references:
        return errors

    verification_gate_report = data.get("verification_gate_report")
    verification_gate_ref = (
        verification_gate_report.get("path")
        if isinstance(verification_gate_report, dict)
        else None
    )
    if not verification_gate_ref:
        errors.append(f"{path}: verification_gate_report.path is required")
    _validate_latest_green_gate_ref(root, path, data, errors, verification_gate_ref)

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
                contract_verification_gate_ref = ((contract.get("inputs") or {}).get("verification_gate_report"))
                if not contract_verification_gate_ref:
                    errors.append(f"{path}: review_prompt_contract inputs.verification_gate_report is required")
                _validate_latest_green_gate_ref(
                    root,
                    path,
                    data,
                    errors,
                    contract_verification_gate_ref,
                    "review_prompt_contract inputs.verification_gate_report",
                )
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


def validate_review_artifact_preparation_artifact(root: Path, path: Path) -> list[str]:
    schema = parse_json(root / "schemas" / "review-artifact-preparation.schema.json")
    data = parse_json(path)
    if not isinstance(data, dict):
        return [f"{path}: review artifact preparation must be a JSON object"]
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
    selected_surfaces = review.get("selected_risk_surfaces")
    if selected_surfaces is not None:
        if not isinstance(selected_surfaces, list):
            errors.append(f"{path}: {context}.selected_risk_surfaces must be a list")
        else:
            blank_surfaces = [
                str(index)
                for index, surface in enumerate(selected_surfaces)
                if isinstance(surface, str) and not surface.strip()
            ]
            if blank_surfaces:
                errors.append(
                    f"{path}: {context}.selected_risk_surfaces must not contain blank entries: {', '.join(blank_surfaces)}"
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


def validate_v02_review_control_phase_policy(path: Path, data: dict) -> list[str]:
    if data.get("name") not in V0_2_REVIEW_CONTROL_WORKFLOWS:
        return []
    has_review_phase = any(
        isinstance(phase, dict) and phase.get("kind") == "review"
        for phase in data.get("phases", []) or []
    )
    if has_review_phase and not isinstance(data.get("review"), dict):
        return [f"{path}: v0.2 review-control workflow with review phase must declare top-level review policy"]
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
    if data.get("name") not in V0_2_REVIEW_CONTROL_WORKFLOWS:
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
        errors.append(f"{path}: v0.2 review-control workflow with post-gate review or fusion must include finding_validation phase")
        return errors
    if fusion_phases and not review_phases:
        errors.append(f"{path}: v0.2 review-control workflow with fusion phase must include review phase")
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


def validate_v02_review_control_materiality_policy(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("name") not in V0_2_REVIEW_CONTROL_WORKFLOWS:
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
    else:
        material_if_changes = set(str(item) for item in materiality.get("material_if_changes", []) or [])
        required_material_triggers = {
            "selected_risk_surfaces_or_failure_path_matrix",
            "review_packet_content",
        }
        missing_triggers = sorted(required_material_triggers - material_if_changes)
        if missing_triggers:
            errors.append(
                f"{path}: materiality_classification.material_if_changes missing: {', '.join(missing_triggers)}"
            )
    if not materiality.get("non_material_if_only"):
        errors.append(f"{path}: materiality_classification.non_material_if_only is required")
    controls = data.get("review_control_rules", {}) or {}
    if controls.get("post_fix_materiality_classification_required") is not True:
        errors.append(f"{path}: review_control_rules.post_fix_materiality_classification_required must be true")
    return errors


def validate_phase_skills_declared(
    path: Path,
    data: dict,
    skill_manifests: dict[str, dict],
) -> list[str]:
    workflow_name = str(data.get("name") or "")
    uses_skills = set(str(item) for item in ((data.get("uses") or {}).get("skills", []) or []))
    missing: set[str] = set()
    incompatible: set[str] = set()
    unknown: set[str] = set()
    for phase in data.get("phases", []) or []:
        if not isinstance(phase, dict):
            continue
        for skill in phase.get("skills", []) or []:
            skill_name = str(skill)
            if skill_name not in skill_manifests:
                unknown.add(skill_name)
                continue
            if skill_name not in uses_skills:
                missing.add(skill_name)
            compatible = skill_manifests.get(skill_name, {}).get("compatible_workflows") or []
            if compatible and workflow_name not in compatible:
                incompatible.add(skill_name)
    errors: list[str] = []
    if missing:
        errors.append(f"{path}: phase skills missing from uses.skills: {', '.join(sorted(missing))}")
    if unknown:
        errors.append(f"{path}: phase skills missing skill manifest: {', '.join(sorted(unknown))}")
    if incompatible:
        errors.append(
            f"{path}: phase skills compatible_workflows missing {workflow_name}: {', '.join(sorted(incompatible))}"
        )
    return errors
