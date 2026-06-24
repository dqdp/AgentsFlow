#!/usr/bin/env python3
"""Run a review set from reviewer assignments.

This is a small dispatcher, not a generic provider runtime:
- internal-agent assignments must already have a reviewer report artifact;
- claude-code assignments are invoked through run_external_reviewer.py;
- every output remains normalized reviewer-report plus invocation evidence.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml


SUPPORTED_PROVIDERS = {"internal-agent", "claude-code"}


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def provider_models_include_family(provider_models: object, model_family: str) -> bool:
    family = str(model_family).lower()
    if not family or not isinstance(provider_models, list):
        return False
    return any(family in str(model).lower() for model in provider_models)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def resolve_path(ref: object, root: Path) -> Path:
    path = Path(str(ref))
    if path.is_absolute():
        return path
    return root / path


def concrete_hash(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(char in "0123456789abcdef" for char in digest)


def validate_report(path: Path, root: Path) -> dict[str, Any]:
    report = load_json(path)
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("jsonschema is required for review-set validation") from exc
    schema = load_json(root / "schemas" / "reviewer-report.schema.json")
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(report), key=lambda err: list(err.path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "<root>"
        raise ValueError(f"{path}: reviewer report schema validation failed at {location}: {first.message}")
    return report


def validate_report_identity(report: dict[str, Any], reviewer: str, path: Path) -> None:
    report_reviewer = report.get("reviewer", {}) or {}
    reviewer_id = str(report_reviewer.get("id") or "") if isinstance(report_reviewer, dict) else ""
    if reviewer not in reviewer_id:
        raise ValueError(f"{path}: reviewer.id must include assigned reviewer {reviewer}")


def validate_report_review_context(
    report: dict[str, Any],
    packet: dict[str, Any],
    packet_path: Path,
    reviewer: str,
    report_path: Path,
    root: Path,
) -> None:
    context = report.get("review_context")
    if not isinstance(context, dict):
        raise ValueError(f"{report_path}: review_context is required for {reviewer}")
    expected_run_id = str(packet.get("run_id") or "")
    if expected_run_id and context.get("run_id") != expected_run_id:
        raise ValueError(f"{report_path}: review_context.run_id must match packet for {reviewer}")
    expected_material_change = str(packet.get("material_change_id") or "")
    if expected_material_change and context.get("material_change_id") != expected_material_change:
        raise ValueError(f"{report_path}: review_context.material_change_id must match packet for {reviewer}")
    expected_packet_ref = str(packet.get("review_packet_path") or packet_path.resolve().relative_to(root.resolve()).as_posix())
    if context.get("review_packet_path") != expected_packet_ref:
        raise ValueError(f"{report_path}: review_context.review_packet_path must match assignment for {reviewer}")
    if context.get("reviewer_instance_id") != reviewer:
        raise ValueError(f"{report_path}: review_context.reviewer_instance_id must match assignment for {reviewer}")


def parse_mock_responses(values: list[str]) -> dict[str, Path]:
    responses: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--mock-response must use reviewer=path")
        reviewer, path = value.split("=", 1)
        if not reviewer or not path:
            raise ValueError("--mock-response must use reviewer=path")
        responses[reviewer] = Path(path)
    return responses


def validate_assignments(assignments: list[dict[str, Any]], contract: dict[str, Any]) -> None:
    reviewers = {
        str(item.get("instance_id"))
        for item in contract.get("reviewer_set", []) or []
        if isinstance(item, dict) and item.get("instance_id")
    }
    assigned = [str(item.get("reviewer", "")) for item in assignments]
    if sorted(assigned) != sorted(reviewers):
        raise ValueError("reviewer_assignments must cover reviewer_set exactly")
    if len(assigned) != len(set(assigned)):
        raise ValueError("reviewer_assignments reviewers must be unique")
    report_paths = [str(resolve_path(item.get("report_path"), Path.cwd()).resolve()) for item in assignments if item.get("report_path")]
    if len(report_paths) != len(set(report_paths)):
        raise ValueError("reviewer_assignments report_path values must be unique")

    provider_policy = contract.get("provider_policy", {}) or {}
    provider_model_families = {
        f"{assignment.get('provider')}/{assignment.get('model_family')}"
        for assignment in assignments
    }
    if provider_policy.get("allow_external_reviewers") is False:
        external = [item.get("reviewer") for item in assignments if item.get("provider") != "internal-agent"]
        if external:
            raise ValueError("provider_policy disallows external reviewers but has external assignments")
    if provider_policy.get("require_model_diversity") is True:
        minimum = int(provider_policy.get("min_distinct_provider_model_families", 2))
        if len(provider_model_families) < minimum:
            raise ValueError("model diversity requirement is not satisfied by reviewer_assignments")

    for assignment in assignments:
        provider = str(assignment.get("provider", ""))
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"unsupported review provider: {provider}")
        for key in ["reviewer", "model_family", "packet_path", "report_path"]:
            if not assignment.get(key):
                raise ValueError(f"reviewer assignment missing {key}: {assignment}")
        if provider == "claude-code":
            for key in ["provider_config", "raw_output_path", "invocation_metadata_path"]:
                if not assignment.get(key):
                    raise ValueError(f"claude-code reviewer assignment missing {key}: {assignment}")


def validate_invocation_set_output_path(contract: dict[str, Any], output_path: Path, root: Path) -> Path | None:
    inputs = contract.get("inputs", {}) or {}
    invocation_set = inputs.get("review_invocation_set")
    if not invocation_set:
        raise ValueError("reviewer_assignments require inputs.review_invocation_set path")
    evidence_report = inputs.get("evidence_report")
    if evidence_report and resolve_path(evidence_report, root).resolve() == resolve_path(invocation_set, root).resolve():
        raise ValueError("inputs.evidence_report must not match inputs.review_invocation_set")
    artifact_preparation_report: Path | None = None
    if contract.get("artifact_scope", "run") == "run":
        preparation_ref = inputs.get("artifact_preparation_report")
        if not preparation_ref:
            raise ValueError("run reviewer_assignments require inputs.artifact_preparation_report path")
        artifact_preparation_report = resolve_path(preparation_ref, root)
        if not artifact_preparation_report.is_file():
            raise ValueError(
                "run reviewer_assignments require existing inputs.artifact_preparation_report: "
                f"{artifact_preparation_report}"
            )
    expected_output = resolve_path(invocation_set, root).resolve()
    if output_path.resolve() != expected_output:
        raise ValueError("--output must match inputs.review_invocation_set path")
    return artifact_preparation_report


def expected_assignment_fingerprint(
    contract: dict[str, Any],
    assignment: dict[str, Any],
    contract_path: Path,
    root: Path,
    forbidden_env_fingerprint: str,
) -> dict[str, str] | None:
    reviewer = str(assignment.get("reviewer") or "")
    reviewers = {
        str(item.get("instance_id")): item
        for item in contract.get("reviewer_set", []) or []
        if isinstance(item, dict) and item.get("instance_id")
    }
    rendered_prompts = {
        str(item.get("reviewer")): item
        for item in contract.get("rendered_prompts", []) or []
        if isinstance(item, dict) and item.get("reviewer")
    }
    reviewer_def = reviewers.get(reviewer, {}) or {}
    rendered_prompt = rendered_prompts.get(reviewer, {}) or {}
    role_ref = reviewer_def.get("role_contract")
    if not role_ref or not assignment.get("provider_config"):
        return None
    config_path = resolve_path(assignment.get("provider_config"), root)
    role_path = resolve_path(role_ref, root)
    config = load_yaml(config_path)
    execution = config.get("execution", {}) or {}
    rubric_hash = rendered_prompt.get("rubric_hash")
    if not concrete_hash(rubric_hash):
        rubric_hash = sha256_text(json.dumps(contract.get("prompt_policy", {}) or {}, sort_keys=True))
    return {
        "reviewer": reviewer,
        "provider_config_hash": sha256_file(config_path),
        "wrapper_hash": sha256_file(root / "scripts" / "reviewers" / "run_external_reviewer.py"),
        "schema_hash": sha256_file(root / "schemas" / "reviewer-report.schema.json"),
        "prompt_contract_hash": sha256_file(resolve_path(contract_path, root)),
        "role_contract_hash": sha256_file(role_path),
        "rubric_hash": str(rubric_hash),
        "forbidden_env_fingerprint": forbidden_env_fingerprint,
        "permission_mode": str(execution.get("permission_mode")),
        "sandbox_mode": str(execution.get("sandbox_mode")),
        "provider_transport_mode": str(execution.get("prompt_transport", "stdin")),
    }


def validate_assignment_fingerprints(
    preflight: dict[str, Any],
    contract: dict[str, Any],
    contract_path: Path,
    root: Path,
    external_assignments: list[dict[str, Any]],
    preflight_path: Path,
) -> None:
    forbidden_payload = preflight.get("forbidden_env", {}) or {}
    forbidden_env_fingerprint = sha256_text(json.dumps(forbidden_payload, sort_keys=True))
    expected_by_reviewer: dict[str, dict[str, str]] = {}
    for assignment in external_assignments:
        expected = expected_assignment_fingerprint(
            contract,
            assignment,
            contract_path,
            root,
            forbidden_env_fingerprint,
        )
        if expected:
            expected_by_reviewer[expected["reviewer"]] = expected
    if not expected_by_reviewer:
        return
    declared_items = preflight.get("assignment_fingerprints")
    if not isinstance(declared_items, list) or not declared_items:
        raise ValueError(f"{preflight_path}: assignment_fingerprints are required for prepared claude-code assignments")
    declared_by_reviewer = {
        str(item.get("reviewer")): item
        for item in declared_items
        if isinstance(item, dict) and item.get("reviewer")
    }
    missing = sorted(set(expected_by_reviewer) - set(declared_by_reviewer))
    if missing:
        raise ValueError(
            f"{preflight_path}: assignment_fingerprints missing reviewer(s): {', '.join(missing)}"
        )
    for reviewer, expected in expected_by_reviewer.items():
        declared = declared_by_reviewer[reviewer]
        for key, expected_value in expected.items():
            declared_value = declared.get(key)
            if key.endswith("_hash") or key == "forbidden_env_fingerprint":
                if not concrete_hash(declared_value):
                    raise ValueError(f"{preflight_path}: assignment_fingerprints[{reviewer}].{key} must be concrete sha256")
            if declared_value != expected_value:
                raise ValueError(
                    f"{preflight_path}: assignment_fingerprints[{reviewer}].{key} must match current review artifact"
                )


def validate_external_reviewer_preflight(
    contract: dict[str, Any],
    contract_path: Path,
    root: Path,
    assignments: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    external_assignments = [item for item in assignments if item.get("provider") == "claude-code"]
    if not external_assignments:
        return None, None
    inputs = contract.get("inputs", {}) or {}
    preflight_ref = inputs.get("external_reviewer_preflight")
    if not preflight_ref:
        raise ValueError("claude-code reviewer assignments require inputs.external_reviewer_preflight")
    preflight_path = resolve_path(preflight_ref, root)
    if not preflight_path.is_file():
        raise ValueError(f"inputs.external_reviewer_preflight must be an existing file: {preflight_ref}")
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("jsonschema is required for external reviewer preflight validation") from exc
    preflight = load_json(preflight_path)
    schema = load_json(root / "schemas" / "external-reviewer-preflight.schema.json")
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(preflight), key=lambda err: list(err.path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "<root>"
        raise ValueError(f"{preflight_path}: external reviewer preflight schema validation failed at {location}: {first.message}")
    if preflight.get("result") != "pass":
        blockers = preflight.get("blockers") or []
        raise ValueError(f"{preflight_path}: external reviewer preflight must pass before dispatch: {blockers}")
    fingerprint = preflight.get("fingerprint", {}) or {}
    contract_hash = sha256_file(resolve_path(contract_path, root))
    if fingerprint.get("prompt_contract_hash") != contract_hash:
        raise ValueError(f"{preflight_path}: prompt_contract_hash must match current review prompt contract")
    wrapper_path = root / "scripts" / "reviewers" / "run_external_reviewer.py"
    if wrapper_path.is_file() and fingerprint.get("wrapper_hash") != sha256_file(wrapper_path):
        raise ValueError(f"{preflight_path}: wrapper_hash must match current external reviewer wrapper")
    schema_path = root / "schemas" / "reviewer-report.schema.json"
    if schema_path.is_file() and fingerprint.get("schema_hash") != sha256_file(schema_path):
        raise ValueError(f"{preflight_path}: schema_hash must match current reviewer report schema")
    declared_config_hash = fingerprint.get("provider_config_hash")
    for assignment in external_assignments:
        config_path = resolve_path(assignment.get("provider_config"), root)
        if declared_config_hash != sha256_file(config_path):
            reviewer = assignment.get("reviewer")
            raise ValueError(f"{preflight_path}: provider_config_hash must match assignment provider_config for {reviewer}")
    validate_assignment_fingerprints(
        preflight,
        contract,
        contract_path,
        root,
        external_assignments,
        preflight_path,
    )
    return str(preflight_ref), sha256_file(preflight_path)


def require_hash_match(path: Path, label: str, declared: object, artifact_path: Path) -> None:
    if not isinstance(declared, str) or not declared.startswith("sha256:"):
        raise ValueError(f"{path}: {label} hash is required")
    digest = declared.removeprefix("sha256:")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError(f"{path}: {label} hash must be a concrete sha256")
    actual = sha256_file(artifact_path)
    if declared != actual:
        raise ValueError(f"{path}: {label} hash must match current artifact")


def resolve_prepared_artifact_path(preparation_path: Path, ref: object, root: Path, label: str) -> Path:
    if not ref:
        raise ValueError(f"{preparation_path}: {label} path is required")
    path = resolve_path(ref, root)
    if not path.is_file():
        raise ValueError(f"{preparation_path}: {label} must be an existing file: {ref}")
    return path


def validate_preparation_artifact(
    preparation_path: Path,
    contract_path: Path,
    root: Path,
    contract: dict[str, Any],
    output_path: Path,
) -> str:
    preparation = load_json(preparation_path)
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("jsonschema is required for review-set validation") from exc
    schema = load_json(root / "schemas" / "review-artifact-preparation.schema.json")
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(preparation), key=lambda err: list(err.path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "<root>"
        raise ValueError(f"{preparation_path}: preparation artifact schema validation failed at {location}: {first.message}")
    if preparation.get("status") != "completed":
        raise ValueError(f"{preparation_path}: preparation artifact status must be completed")
    prompt_contract = preparation.get("review_prompt_contract", {}) or {}
    prepared_contract_ref = prompt_contract.get("path")
    if not prepared_contract_ref:
        raise ValueError(f"{preparation_path}: review_prompt_contract.path is required")
    prepared_contract_path = resolve_path(prepared_contract_ref, root).resolve()
    if prepared_contract_path != contract_path.resolve():
        raise ValueError(f"{preparation_path}: review_prompt_contract.path must match --contract")
    prepared_contract_hash = prompt_contract.get("hash")
    require_hash_match(preparation_path, "review_prompt_contract", prepared_contract_hash, contract_path)

    inputs = contract.get("inputs", {}) or {}
    assignments = {
        str(item.get("reviewer")): item
        for item in contract.get("reviewer_assignments", []) or []
        if isinstance(item, dict) and item.get("reviewer")
    }
    reviewers = {
        str(item.get("instance_id"))
        for item in contract.get("reviewer_set", []) or []
        if isinstance(item, dict) and item.get("instance_id")
    }
    assigned_reviewers = set(assignments)
    if reviewers and assigned_reviewers != reviewers:
        raise ValueError(f"{preparation_path}: reviewer_assignments must cover reviewer_set exactly")

    prep_assignments = {
        str(item.get("reviewer")): item
        for item in preparation.get("reviewer_assignments", []) or []
        if isinstance(item, dict) and item.get("reviewer")
    }
    if set(prep_assignments) != assigned_reviewers:
        raise ValueError(f"{preparation_path}: reviewer_assignments must cover reviewer_set exactly")
    for reviewer, assignment in assignments.items():
        prepared_assignment = prep_assignments[reviewer]
        for key in ["provider", "model_family", "packet_path", "report_path"]:
            if str(prepared_assignment.get(key)) != str(assignment.get(key)):
                raise ValueError(f"{preparation_path}: reviewer_assignments[{reviewer}].{key} must match contract")

    generated = preparation.get("generated_artifacts", {}) or {}
    prep_invocation = generated.get("review_invocation_set", {}) or {}
    if not prep_invocation.get("path"):
        raise ValueError(f"{preparation_path}: generated_artifacts.review_invocation_set.path is required")
    prep_invocation_path = resolve_path(prep_invocation.get("path"), root).resolve()
    if prep_invocation_path != output_path.resolve():
        raise ValueError(f"{preparation_path}: generated_artifacts.review_invocation_set.path must match --output")

    packet_paths = {
        str(item.get("reviewer")): resolve_path(item.get("path"), root)
        for item in inputs.get("review_packets", []) or []
        if isinstance(item, dict) and item.get("reviewer") and item.get("path")
    }
    for reviewer, assignment in assignments.items():
        packet_paths.setdefault(reviewer, resolve_path(assignment.get("packet_path"), root))
    prep_packets = {
        str(item.get("reviewer")): item
        for item in generated.get("review_packets", []) or []
        if isinstance(item, dict) and item.get("reviewer")
    }
    if set(prep_packets) != assigned_reviewers:
        raise ValueError(f"{preparation_path}: generated review_packets must cover reviewer_set exactly")
    for reviewer, packet_entry in prep_packets.items():
        prepared_packet_path = resolve_prepared_artifact_path(
            preparation_path,
            packet_entry.get("path"),
            root,
            f"generated_artifacts.review_packets[{reviewer}]",
        )
        expected_packet_path = packet_paths[reviewer].resolve()
        if prepared_packet_path.resolve() != expected_packet_path:
            raise ValueError(f"{preparation_path}: review packet path must match contract for {reviewer}")
        require_hash_match(preparation_path, f"review packet for {reviewer}", packet_entry.get("hash"), expected_packet_path)

    prompt_paths = {
        str(item.get("reviewer")): resolve_path(item.get("prompt_path"), root)
        for item in contract.get("rendered_prompts", []) or []
        if isinstance(item, dict) and item.get("reviewer") and item.get("prompt_path")
    }
    prep_prompts = {
        str(item.get("reviewer")): item
        for item in generated.get("rendered_prompts", []) or []
        if isinstance(item, dict) and item.get("reviewer")
    }
    if prompt_paths and set(prep_prompts) != assigned_reviewers:
        raise ValueError(f"{preparation_path}: generated rendered_prompts must cover reviewer_set exactly")
    for reviewer, prompt_entry in prep_prompts.items():
        prepared_prompt_path = resolve_prepared_artifact_path(
            preparation_path,
            prompt_entry.get("path"),
            root,
            f"generated_artifacts.rendered_prompts[{reviewer}]",
        )
        if reviewer in prompt_paths and prepared_prompt_path.resolve() != prompt_paths[reviewer].resolve():
            raise ValueError(f"{preparation_path}: rendered prompt path must match contract for {reviewer}")
        require_hash_match(preparation_path, f"rendered prompt for {reviewer}", prompt_entry.get("hash"), prepared_prompt_path)

    for idx, artifact in enumerate(preparation.get("input_artifacts", []) or []):
        if not isinstance(artifact, dict):
            continue
        artifact_path = resolve_prepared_artifact_path(
            preparation_path,
            artifact.get("path"),
            root,
            f"input_artifacts[{idx}]",
        )
        require_hash_match(preparation_path, f"input_artifacts[{idx}]", artifact.get("hash"), artifact_path)
    return sha256_file(preparation_path)


def build_entry(assignment: dict[str, Any], root: Path) -> dict[str, Any]:
    report_path = resolve_path(assignment["report_path"], root)
    return {
        "reviewer": str(assignment["reviewer"]),
        "provider": str(assignment["provider"]),
        "model_family": str(assignment["model_family"]),
        "packet_path": str(resolve_path(assignment["packet_path"], root)),
        "report_path": str(report_path),
    }


def validate_internal_assignment(
    assignment: dict[str, Any],
    entry: dict[str, Any],
    root: Path,
    require_model_diversity: bool,
    wait_seconds: float,
    progress_interval_seconds: float,
) -> None:
    reviewer = str(assignment["reviewer"])
    model_family = str(assignment["model_family"])
    report_path = resolve_path(assignment["report_path"], root)
    entry["checked_at"] = now_utc()
    if not report_path.exists() and wait_seconds > 0:
        entry["status"] = "waiting-for-report"
        deadline = dt.datetime.now(dt.timezone.utc).timestamp() + wait_seconds
        last_progress = time.monotonic()
        while not report_path.exists() and dt.datetime.now(dt.timezone.utc).timestamp() < deadline:
            now = time.monotonic()
            if progress_interval_seconds > 0 and now - last_progress >= progress_interval_seconds:
                print(
                    f"review-set progress: waiting for internal reviewer {reviewer} report",
                    file=sys.stderr,
                    flush=True,
                )
                last_progress = now
            time.sleep(0.25)
        entry["checked_at"] = now_utc()
    if not report_path.exists():
        raise ValueError(f"internal reviewer report is missing for {reviewer}: {report_path}")
    report = validate_report(report_path, root)
    validate_report_identity(report, reviewer, report_path)
    packet_path = resolve_path(assignment["packet_path"], root)
    packet = load_json(packet_path)
    validate_report_review_context(report, packet, packet_path, reviewer, report_path, root)
    report_model = str(((report.get("reviewer") or {}).get("model") or ""))
    if require_model_diversity:
        if not report_model:
            raise ValueError(f"internal reviewer report model is required for {reviewer}")
        if report_model != model_family and model_family.lower() not in report_model.lower():
            raise ValueError(f"internal reviewer report model must match assignment model_family for {reviewer}")
        entry["evidence_model_family"] = model_family
    entry["status"] = "report-present"


def build_external_command(
    assignment: dict[str, Any],
    root: Path,
    mock_responses: dict[str, Path],
) -> list[str]:
    reviewer = str(assignment["reviewer"])
    cmd = [
        sys.executable,
        str(root / "scripts" / "reviewers" / "run_external_reviewer.py"),
        "--provider",
        "claude-code",
        "--config",
        str(resolve_path(assignment["provider_config"], root)),
        "--input",
        str(resolve_path(assignment["packet_path"], root)),
        "--output",
        str(resolve_path(assignment["report_path"], root)),
        "--raw-output",
        str(resolve_path(assignment["raw_output_path"], root)),
        "--invocation-output",
        str(resolve_path(assignment["invocation_metadata_path"], root)),
    ]
    if reviewer in mock_responses:
        cmd.extend(["--mock-response", str(resolve_path(mock_responses[reviewer], root))])
    return cmd


def start_external_assignment(
    assignment: dict[str, Any],
    entry: dict[str, Any],
    root: Path,
    mock_responses: dict[str, Path],
    progress_interval_seconds: float,
) -> dict[str, Any]:
    raw_output_path = resolve_path(assignment["raw_output_path"], root)
    invocation_path = resolve_path(assignment["invocation_metadata_path"], root)
    entry["raw_output_path"] = str(raw_output_path)
    entry["invocation_metadata_path"] = str(invocation_path)
    entry["status"] = "running"
    entry["dispatch_started_at"] = now_utc()
    cmd = build_external_command(assignment, root, mock_responses)
    dispatch_started_monotonic = time.monotonic()
    if progress_interval_seconds > 0:
        print(
            f"review-set progress: dispatched external reviewer {assignment['reviewer']}",
            file=sys.stderr,
            flush=True,
        )
    process = subprocess.Popen(  # noqa: S603
        cmd,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return {
        "assignment": assignment,
        "entry": entry,
        "process": process,
        "raw_output_path": raw_output_path,
        "invocation_path": invocation_path,
        "dispatch_started_monotonic": dispatch_started_monotonic,
        "last_progress_monotonic": dispatch_started_monotonic,
    }


def finish_external_assignment(
    run: dict[str, Any],
    root: Path,
    require_model_diversity: bool,
) -> None:
    assignment = run["assignment"]
    entry = run["entry"]
    process = run["process"]
    reviewer = str(assignment["reviewer"])
    model_family = str(assignment["model_family"])
    report_path = resolve_path(assignment["report_path"], root)
    raw_output_path = run["raw_output_path"]
    invocation_path = run["invocation_path"]

    stdout, stderr = process.communicate()
    entry["dispatch_finished_at"] = now_utc()
    entry["stdout"] = stdout
    entry["stderr"] = stderr
    entry["exit_code"] = process.returncode
    if process.returncode != 0:
        entry["status"] = "failed"
        entry["error"] = f"external reviewer {reviewer} failed"
        raise RuntimeError(f"external reviewer {reviewer} failed: {stdout}{stderr}")
    report = validate_report(report_path, root)
    validate_report_identity(report, reviewer, report_path)
    if invocation_path.exists():
        invocation = load_json(invocation_path)
        for key in [
            "requested_model",
            "requested_effort",
            "execution_mode",
            "provider_models_used",
            "provider_total_cost_usd",
            "provider_service_tier",
            "provider_speed",
            "raw_output_path",
            "raw_output_hash",
            "normalized_output_hash",
        ]:
            if key in invocation:
                entry[key] = invocation[key]
        requested_model = str(invocation.get("requested_model") or "")
        if require_model_diversity:
            if not requested_model:
                raise ValueError(f"external reviewer requested_model is required for {reviewer}")
            if requested_model != model_family:
                raise ValueError(f"external reviewer requested_model must match assignment model_family for {reviewer}")
            if not provider_models_include_family(invocation.get("provider_models_used"), model_family):
                raise ValueError(
                    f"external reviewer provider_models_used must include assignment model_family for {reviewer}"
                )
            entry["evidence_model_family"] = requested_model
    elif require_model_diversity:
        raise ValueError(f"external reviewer invocation metadata is required for {reviewer}")
    entry["status"] = "invoked"


def collect_external_assignments(
    external_runs: list[dict[str, Any]],
    root: Path,
    require_model_diversity: bool,
    timeout_seconds: float,
    progress_interval_seconds: float,
) -> list[str]:
    errors: list[str] = []
    pending = [run for run in external_runs if run["entry"].get("status") == "running"]
    while pending:
        progress = False
        now = time.monotonic()
        for run in list(pending):
            process = run["process"]
            entry = run["entry"]
            reviewer = str(run["assignment"]["reviewer"])
            elapsed = now - float(run["dispatch_started_monotonic"])
            last_progress = float(run.get("last_progress_monotonic", run["dispatch_started_monotonic"]))
            if process.poll() is None and timeout_seconds > 0 and elapsed < timeout_seconds:
                if progress_interval_seconds > 0 and now - last_progress >= progress_interval_seconds:
                    entry["last_progress_at"] = now_utc()
                    print(
                        f"review-set progress: external reviewer {reviewer} still running after {elapsed:.0f}s",
                        file=sys.stderr,
                        flush=True,
                    )
                    run["last_progress_monotonic"] = now
                continue
            if process.poll() is None:
                process.kill()
                stdout, stderr = process.communicate()
                message = f"external reviewer {reviewer} timed out after {timeout_seconds:g} seconds"
                entry["stdout"] = stdout
                entry["stderr"] = stderr
                entry["status"] = "timed-out"
                entry["error"] = message
                entry["dispatch_finished_at"] = now_utc()
                if progress_interval_seconds > 0:
                    print(f"review-set progress: {message}", file=sys.stderr, flush=True)
                errors.append(message)
                pending.remove(run)
                progress = True
                continue
            try:
                finish_external_assignment(run, root, require_model_diversity)
                if progress_interval_seconds > 0:
                    print(
                        f"review-set progress: external reviewer {reviewer} completed",
                        file=sys.stderr,
                        flush=True,
                    )
            except Exception as exc:  # noqa: BLE001
                if entry.get("status") == "running":
                    entry["status"] = "failed"
                entry["error"] = str(exc)
                if progress_interval_seconds > 0:
                    print(
                        f"review-set progress: external reviewer {reviewer} failed: {exc}",
                        file=sys.stderr,
                        flush=True,
                    )
                errors.append(str(exc))
            pending.remove(run)
            progress = True
        if pending and not progress:
            time.sleep(0.25)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, help="review-prompt-contract.yaml")
    parser.add_argument("--output", required=True, help="review invocation set JSON")
    parser.add_argument(
        "--mock-response",
        action="append",
        default=[],
        help="Mock external provider response as reviewer=path.",
    )
    parser.add_argument(
        "--internal-report-wait-seconds",
        type=float,
        default=0.0,
        help="Seconds to wait for internal-agent report-present artifacts after external reviewers are dispatched.",
    )
    parser.add_argument(
        "--external-reviewer-timeout-seconds",
        type=float,
        default=900.0,
        help="Per external reviewer timeout after dispatch. Timed-out reviewers are killed and recorded as evidence.",
    )
    parser.add_argument(
        "--progress-interval-seconds",
        type=float,
        default=30.0,
        help="Emit external reviewer progress heartbeat lines to stderr at this interval. Use 0 to disable.",
    )
    args = parser.parse_args()

    root = Path.cwd()
    contract_path = Path(args.contract)
    output_path = Path(args.output)
    started = now_utc()
    mock_responses = parse_mock_responses(args.mock_response)
    reviewers: list[dict[str, Any]] = []
    external_runs: list[dict[str, Any]] = []
    external_preflight_ref: str | None = None
    external_preflight_hash: str | None = None
    status = "completed"

    try:
        contract = load_yaml(contract_path)
        assignments = contract.get("reviewer_assignments", []) or []
        if not isinstance(assignments, list) or not assignments:
            raise ValueError("review prompt contract must declare reviewer_assignments")
        validate_assignments(assignments, contract)
        artifact_preparation_report = validate_invocation_set_output_path(contract, output_path, root)
        external_preflight_ref, external_preflight_hash = validate_external_reviewer_preflight(
            contract,
            contract_path,
            root,
            assignments,
        )
        artifact_preparation_report_hash: str | None = None
        if artifact_preparation_report:
            artifact_preparation_report_hash = validate_preparation_artifact(
                artifact_preparation_report,
                resolve_path(contract_path, root),
                root,
                contract,
                output_path,
            )
        require_model_diversity = (contract.get("provider_policy", {}) or {}).get("require_model_diversity") is True
        internal_runs: list[tuple[dict[str, Any], dict[str, Any]]] = []

        for assignment in assignments:
            provider = str(assignment["provider"])
            entry = build_entry(assignment, root)
            reviewers.append(entry)
            if provider == "internal-agent":
                internal_runs.append((assignment, entry))
            elif provider == "claude-code":
                external_runs.append(
                    start_external_assignment(
                        assignment,
                        entry,
                        root,
                        mock_responses,
                        max(0.0, args.progress_interval_seconds),
                    )
                )
        for assignment, entry in internal_runs:
            validate_internal_assignment(
                assignment,
                entry,
                root,
                require_model_diversity,
                max(0.0, args.internal_report_wait_seconds),
                max(0.0, args.progress_interval_seconds),
            )
        external_errors = collect_external_assignments(
            external_runs,
            root,
            require_model_diversity,
            max(0.0, args.external_reviewer_timeout_seconds),
            max(0.0, args.progress_interval_seconds),
        )
        if external_errors:
            raise RuntimeError("; ".join(external_errors))
    except Exception as exc:  # noqa: BLE001
        status = "failed"
        if external_runs:
            collection_errors = collect_external_assignments(
                external_runs,
                root,
                locals().get("require_model_diversity", False),
                max(0.0, args.external_reviewer_timeout_seconds),
                max(0.0, args.progress_interval_seconds),
            )
            if collection_errors:
                exc = RuntimeError(f"{exc}; external collection errors: {'; '.join(collection_errors)}")
        for entry in reviewers:
            if not entry.get("status"):
                entry["status"] = "failed"
                entry["error"] = str(exc)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        failed_output = {
            "artifact_kind": "review_invocation_set",
            "review_prompt_contract": str(contract_path),
            "status": status,
            "started_at": started,
            "finished_at": now_utc(),
            "runner_scheduling": "external-first-async",
            "provider_model_families": [],
            "reviewers": reviewers,
            "error": str(exc),
        }
        artifact_preparation_report = (contract.get("inputs", {}) or {}).get("artifact_preparation_report") if "contract" in locals() else None
        if artifact_preparation_report:
            failed_output["artifact_preparation_report"] = str(artifact_preparation_report)
        if "artifact_preparation_report_hash" in locals() and artifact_preparation_report_hash:
            failed_output["artifact_preparation_report_hash"] = artifact_preparation_report_hash
        if external_preflight_ref:
            failed_output["external_reviewer_preflight"] = external_preflight_ref
        if external_preflight_hash:
            failed_output["external_reviewer_preflight_hash"] = external_preflight_hash
        output_path.write_text(
            json.dumps(failed_output, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"review set failed: {exc}", file=sys.stderr)
        return 2

    provider_model_families = sorted(
        {
            f"{entry['provider']}/{entry.get('evidence_model_family') or entry['model_family']}"
            for entry in reviewers
            if entry.get("provider") and entry.get("model_family")
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    completed_output = {
        "artifact_kind": "review_invocation_set",
        "review_prompt_contract": str(contract_path),
        "status": status,
        "started_at": started,
        "finished_at": now_utc(),
        "runner_scheduling": "external-first-async",
        "provider_model_families": provider_model_families,
        "reviewers": reviewers,
    }
    artifact_preparation_report = (contract.get("inputs", {}) or {}).get("artifact_preparation_report")
    if artifact_preparation_report:
        completed_output["artifact_preparation_report"] = str(artifact_preparation_report)
    if "artifact_preparation_report_hash" in locals() and artifact_preparation_report_hash:
        completed_output["artifact_preparation_report_hash"] = artifact_preparation_report_hash
    if external_preflight_ref:
        completed_output["external_reviewer_preflight"] = external_preflight_ref
    if external_preflight_hash:
        completed_output["external_reviewer_preflight_hash"] = external_preflight_hash
    output_path.write_text(
        json.dumps(completed_output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Review invocation set written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
