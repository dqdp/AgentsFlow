from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .common import is_concrete_sha256, parse_json, parse_yaml, sha256_file, validate_against_schema
from .external_reviewers import validate_external_review_provider
from .review import validate_review_packet_artifact


BLOCKING_FINDING_SEVERITIES = {"P0", "P1"}
SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "NOTE": 4}
REQUIRED_CLAUDE_FORBIDDEN_ENV = {
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
}
REQUIRED_REVIEW_FIELDS = ("id", "topic", "provider", "role", "required_live")
MIN_REQUIRED_REVIEWERS = 2
GITHUB_PUBLICATION_BODY_FORBIDDEN_MARKERS = (
    "/Users/",
    "/private/var/",
)
LOCAL_PATH_PATTERNS = (
    re.compile(r"(?<!:)\/(?:Users|home|tmp|private\/var|var\/folders|var\/tmp|workspace|opt\/homebrew)\/[^\s)`'\"<>]+"),
    re.compile(r"(?i)\b[A-Z]:[\\/](?:Users|Temp|tmp|workspace)[\\/][^\s)`'\"<>]+"),
)


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


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    return None


def _contains_full_reviewer_report_dump(text: str) -> bool:
    return '"reviewer"' in text and '"findings"' in text and '"review_context"' in text


def _contains_local_path(text: str) -> bool:
    return any(pattern.search(text) for pattern in LOCAL_PATH_PATTERNS)


def _github_pr_url_matches(url: str, expected_pr: int, expected_repository: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "github.com":
        return False
    if not parsed.fragment.startswith("issuecomment-"):
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return (
        len(parts) == 4
        and f"{parts[0]}/{parts[1]}" == expected_repository
        and parts[2] == "pull"
        and parts[3] == str(expected_pr)
    )


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


def _external_review_lite_invocation_schema(root: Path) -> dict:
    schema = parse_json(root / "schemas" / "external-review-lite-invocation.schema.json")
    if not isinstance(schema, dict):
        raise ValueError("schemas/external-review-lite-invocation.schema.json is not a mapping")
    return schema


def _external_review_lite_request_schema(root: Path) -> dict:
    schema = parse_json(root / "schemas" / "external-review-lite-request.schema.json")
    if not isinstance(schema, dict):
        raise ValueError("schemas/external-review-lite-request.schema.json is not a mapping")
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


def _resolve_lite_request_artifact_ref(root: Path, request_path: Path, ref: object) -> Path | None:
    if not isinstance(ref, str) or not ref.strip():
        return None
    ref_path = Path(ref)
    if ref_path.is_absolute() or ".." in ref_path.parts:
        return None
    output_dir = request_path.parent.resolve()
    root = root.resolve()
    root_candidate = (root / ref_path).resolve()
    output_candidate = (output_dir / ref_path).resolve()
    candidates = [root_candidate] if root_candidate.exists() else [output_candidate, root_candidate]
    for candidate in candidates:
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            pass
        try:
            candidate.relative_to(output_dir)
            return candidate
        except ValueError:
            pass
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


def _canonical_required_review(review: dict[str, Any]) -> dict[str, Any]:
    return {field: review.get(field) for field in REQUIRED_REVIEW_FIELDS}


def _required_reviews_from_source(data: object) -> list[dict[str, Any]] | None:
    if not isinstance(data, dict):
        return None
    if data.get("version") != 1 or data.get("artifact_kind") != "review_requirements":
        return None
    reviews = data.get("required_reviews")
    if not isinstance(reviews, list):
        return None
    if len(reviews) < MIN_REQUIRED_REVIEWERS:
        return None
    if not all(isinstance(item, dict) for item in reviews):
        return None
    for item in reviews:
        if not all(field in item for field in REQUIRED_REVIEW_FIELDS):
            return None
        if not all(isinstance(item.get(field), str) and item.get(field).strip() for field in ["id", "topic", "provider", "role"]):
            return None
        if item.get("provider") not in {"internal-agent", "claude-code"}:
            return None
        if not isinstance(item.get("required_live"), bool):
            return None
    return reviews


def _parse_json_or_yaml(path: Path) -> object:
    if path.suffix.lower() == ".json":
        return parse_json(path)
    return parse_yaml(path)


def _validate_review_requirements_source(
    root: Path,
    report_path: Path,
    review_requirements: object,
    required_reviews: list[dict[str, Any]],
    missing_evidence: list[str],
    blockers: list[str],
) -> None:
    if not isinstance(review_requirements, dict):
        blockers.append("review_requirements_source_missing")
        return
    source = review_requirements.get("source")
    if not isinstance(source, dict):
        blockers.append("review_requirements_source_missing")
        return
    source_ref = source.get("path")
    if not source_ref:
        blockers.append("review_requirements_source_missing")
        return
    source_path = _safe_relative(report_path, root, source_ref)
    if not source_path or not source_path.is_file():
        missing_evidence.append(str(source_ref))
        blockers.append("review_requirements_source_missing")
        return
    declared_hash = source.get("artifact_hash")
    if not is_concrete_sha256(declared_hash):
        blockers.append("review_requirements_source_hash_missing")
    elif declared_hash != sha256_file(source_path):
        blockers.append("review_requirements_source_hash_mismatch")
    try:
        source_data = _parse_json_or_yaml(source_path)
    except ValueError:
        blockers.append("review_requirements_source_invalid")
        return
    source_required_reviews = _required_reviews_from_source(source_data)
    if source_required_reviews is None:
        blockers.append("review_requirements_source_invalid")
        return
    source_canonical = [_canonical_required_review(item) for item in source_required_reviews]
    report_canonical = [_canonical_required_review(item) for item in required_reviews]
    if source_canonical != report_canonical:
        blockers.append("review_requirements_source_mismatch")


def _validate_external_lite_request_context(
    root: Path,
    request_path: Path,
    request_schema: dict,
    review_id: str,
    expected_role: object,
    report_run_id: str,
    report_material_change_id: str,
    review_report: dict[str, Any] | None,
    blockers: list[str],
) -> None:
    try:
        request = parse_json(request_path)
    except ValueError:
        blockers.append(f"external_review_request_invalid:{review_id}")
        return
    if not isinstance(request, dict):
        blockers.append(f"external_review_request_invalid:{review_id}")
        return
    if validate_against_schema(request_path, request, request_schema):
        blockers.append(f"external_review_request_invalid:{review_id}")
    if request.get("provider") != "claude-code":
        blockers.append(f"external_review_request_provider_mismatch:{review_id}")
    reviewer = request.get("reviewer")
    if not isinstance(reviewer, dict):
        blockers.append(f"external_review_request_reviewer_mismatch:{review_id}")
    else:
        if reviewer.get("id") != review_id:
            blockers.append(f"external_review_request_reviewer_mismatch:{review_id}")
        if expected_role and reviewer.get("role") != expected_role:
            blockers.append(f"external_review_request_role_mismatch:{review_id}")
    if report_run_id and request.get("run_id") != report_run_id:
        blockers.append(f"external_review_request_context_mismatch:{review_id}:run_id")
    if report_material_change_id and request.get("material_change_id") != report_material_change_id:
        blockers.append(f"external_review_request_context_mismatch:{review_id}:material_change_id")
    artifacts = request.get("artifacts")
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                blockers.append(f"external_review_request_artifact_invalid:{review_id}")
                continue
            artifact_path = _resolve_lite_request_artifact_ref(
                root,
                request_path,
                artifact.get("path"),
            )
            if not artifact_path or not artifact_path.is_file():
                blockers.append(f"external_review_request_artifact_missing:{review_id}")
                continue
            if artifact.get("hash") != sha256_file(artifact_path):
                blockers.append(f"external_review_request_artifact_hash_mismatch:{review_id}")
            bundle_path = artifact.get("bundle_path")
            if bundle_path:
                bundle_ref = Path(str(bundle_path))
                if bundle_ref.is_absolute() or ".." in bundle_ref.parts:
                    blockers.append(f"external_review_request_artifact_bundle_path_mismatch:{review_id}")
                    continue
                bundle_resolved = (request_path.parent / bundle_ref).resolve()
                if bundle_resolved != artifact_path.resolve():
                    blockers.append(f"external_review_request_artifact_bundle_path_mismatch:{review_id}")
    if not review_report:
        return
    context = review_report.get("review_context")
    if not isinstance(context, dict):
        blockers.append(f"reviewer_report_context_missing:{review_id}")
        return
    if report_run_id and context.get("run_id") != report_run_id:
        blockers.append(f"reviewer_report_context_mismatch:{review_id}")
    if report_material_change_id and context.get("material_change_id") != report_material_change_id:
        blockers.append(f"reviewer_report_context_mismatch:{review_id}")
    if context.get("reviewer_instance_id") != review_id:
        blockers.append(f"reviewer_report_context_mismatch:{review_id}")


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


def _has_concrete_evidence(finding: dict[str, Any]) -> bool:
    evidence = finding.get("evidence")
    return isinstance(evidence, list) and any(_nonempty_text(item) for item in evidence)


def _has_grounded_blocker_path(finding: dict[str, Any]) -> bool:
    return (
        _has_concrete_evidence(finding)
        and _nonempty_text(finding.get("blocker_path"))
        and _nonempty_text(finding.get("acceptance_impact"))
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


def _validate_loaded_review_packet_binding(
    loaded_packet: dict[str, Any],
    review: dict[str, Any],
    required: dict[str, Any],
    report_material_change_id: str,
    blockers: list[str],
) -> None:
    review_id = str(review.get("id", "<unknown>"))
    if loaded_packet.get("reviewer_instance_id") != review_id:
        blockers.append(f"review_packet_context_mismatch:{review_id}:reviewer_instance_id")
    if loaded_packet.get("review_packet_path") and loaded_packet.get("review_packet_path") != review.get("packet_path"):
        blockers.append(f"review_packet_context_mismatch:{review_id}:review_packet_path")
    for key in ["topic", "provider"]:
        if loaded_packet.get(key) and loaded_packet.get(key) != review.get(key):
            blockers.append(f"review_packet_context_mismatch:{review_id}:{key}")
    expected_role = required.get("role") or _role_from_contract_ref(review.get("role_contract_path"))
    if expected_role and loaded_packet.get("reviewer_role") != expected_role:
        blockers.append(f"review_packet_context_mismatch:{review_id}:reviewer_role")
    if review.get("role_contract_path") and loaded_packet.get("role_contract") != review.get("role_contract_path"):
        blockers.append(f"review_packet_context_mismatch:{review_id}:role_contract")
    freshness = loaded_packet.get("evidence_freshness")
    if not isinstance(freshness, dict) or freshness.get("material_change_id") != report_material_change_id:
        blockers.append(f"review_packet_context_mismatch:{review_id}:evidence_freshness.material_change_id")


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
        and item.get("phase_id") == "final_human_merge_decision"
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


def _validate_github_publication_result(
    root: Path,
    report_path: Path,
    publication: dict[str, Any],
    expected_pr: int | None,
    expected_repository: str | None,
    blockers: list[str],
    missing_evidence: list[str],
) -> None:
    if publication.get("publication_mode") != "summary_comment":
        blockers.append("github_publication_evidence_invalid")
    if publication.get("target") != "pull_request":
        blockers.append("github_publication_evidence_invalid")
    if publication.get("tool") != "gh":
        blockers.append("github_publication_evidence_invalid")
    if publication.get("action") != "pr comment":
        blockers.append("github_publication_evidence_invalid")

    body_ref = publication.get("body_path")
    result_ref = publication.get("result_path") or publication.get("evidence_path")
    body_path = _safe_relative(report_path, root, body_ref)
    result_path = _safe_relative(report_path, root, result_ref)
    if not body_path or not body_path.is_file():
        missing_evidence.append(str(body_ref or "github_publication.body_path"))
        blockers.append("github_publication_evidence_missing")
    else:
        body_text = body_path.read_text(encoding="utf-8", errors="replace")
        if not body_text.strip():
            blockers.append("github_publication_evidence_invalid")
        if any(marker in body_text for marker in GITHUB_PUBLICATION_BODY_FORBIDDEN_MARKERS):
            blockers.append("github_publication_evidence_invalid")
        if _contains_local_path(body_text):
            blockers.append("github_publication_evidence_invalid")
        if _contains_full_reviewer_report_dump(body_text):
            blockers.append("github_publication_evidence_invalid")
        body_hash = publication.get("body_hash")
        if not is_concrete_sha256(body_hash) or body_hash != sha256_file(body_path):
            blockers.append("github_publication_evidence_invalid")
    if not result_path or not result_path.is_file():
        missing_evidence.append(str(result_ref or "github_publication.result_path"))
        blockers.append("github_publication_evidence_missing")
        return

    try:
        result = parse_json(result_path)
    except ValueError:
        blockers.append("github_publication_evidence_invalid")
        return
    if not isinstance(result, dict):
        blockers.append("github_publication_evidence_invalid")
        return
    if result.get("provider") != "github":
        blockers.append("github_publication_evidence_invalid")
    if result.get("tool") != "gh":
        blockers.append("github_publication_evidence_invalid")
    if result.get("action") != "pr comment":
        blockers.append("github_publication_evidence_invalid")
    if result.get("status") != "published":
        blockers.append("github_publication_evidence_missing")
    if result.get("body_path") != body_ref:
        blockers.append("github_publication_evidence_invalid")
    if result.get("body_hash") != publication.get("body_hash"):
        blockers.append("github_publication_evidence_invalid")
    publication_pr = _positive_int(publication.get("pr"))
    result_pr = _positive_int(result.get("pr"))
    if not expected_pr or publication_pr != expected_pr or result_pr != expected_pr:
        blockers.append("github_publication_evidence_invalid")
    result_url = result.get("url")
    if not isinstance(result_url, str) or not result_url.strip():
        blockers.append("github_publication_evidence_missing")
    elif (
        not expected_pr
        or not expected_repository
        or not _github_pr_url_matches(result_url, expected_pr, expected_repository)
    ):
        blockers.append("github_publication_evidence_invalid")
    report_url = publication.get("url")
    if isinstance(report_url, str) and report_url.strip() and result_url != report_url:
        blockers.append("github_publication_evidence_invalid")


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
    wrapper = invocation.get("wrapper")
    if wrapper != "scripts/reviewers/run_external_review_lite.py":
        blockers.append(f"external_review_guardrail_wrapper_missing:{review_id}")
    provider_config_ref = invocation.get("effective_provider_config_path")
    provider_config_path = _resolve_invocation_ref(invocation_path, root, provider_config_ref)
    if not provider_config_path or not provider_config_path.is_file():
        blockers.append(f"external_review_guardrail_provider_config_missing:{review_id}")
        return
    provider_config_hash = invocation.get("effective_provider_config_hash")
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
                "review_packet_",
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
    if any(blocker.startswith("github_publication_evidence_") for blocker in blockers):
        return "blocked_missing_evidence"
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
    if not human_record_valid:
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
    lite_invocation_schema = _external_review_lite_invocation_schema(root)
    lite_request_schema = _external_review_lite_request_schema(root)
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
    elif len(required_reviews) < MIN_REQUIRED_REVIEWERS:
        blockers.append("review_requirements_minimum_not_met")
    _validate_review_requirements_source(
        root,
        report_path,
        review_requirements,
        required_reviews,
        missing_evidence,
        blockers,
    )
    required_ids: set[str] = set()
    required_by_id = {
        str(item.get("id", "")): item
        for item in required_reviews
        if isinstance(item, dict) and item.get("id")
    }
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
                if validate_review_packet_artifact(
                    root,
                    review_packet_path,
                    check_references=True,
                    require_green_verification_gate=True,
                ):
                    blockers.append(f"review_packet_invalid:{review_id}")
                if report_run_id and loaded_packet.get("run_id") != report_run_id:
                    blockers.append(f"review_packet_context_mismatch:{review_id}:run_id")
                if report_material_change_id and loaded_packet.get("material_change_id") != report_material_change_id:
                    blockers.append(f"review_packet_context_mismatch:{review_id}:material_change_id")
                required = required_by_id.get(review_id, {})
                if isinstance(required, dict):
                    _validate_loaded_review_packet_binding(
                        loaded_packet,
                        review,
                        required,
                        report_material_change_id,
                        blockers,
                    )
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
                                    "evidence": finding.get("evidence"),
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
                is_lite_invocation = invocation.get("context_mode") == "lite"
                if not is_lite_invocation:
                    blockers.append(f"external_review_invocation_not_lite:{review_id}")
                    continue
                invocation_errors = validate_against_schema(
                    invocation_path,
                    invocation,
                    lite_invocation_schema,
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
                review_request_path = _resolve_invocation_ref(
                    invocation_path,
                    root,
                    invocation.get("review_request_path"),
                )
                _record_hash_check(
                    blockers,
                    review_id,
                    "input",
                    invocation.get("input_hash"),
                    review_request_path,
                    "external_review_packet_missing",
                )
                request_hash = invocation.get("review_request_hash")
                if request_hash and review_request_path and review_request_path.is_file():
                    if request_hash != sha256_file(review_request_path):
                        blockers.append(f"external_review_review_request_hash_mismatch:{review_id}")
                elif not request_hash:
                    blockers.append(f"external_review_invocation_missing_review_request_hash:{review_id}")
                if review_request_path and review_request_path.is_file():
                    _validate_external_lite_request_context(
                        root,
                        review_request_path,
                        lite_request_schema,
                        review_id,
                        expected_role,
                        report_run_id,
                        report_material_change_id,
                        review_report,
                        blockers,
                    )
                prompt_path = _safe_relative(report_path, root, review.get("prompt_path"))
                if is_lite_invocation and prompt_path and prompt_path.is_file():
                    _record_hash_check(
                        blockers,
                        review_id,
                        "prompt",
                        invocation.get("prompt_hash"),
                        prompt_path,
                        "external_review_prompt_path_missing",
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
            blockers.append(f"unresolved_blocking_finding:{finding_id}")
            continue

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
    if human_decision.get("path") or human_decision.get("decision_id"):
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
                human_summary["status"] = "accepted"
            elif match is None:
                blockers.append("human_decision_record_missing")
            else:
                blockers.append("human_decision_record_invalid")
    else:
        warnings.append("human_decision_missing")

    github_publication = data.get("github_publication")
    github_publication_summary: dict[str, Any] = {
        "status": "missing",
    }
    branch = data.get("branch")
    expected_pr = _positive_int(branch.get("pull_request")) if isinstance(branch, dict) else None
    expected_repository = str(branch.get("repository") or "") if isinstance(branch, dict) else ""
    if isinstance(github_publication, dict):
        status = str(github_publication.get("status", "missing"))
        required_for_merge_readiness = github_publication.get("required_for_merge_readiness") is True
        github_publication_summary = {
            "status": status,
            "required_for_merge_readiness": required_for_merge_readiness,
        }
        if not required_for_merge_readiness:
            blockers.append("github_publication_evidence_invalid")
        if status == "published":
            _validate_github_publication_result(
                root,
                report_path,
                github_publication,
                expected_pr,
                expected_repository,
                blockers,
                missing_evidence,
            )
        else:
            blockers.append("github_publication_evidence_missing")
    else:
        blockers.append("github_publication_evidence_missing")

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
        "github_publication": github_publication_summary,
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
    allowed_declared_statuses = [result["state"]]
    if result["state"] == "accepted_merge_ready":
        allowed_declared_statuses.append("awaiting_human_decision")
    if declared not in allowed_declared_statuses:
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
