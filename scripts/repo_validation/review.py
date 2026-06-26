from __future__ import annotations

import json
from pathlib import Path

from .collect import collect_yaml_manifest_names
from .common import (
    is_concrete_sha256,
    parse_json,
    parse_yaml,
    sha256_file,
    validate_against_schema,
)


ROLE_CONTRACT_PREFIXES = ('profiles/reviewer_roles/', '.agentsflow/profiles/reviewer_roles/')
SUPPORTED_REVIEW_PROVIDERS = {"internal-agent", "claude-code"}
V0_2_SUPPORTED_TARGET_WORKFLOWS = {
    'big-feature-contract-first',
}
V0_2_UTILITY_WORKFLOWS = {
    'review-only-fusion',
    'pr-merge-readiness',
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
GREEN_VERIFICATION_GATE_RESULT_STATES = {"pass", "pass_with_notes"}
RUN_ARTIFACT_MARKERS = (
    ("Docs", "agentsflow", "runs"),
    ("run-artifacts", "agentsflow", "runs"),
)


def _is_agentsflow_run_artifact_path(path: Path) -> bool:
    parts = path.parts
    return any(
        parts[index : index + 3] in RUN_ARTIFACT_MARKERS
        for index in range(len(parts) - 2)
    )


def _agentsflow_run_dir(path: Path) -> Path | None:
    parts = path.resolve().parts
    for index in range(len(parts) - 3):
        if parts[index : index + 3] in RUN_ARTIFACT_MARKERS:
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


def _is_verification_gate_report_artifact(
    path: Path,
    *,
    require_green: bool = False,
) -> bool:
    normalized_name = path.name.replace("_", "-")
    if "verification-gate-report" not in normalized_name:
        return False
    if path.suffix == ".md":
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            first_line = lines[0].strip()
        except (IndexError, OSError, UnicodeDecodeError):
            return False
        if require_green:
            status = _markdown_verification_gate_status(lines)
            return first_line == "# Verification Gate Report" and status in GREEN_VERIFICATION_GATE_RESULT_STATES
        return first_line == "# Verification Gate Report"
    if path.suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            return False
        if not isinstance(data, dict):
            return False
        result_state = data.get("result_state")
        if require_green and result_state not in GREEN_VERIFICATION_GATE_RESULT_STATES:
            return False
        return (
            data.get("kind") == "verification_gate_report"
            and result_state in VERIFICATION_GATE_RESULT_STATES
            and isinstance(data.get("checks"), list)
            and bool(data["checks"])
        )
    return False


def _markdown_verification_gate_status(lines: list[str]) -> str | None:
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("status:"):
            return stripped.split(":", 1)[1].strip().replace("-", "_")
    return None


def _resolve_verification_gate_report_ref(
    root: Path,
    packet_path: Path,
    ref: object,
    *,
    require_green: bool = False,
) -> Path | None:
    resolved = _resolve_review_packet_ref(root, packet_path, ref)
    if not resolved or not _is_verification_gate_report_artifact(resolved, require_green=require_green):
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


def _verification_gate_refs_match(
    root: Path,
    packet_path: Path,
    left: object,
    right: object,
    *,
    allow_placeholders: bool = False,
    require_green: bool = False,
) -> bool:
    left_text = str(left).strip()
    right_text = str(right).strip()
    if allow_placeholders and left_text == right_text and _is_placeholder_ref(left_text):
        return True
    left_resolved = _resolve_verification_gate_report_ref(
        root,
        packet_path,
        left_text,
        require_green=require_green,
    )
    right_resolved = _resolve_verification_gate_report_ref(
        root,
        packet_path,
        right_text,
        require_green=require_green,
    )
    return bool(left_resolved and right_resolved and left_resolved == right_resolved)


def _validate_reviewer_report_context(
    root: Path,
    path: Path,
    report: dict,
    packet: dict,
    packet_path: Path,
    reviewer: str,
    errors: list[str],
) -> None:
    context = report.get("review_context")
    if not isinstance(context, dict):
        errors.append(f"{path}: review_context is required for {reviewer}")
        return
    expected_run_id = str(packet.get("run_id") or "")
    if expected_run_id and context.get("run_id") != expected_run_id:
        errors.append(f"{path}: review_context.run_id must match packet for {reviewer}")
    expected_material_change = str(packet.get("material_change_id") or "")
    if expected_material_change and context.get("material_change_id") != expected_material_change:
        errors.append(f"{path}: review_context.material_change_id must match packet for {reviewer}")
    try:
        default_packet_ref = packet_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        default_packet_ref = str(packet_path)
    expected_packet_ref = str(packet.get("review_packet_path") or default_packet_ref)
    if context.get("review_packet_path") != expected_packet_ref:
        errors.append(f"{path}: review_context.review_packet_path must match assignment for {reviewer}")
    if context.get("reviewer_instance_id") != reviewer:
        errors.append(f"{path}: review_context.reviewer_instance_id must match assignment for {reviewer}")


def _require_concrete_hash(path: Path, label: str, declared: object, actual: str, errors: list[str]) -> None:
    if not is_concrete_sha256(declared):
        errors.append(f"{path}: {label} must be a concrete sha256")
        return
    if declared != actual:
        errors.append(f"{path}: {label} hash mismatch: declared {declared}, computed {actual}")


def _validate_reviewer_report_normalization(root: Path, path: Path, data: dict, errors: list[str]) -> None:
    normalization = data.get("normalization")
    if not isinstance(normalization, dict):
        return
    if "output_hash" in normalization:
        errors.append(f"{path}: normalization.output_hash must be recorded outside reviewer-report JSON")
    source_ref = normalization.get("source_path")
    if not source_ref:
        return
    source_path = Path(str(source_ref))
    if source_path.is_absolute():
        resolved = source_path
        if not _is_within_path(resolved, root):
            errors.append(f"{path}: normalization.source_path must be inside repository root: {source_ref}")
            return
    elif ".." in source_path.parts:
        errors.append(f"{path}: normalization.source_path must be relative and non-escaping: {source_ref}")
        return
    else:
        resolved = root / source_path
    if not resolved.exists():
        errors.append(f"{path}: normalization.source_path does not exist: {source_ref}")
        return
    if not resolved.is_file():
        errors.append(f"{path}: normalization.source_path must be a file artifact: {source_ref}")
        return
    _require_concrete_hash(
        path,
        "normalization.source_hash",
        normalization.get("source_hash"),
        sha256_file(resolved),
        errors,
    )


def _validate_latest_green_gate_ref(
    root: Path,
    packet_path: Path,
    data: dict,
    errors: list[str],
    expected_ref: object | None = None,
    expected_label: str = "verification_gate_report.path",
    require_green: bool = False,
) -> None:
    allow_placeholders = _allows_placeholder_verification_refs(packet_path, data)
    if expected_ref and not (allow_placeholders and _is_placeholder_ref(expected_ref)):
        expected_resolved = _resolve_verification_gate_report_ref(
            root,
            packet_path,
            expected_ref,
            require_green=require_green,
        )
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

    freshness = data.get("evidence_freshness")
    if not isinstance(freshness, dict):
        return
    latest_green_gate = freshness.get("latest_green_gate")
    if not latest_green_gate:
        return

    if expected_ref:
        if not _verification_gate_refs_match(
            root,
            packet_path,
            latest_green_gate,
            expected_ref,
            allow_placeholders=allow_placeholders,
            require_green=require_green,
        ):
            errors.append(
                f"{packet_path}: evidence_freshness.latest_green_gate must match {expected_label}"
            )

    if not (allow_placeholders and _is_placeholder_ref(latest_green_gate)):
        latest_resolved = _resolve_verification_gate_report_ref(
            root,
            packet_path,
            latest_green_gate,
            require_green=require_green,
        )
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


def validate_review_packet_artifact(
    root: Path,
    path: Path,
    check_references: bool,
    *,
    require_green_verification_gate: bool = False,
) -> list[str]:
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
    if composition == "heterogeneous" and not data.get("focus_zone"):
        errors.append(f"{path}: heterogeneous review packet must include focus_zone")
    if (
        composition == "homogeneous-plus-focused"
        and data.get("reviewer_role") != "generalist"
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
    _validate_latest_green_gate_ref(
        root,
        path,
        data,
        errors,
        verification_gate_ref,
        require_green=require_green_verification_gate,
    )

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
    output_schema = data.get("output_schema")
    if output_schema and not (root / str(output_schema)).exists():
        errors.append(f"{path}: output_schema does not exist: {output_schema}")
    return errors


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
    errors: list[str] = []
    schema = parse_json(root / "schemas" / "reviewer-report.schema.json")
    data = parse_json(path)
    if not isinstance(data, dict):
        return [f"{path}: reviewer report must be a JSON object"]
    errors.extend(validate_against_schema(path, data, schema))
    _validate_reviewer_report_normalization(root, path, data, errors)
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
        for key in [
            "baseline_same_prompt",
            "baseline_same_packet",
            "baseline_same_rubric",
            "focused_reviewers_require_explicit_focus_zone",
            "focus_zones_may_overlap",
            "all_reviewers_must_report_p0_p1_outside_focus",
        ]:
            if prompt_policy.get(key) is not True:
                errors.append(f"{path}: {context}.prompt_policy.{key} must be true")
    elif composition == "heterogeneous":
        if isinstance(reviewers, list) and len(reviewers) < 3:
            errors.append(f"{path}: heterogeneous review must use at least three reviewers")
        if isinstance(reviewers, list) and len(reviewers) > 8:
            errors.append(f"{path}: heterogeneous review must use no more than eight reviewers")
        for key in ["focus_prompts_required", "focus_zones_may_overlap", "all_reviewers_must_report_p0_p1_outside_focus"]:
            if prompt_policy.get(key) is not True:
                errors.append(f"{path}: {context}.prompt_policy.{key} must be true")

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
