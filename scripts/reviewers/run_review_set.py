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
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = SCRIPT_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from repo_validation.common import parse_json_mapping as load_json  # noqa: E402
from repo_validation.common import parse_yaml_mapping as load_yaml  # noqa: E402
from repo_validation.common import provider_models_include_family  # noqa: E402
from repo_validation.common import raise_schema_validation_error  # noqa: E402
from repo_validation.common import sha256_file  # noqa: E402

SUPPORTED_PROVIDERS = {"internal-agent", "claude-code"}


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def resolve_path(ref: object, root: Path) -> Path:
    path = Path(str(ref))
    if path.is_absolute():
        return path
    return root / path


def validate_report(path: Path, root: Path) -> dict[str, Any]:
    report = load_json(path)
    raise_schema_validation_error(
        report,
        load_json(root / "schemas" / "reviewer-report.schema.json"),
        f"{path}: reviewer report",
    )
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


def validate_invocation_set_output_path(contract: dict[str, Any], output_path: Path, root: Path) -> None:
    inputs = contract.get("inputs", {}) or {}
    invocation_set = inputs.get("review_invocation_set")
    if not invocation_set:
        raise ValueError("reviewer_assignments require inputs.review_invocation_set path")
    evidence_report = inputs.get("evidence_report")
    if evidence_report and resolve_path(evidence_report, root).resolve() == resolve_path(invocation_set, root).resolve():
        raise ValueError("inputs.evidence_report must not match inputs.review_invocation_set")
    expected_output = resolve_path(invocation_set, root).resolve()
    if output_path.resolve() != expected_output:
        raise ValueError("--output must match inputs.review_invocation_set path")


def build_entry(
    assignment: dict[str, Any],
    root: Path,
    contract_path: Path,
) -> dict[str, Any]:
    reviewer = str(assignment["reviewer"])
    packet_path = resolve_path(assignment["packet_path"], root)
    report_path = resolve_path(assignment["report_path"], root)
    entry = {
        "reviewer": reviewer,
        "provider": str(assignment["provider"]),
        "model_family": str(assignment["model_family"]),
        "packet_path": str(packet_path),
        "report_path": str(report_path),
    }
    if packet_path.is_file():
        entry["packet_hash"] = sha256_file(packet_path)
    return entry


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
    entry["report_hash"] = sha256_file(report_path)
    validate_report_identity(report, reviewer, report_path)
    packet_path = resolve_path(assignment["packet_path"], root)
    packet = load_json(packet_path)
    entry["packet_hash"] = sha256_file(packet_path)
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
    entry["report_hash"] = sha256_file(report_path)
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
    status = "completed"

    try:
        contract = load_yaml(contract_path)
        assignments = contract.get("reviewer_assignments", []) or []
        if not isinstance(assignments, list) or not assignments:
            raise ValueError("review prompt contract must declare reviewer_assignments")
        validate_assignments(assignments, contract)
        validate_invocation_set_output_path(contract, output_path, root)
        require_model_diversity = (contract.get("provider_policy", {}) or {}).get("require_model_diversity") is True
        internal_runs: list[tuple[dict[str, Any], dict[str, Any]]] = []

        for assignment in assignments:
            provider = str(assignment["provider"])
            entry = build_entry(assignment, root, contract_path)
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
            "review_prompt_contract_hash": sha256_file(contract_path) if contract_path.is_file() else "",
            "status": status,
            "started_at": started,
            "finished_at": now_utc(),
            "runner_scheduling": "external-first-async",
            "provider_model_families": [],
            "reviewers": reviewers,
            "error": str(exc),
        }
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
        "review_prompt_contract_hash": sha256_file(contract_path),
        "status": status,
        "started_at": started,
        "finished_at": now_utc(),
        "runner_scheduling": "external-first-async",
        "provider_model_families": provider_model_families,
        "reviewers": reviewers,
    }
    output_path.write_text(
        json.dumps(completed_output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Review invocation set written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
