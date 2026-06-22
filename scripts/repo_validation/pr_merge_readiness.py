from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .common import is_concrete_sha256, parse_json, parse_yaml, sha256_file, validate_against_schema
from .external_reviewers import validate_external_review_provider


BLOCKING_FINDING_SEVERITIES = {"P0", "P1"}
SUPPORTED_COLLISION_CONTROL_CONCLUSION = "orchestrator-disposition-supported"
SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "NOTE": 4}
REQUIRED_CLAUDE_FORBIDDEN_ENV = {
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
}
DEFAULT_PR_MERGE_REQUIRED_REVIEWS = [
    ("verification-codex", "verification-evidence", "internal-agent", False, "verification"),
    ("verification-claude", "verification-evidence", "claude-code", True, "verification"),
    ("architecture-codex", "architecture-process", "internal-agent", False, "architecture"),
    ("architecture-claude", "architecture-process", "claude-code", True, "architecture"),
    ("adversarial-codex", "adversarial-authority", "internal-agent", False, "adversarial"),
    ("adversarial-claude", "adversarial-authority", "claude-code", True, "adversarial"),
]


def _schema(root: Path) -> dict:
    schema = parse_json(root / "schemas" / "pr-merge-readiness-report.schema.json")
    if not isinstance(schema, dict):
        raise ValueError("schemas/pr-merge-readiness-report.schema.json is not a mapping")
    return schema


def _safe_relative(path: Path, root: Path, ref: object) -> Path | None:
    if not isinstance(ref, str) or not ref.strip():
        return None
    ref_path = Path(ref)
    if ref_path.is_absolute() or ".." in ref_path.parts:
        return None
    resolved = (path.parent / ref_path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    return resolved


def _path_exists(report_path: Path, root: Path, ref: object) -> bool:
    resolved = _safe_relative(report_path, root, ref)
    return bool(resolved and resolved.is_file())


def _record_missing(
    report_path: Path,
    root: Path,
    ref: object,
    missing: list[str],
) -> None:
    if not ref:
        return
    if not _path_exists(report_path, root, ref):
        missing.append(str(ref))


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _external_review_summary(entries: list[dict[str, Any]]) -> dict[str, bool]:
    return {
        "claude_code_live": any(
            entry.get("provider") == "claude-code"
            and entry.get("mode") == "live"
            and entry.get("status") == "pass"
            for entry in entries
        )
    }


def _reviewer_invocation_schema(root: Path) -> dict:
    schema = parse_json(root / "schemas" / "reviewer-invocation.schema.json")
    if not isinstance(schema, dict):
        raise ValueError("schemas/reviewer-invocation.schema.json is not a mapping")
    return schema


def _reviewer_report_schema(root: Path) -> dict:
    schema = parse_json(root / "schemas" / "reviewer-report.schema.json")
    if not isinstance(schema, dict):
        raise ValueError("schemas/reviewer-report.schema.json is not a mapping")
    return schema


def _human_decisions_schema(root: Path) -> dict:
    schema = parse_json(root / "schemas" / "human-decisions.schema.json")
    if not isinstance(schema, dict):
        raise ValueError("schemas/human-decisions.schema.json is not a mapping")
    return schema


def _resolve_invocation_ref(invocation_path: Path, root: Path, ref: object) -> Path | None:
    if not isinstance(ref, str) or not ref.strip():
        return None
    ref_path = Path(ref)
    if ".." in ref_path.parts:
        return None
    root = root.resolve()
    if ref_path.is_absolute():
        resolved = ref_path.resolve()
        candidates = [resolved]
    else:
        candidates = [
            (invocation_path.parent / ref_path).resolve(),
            (root / ref_path).resolve(),
        ]
    for candidate in candidates:
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        if candidate.exists():
            return candidate
    for candidate in candidates:
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        return candidate
    return None


def _role_from_contract_ref(ref: object) -> str | None:
    if not isinstance(ref, str) or not ref.strip():
        return None
    return Path(ref).stem or None


def _external_entry_by_report_path(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for entry in entries:
        report_path = entry.get("normalized_report_path")
        if isinstance(report_path, str) and report_path:
            indexed[report_path] = entry
    return indexed


def _candidate_handles_source_finding(candidate: dict[str, Any], review_id: str, finding_id: str) -> bool:
    for source in candidate.get("source_findings", []) or []:
        if isinstance(source, str):
            continue
        if not isinstance(source, dict):
            continue
        if source.get("id") != finding_id:
            continue
        source_reviewer = source.get("reviewer") or source.get("review_id")
        if source_reviewer == review_id:
            return True
    return False


def _more_blocking(left: str, right: str) -> str:
    if SEVERITY_RANK.get(left, 99) <= SEVERITY_RANK.get(right, 99):
        return left
    return right


def _effective_candidate_severity(
    candidate: dict[str, Any],
    source_blocking_findings: list[dict[str, Any]],
) -> str:
    validated_severity = str(candidate.get("validated_severity", ""))
    candidate_severity = str(candidate.get("severity", ""))
    effective = validated_severity or candidate_severity
    for source in source_blocking_findings:
        if _candidate_handles_source_finding(candidate, source["review_id"], source["finding_id"]):
            effective = _more_blocking(effective, source["severity"])
    return effective


def _nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_grounded_blocker_path(finding: dict[str, Any]) -> bool:
    return _nonempty_text(finding.get("blocker_path")) and _nonempty_text(
        finding.get("acceptance_impact")
    )


def _has_calibration_reason(finding: dict[str, Any]) -> bool:
    return any(
        _nonempty_text(finding.get(key))
        for key in [
            "validation_rationale",
            "calibration_reason",
            "no_blocker_path_reason",
        ]
    )


def _is_mandatory_evidence_gap(finding: dict[str, Any]) -> bool:
    return finding.get("mandatory_evidence_gap") is True


def _effective_grounded_blocker_path(
    candidate: dict[str, Any],
    source_blocking_findings: list[dict[str, Any]],
) -> bool:
    if _has_grounded_blocker_path(candidate):
        return True
    return any(
        _candidate_handles_source_finding(candidate, source["review_id"], source["finding_id"])
        and _has_grounded_blocker_path(source)
        for source in source_blocking_findings
    )


def _effective_mandatory_evidence_gap(
    candidate: dict[str, Any],
    source_blocking_findings: list[dict[str, Any]],
) -> bool:
    if _is_mandatory_evidence_gap(candidate):
        return True
    return any(
        _candidate_handles_source_finding(candidate, source["review_id"], source["finding_id"])
        and _is_mandatory_evidence_gap(source)
        for source in source_blocking_findings
    )


def _validate_control_report(
    root: Path,
    report_path: Path,
    ref: object,
    reviewer_report_schema: dict,
    missing: list[str],
    blockers: list[str],
    finding_id: str,
    collision_batch_id: str,
    latest_material_change_at: datetime | None,
    collision_prompt_prepared_at: datetime | None,
) -> str | None:
    _record_missing(report_path, root, ref, missing)
    resolved = _safe_relative(report_path, root, ref)
    if not resolved or not resolved.is_file():
        return None
    try:
        data = parse_json(resolved)
    except ValueError:
        blockers.append(f"collision_control_report_invalid:{finding_id}")
        return None
    if not isinstance(data, dict):
        blockers.append(f"collision_control_report_invalid:{finding_id}")
        return None
    if validate_against_schema(resolved, data, reviewer_report_schema):
        blockers.append(f"collision_control_report_invalid:{finding_id}")
        return None
    reviewer = data.get("reviewer")
    if not isinstance(reviewer, dict) or not reviewer.get("id"):
        blockers.append(f"collision_control_report_invalid:{finding_id}")
        return None
    collision = data.get("collision_control")
    if not isinstance(collision, dict):
        blockers.append(f"collision_control_report_invalid:{finding_id}")
        return None
    disputed = collision.get("disputed_finding_ids")
    control_conclusion = collision.get("control_conclusion")
    if (
        collision.get("collision_batch_id") != collision_batch_id
        or not isinstance(disputed, list)
        or finding_id not in disputed
        or not control_conclusion
    ):
        blockers.append(f"collision_control_report_invalid:{finding_id}")
        return None
    if control_conclusion != SUPPORTED_COLLISION_CONTROL_CONCLUSION:
        blockers.append(f"collision_control_unsupported:{finding_id}")
        return None
    completed_at = _parse_timestamp(collision.get("completed_at"))
    if not completed_at:
        blockers.append(f"collision_control_report_invalid:{finding_id}")
        return None
    if latest_material_change_at:
        try:
            if completed_at < latest_material_change_at:
                blockers.append(f"collision_control_stale:{finding_id}")
                return None
        except TypeError:
            blockers.append(f"collision_control_report_invalid:{finding_id}")
            return None
    if collision_prompt_prepared_at:
        try:
            if completed_at < collision_prompt_prepared_at:
                blockers.append(f"collision_control_stale:{finding_id}")
                return None
        except TypeError:
            blockers.append(f"collision_control_report_invalid:{finding_id}")
            return None
    return str(reviewer["id"])


def _validate_collision_control_prompt_contract(
    root: Path,
    report_path: Path,
    ref: object,
    missing: list[str],
    blockers: list[str],
    finding_id: str,
    collision_batch_id: str,
    latest_material_change_at: datetime | None,
) -> tuple[set[str], datetime | None]:
    _record_missing(report_path, root, ref, missing)
    resolved = _safe_relative(report_path, root, ref)
    if not resolved or not resolved.is_file():
        blockers.append(f"collision_control_prompt_contract_missing:{finding_id}")
        return set(), None
    try:
        data = parse_yaml(resolved)
    except ValueError:
        blockers.append(f"collision_control_prompt_contract_invalid:{finding_id}")
        return set(), None
    if not isinstance(data, dict):
        blockers.append(f"collision_control_prompt_contract_invalid:{finding_id}")
        return set(), None
    schema = parse_json(root / "schemas" / "review-prompt-contract.schema.json")
    if not isinstance(schema, dict) or validate_against_schema(resolved, data, schema):
        blockers.append(f"collision_control_prompt_contract_invalid:{finding_id}")

    identity = data.get("identity")
    if not isinstance(identity, dict) or identity.get("review_profile") != "collision-control":
        blockers.append(f"collision_control_prompt_contract_invalid:{finding_id}")
    if isinstance(identity, dict) and identity.get("primary_gate") is not False:
        blockers.append(f"collision_control_prompt_contract_invalid:{finding_id}")

    collision = data.get("collision_control")
    prepared_at: datetime | None = None
    if not isinstance(collision, dict):
        blockers.append(f"collision_control_prompt_contract_invalid:{finding_id}")
    else:
        disputed = collision.get("disputed_findings")
        disputed_ids = {
            str(item.get("finding_id"))
            for item in disputed or []
            if isinstance(item, dict) and item.get("finding_id")
        }
        if (
            collision.get("trigger") != "rejected_or_downgraded_blocker_collision"
            or collision.get("collision_batch_id") != collision_batch_id
            or collision.get("control_reviewer_count") != 2
            or finding_id not in disputed_ids
        ):
            blockers.append(f"collision_control_prompt_contract_invalid:{finding_id}")
        prepared_at = _parse_timestamp(collision.get("prepared_at"))
        if not prepared_at:
            blockers.append(f"collision_control_prompt_contract_invalid:{finding_id}")
        elif latest_material_change_at:
            try:
                if prepared_at < latest_material_change_at:
                    blockers.append(f"collision_control_stale:{finding_id}")
            except TypeError:
                blockers.append(f"collision_control_prompt_contract_invalid:{finding_id}")

    reviewer_ids = {
        str(item.get("instance_id"))
        for item in data.get("reviewer_set", []) or []
        if isinstance(item, dict) and item.get("instance_id")
    }
    if len(reviewer_ids) != 2:
        blockers.append(f"collision_control_prompt_contract_invalid:{finding_id}")
    return reviewer_ids, prepared_at


def _has_matching_human_decision(
    root: Path,
    report_path: Path,
    report_run_id: object,
    report_material_change_id: object,
    report_hash: str,
    decision: dict[str, Any],
) -> bool | None:
    decision_id = decision.get("decision_id")
    if not isinstance(decision_id, str) or not decision_id.strip():
        return None
    resolved = _safe_relative(report_path, root, decision.get("path"))
    if not resolved or not resolved.is_file():
        return None
    try:
        data = parse_yaml(resolved)
    except ValueError:
        return False
    if not isinstance(data, dict):
        return False
    schema_errors = validate_against_schema(resolved, data, _human_decisions_schema(root))
    if schema_errors:
        return False
    if data.get("run_id") != report_run_id:
        return False
    decisions = data.get("decisions")
    if not isinstance(decisions, list):
        return False
    matching: list[dict[str, Any]] = []
    for item in decisions:
        if not isinstance(item, dict) or item.get("decision_id") != decision_id:
            continue
        if decision_id != "merge.acceptance":
            return False
        if not _affected_artifacts_target_report(
            item.get("affected_artifacts"),
            resolved,
            root,
            report_path,
        ):
            continue
        matching.append(item)

    if not matching:
        return False
    if len(matching) != 1:
        return False
    item = matching[0]
    if item.get("status") in {"rejected", "superseded"}:
        return False

    answer = item.get("answer")
    answer_accepted = answer is True or str(answer) in {
        "accepted",
        "merge_ready",
        "accepted_merge_ready",
    }
    return (
        item.get("status") == "confirmed"
        and item.get("answered_by") == "human"
        and item.get("classification") == "blocking-material"
        and item.get("phase_id") == "human_merge_decision"
        and item.get("question_ref") == "merge.acceptance"
        and item.get("material_change_id") == report_material_change_id
        and item.get("report_hash") == report_hash
        and _affected_artifacts_target_report(
            item.get("affected_artifacts"),
            resolved,
            root,
            report_path,
        )
        and answer_accepted
    )


def _affected_artifacts_target_report(
    affected: object,
    decisions_path: Path,
    root: Path,
    report_path: Path,
) -> bool:
    if not isinstance(affected, list):
        return False
    report_resolved = report_path.resolve()
    for ref in affected:
        ref_path = Path(str(ref))
        if ref_path.is_absolute() or ".." in ref_path.parts:
            continue
        candidates = [
            (decisions_path.parent / ref_path).resolve(),
            (root / ref_path).resolve(),
        ]
        if any(candidate == report_resolved for candidate in candidates):
            return True
    return False


def _normalization_source_ref(data: dict[str, Any] | None) -> str:
    if not isinstance(data, dict):
        return ""
    normalization = data.get("normalization")
    if not isinstance(normalization, dict):
        return ""
    source_path = normalization.get("source_path")
    if not isinstance(source_path, str):
        return ""
    return source_path.strip()


def _record_hash_check(
    blockers: list[str],
    review_id: str,
    label: str,
    declared: object,
    artifact_path: Path | None,
    missing_blocker: str | None = None,
) -> None:
    if not is_concrete_sha256(declared):
        blockers.append(f"external_review_invocation_missing_{label}_hash:{review_id}")
        return
    if not artifact_path or not artifact_path.is_file():
        if missing_blocker:
            blockers.append(f"{missing_blocker}:{review_id}")
        return
    if declared != sha256_file(artifact_path):
        blockers.append(f"external_review_{label}_hash_mismatch:{review_id}")


def _record_expected_hash_check(
    blockers: list[str],
    review_id: str,
    label: str,
    declared: object,
    expected: object,
    missing_blocker: str,
) -> None:
    if not is_concrete_sha256(declared):
        blockers.append(f"external_review_invocation_missing_{label}_hash:{review_id}")
        return
    if not is_concrete_sha256(expected):
        blockers.append(f"{missing_blocker}:{review_id}")
        return
    if declared != expected:
        blockers.append(f"external_review_{label}_hash_mismatch:{review_id}")


def _prompt_contract_rubric_hash(report_path: Path, root: Path, contract_ref: object, review_id: str) -> str | None:
    contract_path = _safe_relative(report_path, root, contract_ref)
    if not contract_path or not contract_path.is_file():
        return None
    try:
        contract = parse_yaml(contract_path)
    except ValueError:
        return None
    if not isinstance(contract, dict):
        return None
    for item in contract.get("rendered_prompts", []) or []:
        if not isinstance(item, dict) or item.get("reviewer") != review_id:
            continue
        rubric_hash = item.get("rubric_hash")
        if is_concrete_sha256(rubric_hash):
            return str(rubric_hash)
    return None


def _validate_live_claude_guardrails(
    root: Path,
    invocation_path: Path,
    invocation: dict[str, Any],
    blockers: list[str],
    review_id: str,
) -> None:
    checked = invocation.get("forbidden_env_checked")
    checked_set = {str(item) for item in checked} if isinstance(checked, list) else set()
    if not REQUIRED_CLAUDE_FORBIDDEN_ENV.issubset(checked_set):
        blockers.append(f"external_review_guardrail_forbidden_env_missing:{review_id}")
    command = str(invocation.get("command") or "")
    if not command.startswith("claude "):
        blockers.append(f"external_review_guardrail_command_invalid:{review_id}")
    if invocation.get("wrapper") != "scripts/reviewers/run_external_reviewer.py":
        blockers.append(f"external_review_guardrail_wrapper_missing:{review_id}")
    provider_config_ref = invocation.get("provider_config_path")
    provider_config_path = _resolve_invocation_ref(invocation_path, root, provider_config_ref)
    if not provider_config_path or not provider_config_path.is_file():
        blockers.append(f"external_review_guardrail_provider_config_missing:{review_id}")
        return
    provider_config_hash = invocation.get("provider_config_hash")
    if not is_concrete_sha256(provider_config_hash):
        blockers.append(f"external_review_invocation_missing_provider_config_hash:{review_id}")
    elif provider_config_hash != sha256_file(provider_config_path):
        blockers.append(f"external_review_provider_config_hash_mismatch:{review_id}")
    if validate_external_review_provider(provider_config_path):
        blockers.append(f"external_review_provider_config_invalid:{review_id}")


def _validate_internal_review_context(
    root: Path,
    review_packet_path: Path | None,
    review_report: dict[str, Any],
    blockers: list[str],
    review_id: str,
) -> None:
    if not review_packet_path or not review_packet_path.is_file():
        blockers.append(f"reviewer_report_context_missing:{review_id}")
        return
    try:
        packet = parse_json(review_packet_path)
    except ValueError:
        blockers.append(f"reviewer_report_context_missing:{review_id}")
        return
    if not isinstance(packet, dict):
        blockers.append(f"reviewer_report_context_missing:{review_id}")
        return
    context = review_report.get("review_context")
    if not isinstance(context, dict):
        blockers.append(f"reviewer_report_context_missing:{review_id}")
        return
    expected_run_id = str(packet.get("run_id") or "")
    if expected_run_id and context.get("run_id") != expected_run_id:
        blockers.append(f"reviewer_report_context_mismatch:{review_id}")
    expected_material_change = str(packet.get("material_change_id") or "")
    if expected_material_change and context.get("material_change_id") != expected_material_change:
        blockers.append(f"reviewer_report_context_mismatch:{review_id}")
    try:
        default_packet_ref = review_packet_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        default_packet_ref = str(review_packet_path)
    expected_packet_ref = str(packet.get("review_packet_path") or default_packet_ref)
    if context.get("review_packet_path") != expected_packet_ref:
        blockers.append(f"reviewer_report_context_mismatch:{review_id}")
    if context.get("reviewer_instance_id") != review_id:
        blockers.append(f"reviewer_report_context_mismatch:{review_id}")


def _validate_live_raw_output_persistence(
    root: Path,
    invocation_path: Path,
    invocation: dict[str, Any],
    review_report: dict[str, Any] | None,
    raw_output: object,
    blockers: list[str],
    review_id: str,
) -> None:
    raw_output_path = _resolve_invocation_ref(
        invocation_path,
        root,
        invocation.get("raw_output_path"),
    )
    raw_persistence = raw_output.get("persistence") if isinstance(raw_output, dict) else None
    persisted_raw_ref = (
        isinstance(invocation.get("raw_output_path"), str)
        and bool(invocation.get("raw_output_path", "").strip())
    )
    persisted_raw_ref = persisted_raw_ref or bool(_normalization_source_ref(invocation))
    persisted_raw_ref = persisted_raw_ref or bool(_normalization_source_ref(review_report))
    if raw_persistence == "raw":
        if not raw_output_path or not raw_output_path.is_file():
            blockers.append(f"external_review_raw_output_missing:{review_id}")
            return
        raw_output_hash = invocation.get("raw_output_hash")
        if not is_concrete_sha256(raw_output_hash):
            blockers.append(f"external_review_invocation_missing_raw_output_hash:{review_id}")
            return
        if raw_output_hash != sha256_file(raw_output_path):
            blockers.append(f"external_review_raw_output_hash_mismatch:{review_id}")
    elif persisted_raw_ref:
        blockers.append(f"raw_output_unexpected_persisted:{review_id}")


def _classify_state(
    blockers: list[str],
    stale_reviews: list[str],
    human_status: str,
    human_record_valid: bool,
    is_non_real_fixture: bool,
) -> str:
    if is_non_real_fixture:
        return "incomplete"
    if "cyclic_self_proof_claim" in blockers:
        return "blocked_cyclic_self_proof"
    if "missing_required_evidence" in blockers:
        return "blocked_missing_evidence"
    if any(
        blocker.startswith(
            (
                "review_requirements_",
                "required_review_",
                "required_live_claude_not_declared:",
                "missing_required_review:",
                "duplicate_required_review:",
                "duplicate_review:",
                "reviewer_report_",
            )
        )
        for blocker in blockers
    ):
        return "blocked_missing_evidence"
    if "live_claude_absent" in blockers:
        return "blocked_external_review"
    if any(blocker.startswith("external_review_") for blocker in blockers):
        return "blocked_external_review"
    if any(blocker.startswith("raw_") for blocker in blockers):
        return "blocked_sensitive_raw_evidence"
    if any(blocker.startswith("collision_control_") for blocker in blockers):
        return "blocked_collision_control"
    if stale_reviews:
        return "blocked_stale_review"
    if any(blocker.startswith("failed_check:") or blocker.startswith("failed_review:") for blocker in blockers):
        return "rejected"
    if any(blocker.startswith("unresolved_blocking_finding:") for blocker in blockers):
        return "rejected"
    if any(blocker.startswith("unresolved_duplicate_blocking_finding:") for blocker in blockers):
        return "rejected"
    if any(blocker.startswith("unhandled_source_blocking_finding:") for blocker in blockers):
        return "rejected"
    if blockers:
        return "rejected"
    if human_status != "accepted" or not human_record_valid:
        return "awaiting_human_decision"
    return "accepted_merge_ready"


def evaluate_pr_merge_readiness_report(root: Path, report_path: Path) -> dict[str, Any]:
    root = root.resolve()
    report_path = report_path.resolve()
    data = parse_json(report_path)
    if not isinstance(data, dict):
        return {
            "state": "invalid",
            "accepted": False,
            "blockers": ["report_not_object"],
            "warnings": [],
            "missing_evidence": [],
            "stale_reviews": [],
            "external_review": {"claude_code_live": False},
            "human_decision": {"required": True, "status": "missing"},
            "allowed_statuses": [],
        }

    missing_evidence: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []
    stale_reviews: list[str] = []
    human_record_valid = False
    reviewer_report_schema = _reviewer_report_schema(root)
    reviewer_invocation_schema = _reviewer_invocation_schema(root)
    reviewer_reports: dict[str, dict[str, Any]] = {}
    reviewer_report_paths: dict[str, Path] = {}
    source_blocking_findings: list[dict[str, str]] = []
    report_run_id = str(data.get("run_id") or "")
    report_material_change_id = str(data.get("material_change_id") or "")
    if not report_material_change_id:
        blockers.append("material_change_id_missing")

    for check in data.get("checks", []) or []:
        if isinstance(check, dict):
            _record_missing(report_path, root, check.get("evidence_path"), missing_evidence)
            if check.get("status") != "pass":
                blockers.append(f"failed_check:{check.get('id', '<unknown>')}")

    external_entries = [
        entry
        for entry in data.get("external_review_evidence", []) or []
        if isinstance(entry, dict)
    ]
    external_by_report = _external_entry_by_report_path(external_entries)
    reviews = [
        review
        for review in data.get("reviews", []) or []
        if isinstance(review, dict)
    ]
    reviews_by_id: dict[str, dict[str, Any]] = {}
    latest_material_change_at: datetime | None = None
    for review in reviews:
        review_id = str(review.get("id", "<unknown>"))
        if review_id in reviews_by_id:
            blockers.append(f"duplicate_review:{review_id}")
        reviews_by_id[review_id] = review

    review_requirements = data.get("review_requirements")
    required_reviews = []
    if isinstance(review_requirements, dict):
        required_reviews = [
            item
            for item in review_requirements.get("required_reviews", []) or []
            if isinstance(item, dict)
        ]
    if not required_reviews:
        blockers.append("review_requirements_missing")
    required_ids: set[str] = set()
    required_by_id = {
        str(item.get("id", "")): item
        for item in required_reviews
        if isinstance(item, dict) and item.get("id")
    }
    if data.get("workflow") == "pr-merge-readiness":
        for default_id, default_topic, default_provider, default_live, default_role in DEFAULT_PR_MERGE_REQUIRED_REVIEWS:
            declared = required_by_id.get(default_id)
            if not declared:
                blockers.append(f"review_requirements_undeclared:{default_id}")
                if default_id not in reviews_by_id:
                    blockers.append(f"missing_required_review:{default_id}")
                continue
            if declared.get("topic") != default_topic:
                blockers.append(f"required_review_mismatch:{default_id}:topic")
            if declared.get("provider") != default_provider:
                blockers.append(f"required_review_mismatch:{default_id}:provider")
            if default_provider == "claude-code" and declared.get("required_live") is not default_live:
                blockers.append(f"required_live_claude_not_declared:{default_id}")
            if declared.get("role") != default_role:
                blockers.append(f"required_review_mismatch:{default_id}:role")
    for required in required_reviews:
        required_id = str(required.get("id", ""))
        if not required_id:
            blockers.append("required_review_id_missing")
            continue
        if required_id in required_ids:
            blockers.append(f"duplicate_required_review:{required_id}")
        required_ids.add(required_id)
        review = reviews_by_id.get(required_id)
        if not review:
            blockers.append(f"missing_required_review:{required_id}")
            continue
        for key in ["topic", "provider"]:
            if required.get(key) != review.get(key):
                blockers.append(f"required_review_mismatch:{required_id}:{key}")
        if required.get("provider") == "claude-code" and required.get("required_live") is not True:
            blockers.append(f"required_live_claude_not_declared:{required_id}")
        expected_role = required.get("role")
        if expected_role:
            review_role = review.get("role") or _role_from_contract_ref(review.get("role_contract_path"))
            if review_role != expected_role:
                blockers.append(f"required_review_mismatch:{required_id}:role_contract_path")

    for review in reviews:
        review_id = str(review.get("id", "<unknown>"))
        if review.get("status") not in {"pass", "pass-with-notes"}:
            blockers.append(f"failed_review:{review_id}")
        _record_missing(report_path, root, review.get("packet_path"), missing_evidence)
        _record_missing(report_path, root, review.get("report_path"), missing_evidence)
        review_packet_path = _safe_relative(report_path, root, review.get("packet_path"))
        review_report_path = _safe_relative(report_path, root, review.get("report_path"))
        if review_packet_path and review_packet_path.is_file():
            try:
                loaded_packet = parse_json(review_packet_path)
            except ValueError:
                loaded_packet = None
            if not isinstance(loaded_packet, dict):
                blockers.append(f"review_packet_invalid:{review_id}")
            else:
                if report_run_id and loaded_packet.get("run_id") != report_run_id:
                    blockers.append(f"review_packet_context_mismatch:{review_id}:run_id")
                if report_material_change_id and loaded_packet.get("material_change_id") != report_material_change_id:
                    blockers.append(f"review_packet_context_mismatch:{review_id}:material_change_id")
        review_report: dict[str, Any] | None = None
        if review_report_path and review_report_path.is_file():
            try:
                loaded_report = parse_json(review_report_path)
            except ValueError:
                loaded_report = None
            if not isinstance(loaded_report, dict):
                blockers.append(f"reviewer_report_invalid:{review_id}")
            else:
                report_errors = validate_against_schema(
                    review_report_path,
                    loaded_report,
                    reviewer_report_schema,
                )
                if report_errors:
                    blockers.append(f"reviewer_report_invalid:{review_id}")
                else:
                    review_report = loaded_report
                    reviewer_reports[review_id] = loaded_report
                    reviewer_report_paths[review_id] = review_report_path
                    reviewer = loaded_report.get("reviewer")
                    if not isinstance(reviewer, dict):
                        blockers.append(f"reviewer_report_identity_mismatch:{review_id}")
                    else:
                        if reviewer.get("id") != review_id:
                            blockers.append(f"reviewer_report_identity_mismatch:{review_id}")
                        if reviewer.get("provider") != review.get("provider"):
                            blockers.append(f"reviewer_report_provider_mismatch:{review_id}")
                        required = required_by_id.get(review_id, {})
                        expected_role = required.get("role") if isinstance(required, dict) else None
                        if expected_role and reviewer.get("role") != expected_role:
                            blockers.append(f"reviewer_report_role_mismatch:{review_id}")
                    if review.get("provider") == "internal-agent":
                        _validate_internal_review_context(
                            root,
                            review_packet_path,
                            loaded_report,
                            blockers,
                            review_id,
                        )
                    for finding in loaded_report.get("findings", []) or []:
                        if not isinstance(finding, dict):
                            continue
                        severity = str(finding.get("severity", ""))
                        finding_id = str(finding.get("id", "<unknown>"))
                        if (
                            severity in BLOCKING_FINDING_SEVERITIES
                            or _is_mandatory_evidence_gap(finding)
                        ):
                            source_blocking_findings.append(
                                {
                                    "review_id": review_id,
                                    "finding_id": finding_id,
                                    "severity": severity,
                                    "blocker_path": finding.get("blocker_path"),
                                    "acceptance_impact": finding.get("acceptance_impact"),
                                    "mandatory_evidence_gap": finding.get("mandatory_evidence_gap"),
                                }
                            )
        prepared_at = _parse_timestamp(review.get("packet_prepared_at"))
        material_at = _parse_timestamp(review.get("latest_material_change_at"))
        if material_at:
            try:
                if latest_material_change_at is None or material_at > latest_material_change_at:
                    latest_material_change_at = material_at
            except TypeError:
                blockers.append(f"invalid_review_timestamp:{review_id}")
        if not prepared_at or not material_at:
            stale_reviews.append(review_id)
            blockers.append(f"invalid_review_timestamp:{review_id}")
        else:
            try:
                is_stale = prepared_at < material_at
            except TypeError:
                is_stale = True
                blockers.append(f"invalid_review_timestamp:{review_id}")
            if is_stale:
                if review_id not in stale_reviews:
                    stale_reviews.append(review_id)
                blockers.append(f"stale_review:{review_id}")
        if review.get("provider") == "claude-code":
            external_entry = external_by_report.get(str(review.get("report_path", "")))
            if not external_entry:
                blockers.append(f"external_review_evidence_missing:{review_id}")
                continue
            if external_entry.get("provider") != "claude-code":
                blockers.append(f"external_review_provider_mismatch:{review_id}")
            if external_entry.get("required_live") is not True:
                blockers.append(f"external_review_required_live_missing:{review_id}")
            if external_entry.get("mode") != "live" or external_entry.get("status") != "pass":
                blockers.append(f"external_review_not_live:{review_id}")
            invocation_ref = external_entry.get("invocation_metadata_path")
            invocation_path = _safe_relative(report_path, root, invocation_ref)
            if not invocation_path or not invocation_path.is_file():
                blockers.append(f"external_review_invocation_missing:{review_id}")
                continue
            try:
                invocation = parse_json(invocation_path)
            except ValueError:
                invocation = None
            if not isinstance(invocation, dict):
                blockers.append(f"external_review_invocation_invalid:{review_id}")
            else:
                invocation_errors = validate_against_schema(
                    invocation_path,
                    invocation,
                    reviewer_invocation_schema,
                )
                if invocation_errors:
                    blockers.append(f"external_review_invocation_invalid:{review_id}")
                if invocation.get("provider") != "claude-code":
                    blockers.append(f"external_review_invocation_provider_mismatch:{review_id}")
                if invocation.get("permission_mode") != "default":
                    blockers.append(f"external_review_invocation_unsafe_permission_mode:{review_id}")
                if invocation.get("output_format") != "json":
                    blockers.append(f"external_review_invocation_output_format_invalid:{review_id}")
                if invocation.get("requested_model") != "opus":
                    blockers.append(f"external_review_invocation_model_invalid:{review_id}")
                if invocation.get("requested_effort") != "max":
                    blockers.append(f"external_review_invocation_effort_invalid:{review_id}")
                prompt_transport = invocation.get("prompt_transport")
                if prompt_transport not in {"stdin", "file"}:
                    blockers.append(f"external_review_invocation_prompt_transport_missing:{review_id}")
                elif prompt_transport == "stdin" and invocation.get("tools") != "":
                    blockers.append(f"external_review_invocation_tools_invalid:{review_id}")
                elif prompt_transport == "file" and invocation.get("tools") != "Read":
                    blockers.append(f"external_review_invocation_tools_invalid:{review_id}")
                if invocation.get("execution_mode") != "real":
                    blockers.append(f"external_review_not_real:{review_id}")
                if invocation.get("exit_code") != 0:
                    blockers.append(f"external_review_invocation_failed:{review_id}")
                _validate_live_claude_guardrails(root, invocation_path, invocation, blockers, review_id)
                if review_report:
                    reviewer = review_report.get("reviewer")
                    if isinstance(reviewer, dict) and invocation.get("reviewer_role") != reviewer.get("role"):
                        blockers.append(f"external_review_invocation_role_mismatch:{review_id}")
                required = required_by_id.get(review_id, {})
                expected_role = required.get("role") if isinstance(required, dict) else None
                if expected_role and invocation.get("reviewer_role") != expected_role:
                    blockers.append(f"external_review_invocation_role_mismatch:{review_id}")
                _record_hash_check(
                    blockers,
                    review_id,
                    "input",
                    invocation.get("input_hash"),
                    review_packet_path,
                    "external_review_packet_missing",
                )
                prompt_path = _safe_relative(report_path, root, review.get("prompt_path"))
                _record_hash_check(
                    blockers,
                    review_id,
                    "prompt",
                    invocation.get("prompt_hash"),
                    prompt_path,
                    "external_review_prompt_path_missing",
                )
                review_prompt_contract_path = _safe_relative(
                    report_path,
                    root,
                    (review_requirements or {}).get("review_prompt_contract_path")
                    if isinstance(review_requirements, dict)
                    else None,
                )
                _record_hash_check(
                    blockers,
                    review_id,
                    "review_prompt_contract",
                    invocation.get("review_prompt_contract_hash"),
                    review_prompt_contract_path,
                    "external_review_prompt_contract_path_missing",
                )
                role_contract_path = _safe_relative(report_path, root, review.get("role_contract_path"))
                _record_hash_check(
                    blockers,
                    review_id,
                    "role_contract",
                    invocation.get("role_contract_hash"),
                    role_contract_path,
                    "external_review_role_contract_path_missing",
                )
                rubric_path = _safe_relative(
                    report_path,
                    root,
                    (review_requirements or {}).get("rubric_path") if isinstance(review_requirements, dict) else None,
                )
                prompt_contract_rubric_hash = _prompt_contract_rubric_hash(
                    report_path,
                    root,
                    (review_requirements or {}).get("review_prompt_contract_path")
                    if isinstance(review_requirements, dict)
                    else None,
                    review_id,
                )
                if prompt_contract_rubric_hash:
                    _record_expected_hash_check(
                        blockers,
                        review_id,
                        "rubric",
                        invocation.get("rubric_hash"),
                        prompt_contract_rubric_hash,
                        "external_review_rubric_path_missing",
                    )
                else:
                    _record_hash_check(
                        blockers,
                        review_id,
                        "rubric",
                        invocation.get("rubric_hash"),
                        rubric_path,
                        "external_review_rubric_path_missing",
                    )
                _record_hash_check(
                    blockers,
                    review_id,
                    "schema",
                    invocation.get("schema_hash"),
                    root / "schemas" / "reviewer-report.schema.json",
                    "external_review_schema_missing",
                )
                normalized_output_path = _resolve_invocation_ref(
                    invocation_path,
                    root,
                    invocation.get("normalized_output_path"),
                )
                if (
                    not normalized_output_path
                    or not review_report_path
                    or normalized_output_path.resolve() != review_report_path.resolve()
                ):
                    blockers.append(f"external_review_invocation_output_path_mismatch:{review_id}")
                raw_output = external_entry.get("raw_output")
                _validate_live_raw_output_persistence(
                    root,
                    invocation_path,
                    invocation,
                    review_report,
                    raw_output,
                    blockers,
                    review_id,
                )
                if review_report_path and review_report_path.is_file() and invocation.get("normalized_output_hash"):
                    if invocation.get("normalized_output_hash") != sha256_file(review_report_path):
                        blockers.append(f"external_review_normalized_output_hash_mismatch:{review_id}")
                elif not invocation.get("normalized_output_hash"):
                    blockers.append(f"external_review_invocation_missing_normalized_output_hash:{review_id}")

    external_review = _external_review_summary(external_entries)
    live_claude_required = any(
        entry.get("provider") == "claude-code" and entry.get("required_live") is True
        for entry in external_entries
    ) or any(
        required.get("provider") == "claude-code" and required.get("required_live") is True
        for required in required_reviews
    )
    for entry in external_entries:
        _record_missing(report_path, root, entry.get("normalized_report_path"), missing_evidence)
        _record_missing(report_path, root, entry.get("invocation_metadata_path"), missing_evidence)
        raw_output = entry.get("raw_output")
        if isinstance(raw_output, dict):
            persistence = raw_output.get("persistence")
            review_id = next(
                (
                    candidate_id
                    for candidate_id, review in reviews_by_id.items()
                    if review.get("report_path") == entry.get("normalized_report_path")
                ),
                str(entry.get("normalized_report_path", "<unknown>")),
            )
            if persistence == "not_persisted" and (
                entry.get("mode") == "live" or entry.get("required_live") is True
            ):
                blockers.append(f"raw_output_not_persisted:{review_id}")
            if persistence in {"redacted", "summary", "pointer"} and not (
                raw_output.get("redaction_reason") or raw_output.get("reason")
            ):
                blockers.append("raw_redaction_reason_missing")
            if persistence == "raw" and raw_output.get("non_sensitive") is not True:
                blockers.append("raw_output_non_sensitive_declaration_missing")
            redacted_ref = raw_output.get("artifact_path")
            redacted_hash = raw_output.get("artifact_hash")
            if persistence in {"redacted", "summary", "pointer"}:
                if not redacted_ref or not redacted_hash:
                    blockers.append(f"raw_output_artifact_missing:{review_id}")
                else:
                    redacted_path = _safe_relative(report_path, root, redacted_ref)
                    if not redacted_path or not redacted_path.is_file():
                        missing_evidence.append(str(redacted_ref))
                        blockers.append(f"raw_output_artifact_missing:{review_id}")
                    elif not is_concrete_sha256(redacted_hash):
                        blockers.append(f"raw_output_artifact_hash_missing:{review_id}")
                    elif redacted_hash != sha256_file(redacted_path):
                        blockers.append(f"raw_output_artifact_hash_mismatch:{review_id}")
    if live_claude_required and not external_review["claude_code_live"]:
        blockers.append("live_claude_absent")

    candidate_findings = [
        finding
        for finding in data.get("candidate_findings", []) or []
        if isinstance(finding, dict)
    ]
    for finding in candidate_findings:
        if not isinstance(finding, dict):
            continue
        severity = _effective_candidate_severity(finding, source_blocking_findings)
        status = str(finding.get("status", ""))
        finding_id = str(finding.get("id", "<unknown>"))
        has_blocker_path = _effective_grounded_blocker_path(finding, source_blocking_findings)
        has_mandatory_gap = _effective_mandatory_evidence_gap(finding, source_blocking_findings)
        if severity not in BLOCKING_FINDING_SEVERITIES and not has_mandatory_gap:
            continue
        if not has_blocker_path and not has_mandatory_gap:
            if status in {"accepted", "needs-more-evidence"}:
                blockers.append(f"finding_blocker_path_missing:{finding_id}")
            elif status in {"rejected", "downgraded", "duplicate"} and not _has_calibration_reason(finding):
                blockers.append(f"finding_calibration_reason_missing:{finding_id}")
            continue
        if status in {"accepted", "needs-more-evidence"}:
            blockers.append(f"unresolved_blocking_finding:{finding_id}")
            continue
        if status == "duplicate":
            blockers.append(f"unresolved_duplicate_blocking_finding:{finding_id}")
            continue
        if status in {"rejected", "downgraded"}:
            control = finding.get("collision_control")
            if not isinstance(control, dict) or control.get("status") != "completed":
                blockers.append(f"collision_control_missing:{finding_id}")
                continue
            evidence_path = control.get("evidence_path")
            review_prompt_contract_path = control.get("review_prompt_contract_path")
            control_reports = control.get("control_reports")
            disputed_finding_ids = control.get("disputed_finding_ids")
            collision_batch_id = control.get("collision_batch_id")
            if (
                not evidence_path
                or not review_prompt_contract_path
                or not isinstance(collision_batch_id, str)
                or not collision_batch_id.strip()
                or control.get("control_reviewer_count") != 2
                or not isinstance(control_reports, list)
                or len(control_reports) < 2
                or not isinstance(disputed_finding_ids, list)
                or finding_id not in disputed_finding_ids
            ):
                blockers.append(f"collision_control_incomplete:{finding_id}")
            _record_missing(report_path, root, evidence_path, missing_evidence)
            expected_control_reviewer_ids = set()
            collision_prompt_prepared_at: datetime | None = None
            if isinstance(collision_batch_id, str) and collision_batch_id.strip():
                (
                    expected_control_reviewer_ids,
                    collision_prompt_prepared_at,
                ) = _validate_collision_control_prompt_contract(
                    root,
                    report_path,
                    review_prompt_contract_path,
                    missing_evidence,
                    blockers,
                    finding_id,
                    collision_batch_id,
                    latest_material_change_at,
                )
            control_reviewer_ids: set[str] = set()
            if isinstance(control_reports, list):
                for control_report in control_reports:
                    if isinstance(control_report, dict):
                        reviewer_id = _validate_control_report(
                            root,
                            report_path,
                            control_report.get("path"),
                            reviewer_report_schema,
                            missing_evidence,
                            blockers,
                            finding_id,
                            collision_batch_id,
                            latest_material_change_at,
                            collision_prompt_prepared_at,
                        )
                    else:
                        reviewer_id = _validate_control_report(
                            root,
                            report_path,
                            control_report,
                            reviewer_report_schema,
                            missing_evidence,
                            blockers,
                            finding_id,
                            collision_batch_id,
                            latest_material_change_at,
                            collision_prompt_prepared_at,
                        )
                    if reviewer_id:
                        control_reviewer_ids.add(reviewer_id)
            if isinstance(control_reports, list) and len(control_reviewer_ids) < 2:
                blockers.append(f"collision_control_incomplete:{finding_id}")
            if expected_control_reviewer_ids and control_reviewer_ids != expected_control_reviewer_ids:
                blockers.append(f"collision_control_reviewer_set_mismatch:{finding_id}")

    for source in source_blocking_findings:
        if not any(
            _candidate_handles_source_finding(
                candidate,
                source["review_id"],
                source["finding_id"],
            )
            for candidate in candidate_findings
        ):
            blockers.append(
                "unhandled_source_blocking_finding:"
                f"{source['review_id']}:{source['finding_id']}"
            )

    human_decision = data.get("human_decision")
    if not isinstance(human_decision, dict):
        human_decision = {"status": "missing"}
    human_summary = {
        "required": True,
        "status": str(human_decision.get("status", "missing")),
    }
    if human_summary["status"] == "accepted":
        if not human_decision.get("path") or not human_decision.get("decision_id"):
            missing_evidence.append("human_decision.path")
            blockers.append("human_decision_record_missing")
        else:
            _record_missing(report_path, root, human_decision.get("path"), missing_evidence)
            match = _has_matching_human_decision(
                root,
                report_path,
                data.get("run_id"),
                report_material_change_id,
                sha256_file(report_path),
                human_decision,
            )
            if match is True:
                human_record_valid = True
            elif match is None:
                blockers.append("human_decision_record_missing")
            else:
                blockers.append("human_decision_record_invalid")
    else:
        warnings.append("human_decision_missing")

    self_application = data.get("self_application")
    if isinstance(self_application, dict) and self_application.get("enabled") is True:
        if self_application.get("proof_claim") != "bootstrap_not_self_proof":
            blockers.append("cyclic_self_proof_claim")

    if missing_evidence:
        blockers.append("missing_required_evidence")

    fixture = data.get("fixture")
    is_non_real_fixture = isinstance(fixture, dict) and fixture.get("not_real_readiness_evidence") is True
    if is_non_real_fixture:
        warnings.append("fixture_not_real_readiness_evidence")

    state = _classify_state(
        blockers,
        stale_reviews,
        human_summary["status"],
        human_record_valid,
        is_non_real_fixture,
    )

    return {
        "state": state,
        "accepted": state == "accepted_merge_ready",
        "blockers": blockers,
        "warnings": warnings,
        "missing_evidence": missing_evidence,
        "stale_reviews": stale_reviews,
        "external_review": external_review,
        "human_decision": human_summary,
        "allowed_statuses": ["accepted_merge_ready"] if state == "accepted_merge_ready" else [state],
    }


def validate_pr_merge_readiness_report(root: Path, report_path: Path) -> list[str]:
    errors: list[str] = []
    data = parse_json(report_path)
    if not isinstance(data, dict):
        return [f"{report_path}: pr-merge-readiness report must be a JSON object"]
    errors.extend(validate_against_schema(report_path, data, _schema(root)))
    if errors:
        return errors
    result = evaluate_pr_merge_readiness_report(root, report_path)
    declared = data.get("status")
    if declared != result["state"]:
        errors.append(
            f"{report_path}: status {declared} does not match computed state {result['state']}"
        )
    for missing in result["missing_evidence"]:
        errors.append(f"{report_path}: missing referenced evidence: {missing}")
    if declared == "accepted_merge_ready" and result["blockers"]:
        errors.append(
            f"{report_path}: accepted report has blockers: {', '.join(result['blockers'])}"
        )
    return errors
