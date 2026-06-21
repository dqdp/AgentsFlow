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
) -> None:
    reviewer = str(assignment["reviewer"])
    model_family = str(assignment["model_family"])
    report_path = resolve_path(assignment["report_path"], root)
    entry["checked_at"] = now_utc()
    if not report_path.exists() and wait_seconds > 0:
        entry["status"] = "waiting-for-report"
        deadline = dt.datetime.now(dt.timezone.utc).timestamp() + wait_seconds
        while not report_path.exists() and dt.datetime.now(dt.timezone.utc).timestamp() < deadline:
            time.sleep(0.25)
        entry["checked_at"] = now_utc()
    if not report_path.exists():
        raise ValueError(f"internal reviewer report is missing for {reviewer}: {report_path}")
    report = validate_report(report_path, root)
    validate_report_identity(report, reviewer, report_path)
    report_model = str(((report.get("reviewer") or {}).get("model") or ""))
    if require_model_diversity:
        if not report_model:
            raise ValueError(f"internal reviewer report model is required for {reviewer}")
        if report_model != model_family:
            raise ValueError(f"internal reviewer report model must match assignment model_family for {reviewer}")
        entry["evidence_model_family"] = report_model
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
) -> dict[str, Any]:
    raw_output_path = resolve_path(assignment["raw_output_path"], root)
    invocation_path = resolve_path(assignment["invocation_metadata_path"], root)
    entry["raw_output_path"] = str(raw_output_path)
    entry["invocation_metadata_path"] = str(invocation_path)
    entry["status"] = "running"
    entry["dispatch_started_at"] = now_utc()
    cmd = build_external_command(assignment, root, mock_responses)
    dispatch_started_monotonic = time.monotonic()
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
            if process.poll() is None and timeout_seconds > 0 and elapsed < timeout_seconds:
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
                errors.append(message)
                pending.remove(run)
                progress = True
                continue
            try:
                finish_external_assignment(run, root, require_model_diversity)
            except Exception as exc:  # noqa: BLE001
                if entry.get("status") == "running":
                    entry["status"] = "failed"
                entry["error"] = str(exc)
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
    args = parser.parse_args()

    root = Path.cwd()
    contract_path = Path(args.contract)
    output_path = Path(args.output)
    started = now_utc()
    mock_responses = parse_mock_responses(args.mock_response)
    reviewers: list[dict[str, Any]] = []
    external_runs: list[dict[str, Any]] = []
    status = "completed"

    try:
        contract = load_yaml(contract_path)
        assignments = contract.get("reviewer_assignments", []) or []
        if not isinstance(assignments, list) or not assignments:
            raise ValueError("review prompt contract must declare reviewer_assignments")
        validate_assignments(assignments, contract)
        artifact_preparation_report = validate_invocation_set_output_path(contract, output_path, root)
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
                external_runs.append(start_external_assignment(assignment, entry, root, mock_responses))
        for assignment, entry in internal_runs:
            validate_internal_assignment(
                assignment,
                entry,
                root,
                require_model_diversity,
                max(0.0, args.internal_report_wait_seconds),
            )
        external_errors = collect_external_assignments(
            external_runs,
            root,
            require_model_diversity,
            max(0.0, args.external_reviewer_timeout_seconds),
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
    output_path.write_text(
        json.dumps(completed_output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Review invocation set written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
