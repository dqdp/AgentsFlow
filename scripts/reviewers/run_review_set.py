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
from pathlib import Path
from typing import Any

import yaml


SUPPORTED_PROVIDERS = {"internal-agent", "claude-code"}


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


def validate_invocation_set_output_path(contract: dict[str, Any], output_path: Path, root: Path) -> None:
    evidence_report = (contract.get("inputs", {}) or {}).get("evidence_report")
    if not evidence_report:
        raise ValueError("reviewer_assignments require inputs.evidence_report review_invocation_set path")
    expected_output = resolve_path(evidence_report, root).resolve()
    if output_path.resolve() != expected_output:
        raise ValueError("--output must match inputs.evidence_report review_invocation_set path")


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
    args = parser.parse_args()

    root = Path.cwd()
    contract_path = Path(args.contract)
    output_path = Path(args.output)
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    mock_responses = parse_mock_responses(args.mock_response)
    reviewers: list[dict[str, Any]] = []
    current_entry: dict[str, Any] | None = None
    status = "completed"

    try:
        contract = load_yaml(contract_path)
        assignments = contract.get("reviewer_assignments", []) or []
        if not isinstance(assignments, list) or not assignments:
            raise ValueError("review prompt contract must declare reviewer_assignments")
        validate_assignments(assignments, contract)
        validate_invocation_set_output_path(contract, output_path, root)
        require_model_diversity = (contract.get("provider_policy", {}) or {}).get("require_model_diversity") is True

        for assignment in assignments:
            reviewer = str(assignment["reviewer"])
            provider = str(assignment["provider"])
            model_family = str(assignment["model_family"])
            report_path = resolve_path(assignment["report_path"], root)
            entry: dict[str, Any] = {
                "reviewer": reviewer,
                "provider": provider,
                "model_family": model_family,
                "packet_path": str(resolve_path(assignment["packet_path"], root)),
                "report_path": str(report_path),
            }
            current_entry = entry

            if provider == "internal-agent":
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
            elif provider == "claude-code":
                raw_output_path = resolve_path(assignment["raw_output_path"], root)
                invocation_path = resolve_path(assignment["invocation_metadata_path"], root)
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
                    str(report_path),
                    "--raw-output",
                    str(raw_output_path),
                    "--invocation-output",
                    str(invocation_path),
                ]
                if reviewer in mock_responses:
                    cmd.extend(["--mock-response", str(resolve_path(mock_responses[reviewer], root))])
                result = subprocess.run(cmd, cwd=root, text=True, capture_output=True, check=False)
                entry["status"] = "invoked" if result.returncode == 0 else "failed"
                entry["stdout"] = result.stdout
                entry["stderr"] = result.stderr
                entry["raw_output_path"] = str(raw_output_path)
                entry["invocation_metadata_path"] = str(invocation_path)
                if result.returncode != 0:
                    raise RuntimeError(f"external reviewer {reviewer} failed: {result.stdout}{result.stderr}")
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
            reviewers.append(entry)
            current_entry = None
    except Exception as exc:  # noqa: BLE001
        status = "failed"
        if current_entry is not None and current_entry not in reviewers:
            current_entry["status"] = "failed"
            current_entry["error"] = str(exc)
            reviewers.append(current_entry)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {
                    "artifact_kind": "review_invocation_set",
                    "review_prompt_contract": str(contract_path),
                    "status": status,
                    "started_at": started,
                    "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "provider_model_families": [],
                    "reviewers": reviewers,
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
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
    output_path.write_text(
        json.dumps(
            {
                "artifact_kind": "review_invocation_set",
                "review_prompt_contract": str(contract_path),
                "status": status,
                "started_at": started,
                "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "provider_model_families": provider_model_families,
                "reviewers": reviewers,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Review invocation set written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
