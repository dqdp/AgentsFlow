from __future__ import annotations

from pathlib import Path

from .common import (
    compare_hash,
    parse_json,
    parse_yaml,
    safe_resolve,
    sha256_file,
    sha256_text,
    validate_against_schema,
)
from .gates import STRICTNESS_OVERRIDE_SOURCES, supported_workflow_strictness


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


def _find_project_root_for_run(root: Path, path: Path) -> Path | None:
    current = path.parent.resolve()
    repo_root = root.resolve()
    while True:
        if (current / ".agentsflow").is_dir():
            return current
        if current == repo_root or current.parent == current:
            return None
        current = current.parent


def validate_workflow_run_strictness(root: Path, path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    if "strictness" not in data and "strictness_source" not in data:
        return errors

    project_root = _find_project_root_for_run(root, path)
    if not project_root:
        return errors

    binding_path = safe_resolve(project_root, data.get("binding"), f"{path}: binding", errors)
    if not binding_path or not binding_path.exists():
        return errors

    binding = parse_yaml(binding_path) or {}
    if not isinstance(binding, dict):
        errors.append(f"{binding_path}: workflow binding must be a mapping")
        return errors

    extends_path = safe_resolve(root, binding.get("extends"), f"{binding_path}: extends", errors)
    if not extends_path or not extends_path.exists():
        return errors

    workflow = parse_yaml(extends_path) or {}
    if not isinstance(workflow, dict):
        errors.append(f"{extends_path}: workflow must be a mapping")
        return errors

    strictness = data.get("strictness")
    source = data.get("strictness_source")
    supported = supported_workflow_strictness(workflow)
    default = workflow.get("default_strictness")

    if source == "workflow_default" and default is not None and strictness != default:
        errors.append(
            f"{path}: strictness_source workflow_default requires strictness {default}, "
            f"got {strictness}"
        )
    if source in STRICTNESS_OVERRIDE_SOURCES:
        if supported and str(strictness) not in supported:
            errors.append(
                f"{path}: strictness {strictness} is not supported by upstream workflow "
                f"{workflow.get('name', data.get('workflow'))}"
            )
        if not supported:
            errors.append(
                f"{path}: strictness override requires upstream workflow supported_profiles.strictness"
            )
    return errors


def validate_workflow_run_artifact(root: Path, path: Path) -> list[str]:
    schema = parse_json(root / "schemas" / "workflow-run.schema.json")
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"{path}: workflow run metadata must be a mapping"]
    errors = validate_against_schema(path, data, schema)
    errors.extend(validate_workflow_run_strictness(root, path, data))
    errors.extend(validate_workflow_run_phase_guard(path, data))
    return errors
