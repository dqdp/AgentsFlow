#!/usr/bin/env python3
"""Prepare provider-assigned review artifacts.

This script is deliberately small and deterministic. It does not choose review
topology, reviewer roles, provider assignments or important files. It
materializes already-declared review inputs and writes structured preparation
evidence that validators can later bind to invocation evidence.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = SCRIPT_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from reviewers.prompt_rendering import render_review_prompt  # noqa: E402


ENVELOPE_FIELDS = {"review_packet_path", "reviewer_instance_id", "provider"}


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def validate_embedded_file_snapshots(root: Path, packet: dict[str, Any], packet_path: Path) -> None:
    files = packet.get("files")
    if not isinstance(files, list):
        return
    for idx, entry in enumerate(files):
        if not isinstance(entry, dict):
            continue
        ref = entry.get("path")
        if not isinstance(ref, str) or not ref:
            continue
        path = resolve_ref(root, ref, f"{packet_path}.files[{idx}].path")
        if not path.is_file():
            raise ValueError(f"{packet_path}: embedded file snapshot does not exist: {ref}")
        content = entry.get("content")
        if isinstance(content, str):
            actual = path.read_text(encoding="utf-8")
            if content != actual:
                raise ValueError(f"{packet_path}: embedded file snapshot is stale for {ref}")
        size_bytes = entry.get("size_bytes")
        if isinstance(size_bytes, int) and size_bytes != path.stat().st_size:
            raise ValueError(f"{packet_path}: embedded file size is stale for {ref}")


def resolve_ref(root: Path, ref: object, label: str) -> Path:
    if not ref:
        raise ValueError(f"{label} is required")
    path = Path(str(ref))
    if path.is_absolute():
        resolved = path.resolve()
    else:
        if ".." in path.parts:
            raise ValueError(f"{label} must be relative and non-escaping: {ref}")
        resolved = (root / path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside root: {ref}") from exc
    return resolved


def rel_ref(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def normalize_rel(ref: str) -> str:
    path = Path(ref)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"path must be relative and non-escaping: {ref}")
    return path.as_posix()


def parse_exclusions(values: list[str]) -> dict[str, str]:
    exclusions: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--exclude must use path=reason")
        path, reason = value.split("=", 1)
        path = normalize_rel(path.strip())
        reason = reason.strip()
        if not reason:
            raise ValueError("--exclude must include a non-empty reason")
        exclusions[path] = reason
    return exclusions


def collect_worktree_status(root: Path) -> list[dict[str, str]]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git status failed: {result.stdout}{result.stderr}")
    entries: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        status = line[:2].strip() or line[:2]
        path = line[3:] if len(line) > 3 else ""
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        entries.append({"path": path, "status": status})
    return entries


def fail_on_uncovered_dirty_paths(
    status_entries: list[dict[str, str]],
    covered_paths: set[str],
    exclusions: dict[str, str],
) -> None:
    uncovered = [
        entry["path"]
        for entry in status_entries
        if entry.get("path") and entry["path"] not in covered_paths and entry["path"] not in exclusions
    ]
    if uncovered:
        raise ValueError("uncovered dirty worktree path(s): " + ", ".join(sorted(uncovered)))


def reviewer_by_id(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("instance_id")): item
        for item in contract.get("reviewer_set", []) or []
        if isinstance(item, dict) and item.get("instance_id")
    }


def prompt_by_reviewer(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("reviewer")): item
        for item in contract.get("rendered_prompts", []) or []
        if isinstance(item, dict) and item.get("reviewer")
    }


def assignment_by_reviewer(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("reviewer")): item
        for item in contract.get("reviewer_assignments", []) or []
        if isinstance(item, dict) and item.get("reviewer")
    }


def packet_entry_by_reviewer(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("reviewer")): item
        for item in ((contract.get("inputs") or {}).get("review_packets") or [])
        if isinstance(item, dict) and item.get("reviewer")
    }


def packet_shared_payload(packet: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in packet.items() if key not in ENVELOPE_FIELDS}


def normalize_forbidden_actions(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    aliases = {
        "run_tests": "Do not run tests.",
        "run_scripts": "Do not execute scripts.",
        "modify_files": "Do not modify files.",
        "create_patch": "Do not produce patches.",
        "update_evidence": "Do not update evidence.",
    }
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value)
        action = aliases.get(text, text)
        if action not in seen:
            normalized.append(action)
            seen.add(action)
    return normalized


def artifact_entry(root: Path, ref: object, kind: str, required_by: list[str] | None = None) -> dict[str, Any]:
    path = resolve_ref(root, ref, kind)
    if not path.is_file():
        raise ValueError(f"{kind} must be a file artifact: {ref}")
    entry: dict[str, Any] = {
        "path": rel_ref(root, path),
        "kind": kind,
        "hash": sha256_file(path),
    }
    if required_by:
        entry["required_by"] = required_by
    return entry


def collect_input_artifacts(
    root: Path,
    contract: dict[str, Any],
    shared_packet_path: Path,
    include_paths: list[str],
) -> list[dict[str, Any]]:
    inputs = contract.get("inputs", {}) or {}
    artifacts: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(ref: object, kind: str, required_by: list[str] | None = None) -> None:
        if not ref:
            return
        entry = artifact_entry(root, ref, kind, required_by)
        if entry["path"] not in seen:
            artifacts.append(entry)
            seen.add(entry["path"])

    add(rel_ref(root, shared_packet_path), "shared_review_packet_source", ["review_packet_generation"])
    add(inputs.get("task_contract"), "task_contract", ["review_context"])
    add(inputs.get("verification_gate_report"), "verification_gate_report", ["review_context"])
    add(inputs.get("review_packet_schema"), "schema", ["review_packet_generation"])
    add(inputs.get("output_schema"), "schema", ["reviewer_output"])
    for include in include_paths:
        kind = "agent_instructions" if Path(include).name == "AGENTS.md" else "declared_input"
        add(include, kind, ["explicit_include"])
    return artifacts


def apply_common_packet_fields(
    packet: dict[str, Any],
    contract: dict[str, Any],
    contract_ref: str,
) -> dict[str, Any]:
    identity = contract.get("identity", {}) or {}
    inputs = contract.get("inputs", {}) or {}
    packet = dict(packet)
    packet.setdefault("agentsflow_version", "0.2")
    for key in ["workflow", "run_id", "review_profile", "composition"]:
        if identity.get(key) is not None:
            packet[key] = identity[key]
    packet["prompt_policy"] = contract.get("prompt_policy", {}) or {}
    packet["review_prompt_contract"] = {
        "path": contract_ref,
        "schema": "schemas/review-prompt-contract.schema.json",
    }
    if contract.get("context_policy"):
        packet["context_policy"] = contract["context_policy"]
    permission_policy = contract.get("permission_policy", {}) or {}
    if permission_policy.get("forbidden_actions"):
        packet["forbidden_actions"] = normalize_forbidden_actions(permission_policy["forbidden_actions"])
    if contract.get("risk_surface_profile"):
        packet["risk_surface_profile"] = contract["risk_surface_profile"]
    if contract.get("failure_path_matrix"):
        packet["failure_path_matrix"] = contract["failure_path_matrix"]
    if contract.get("known_blockers") is not None:
        packet["known_blockers"] = contract["known_blockers"]
    if inputs.get("output_schema"):
        packet["output_schema"] = inputs["output_schema"]
    if inputs.get("verification_gate_report"):
        packet["verification_gate_report"] = {"path": inputs["verification_gate_report"]}
        packet.setdefault("evidence_freshness", {})
        freshness = packet.get("evidence_freshness")
        if isinstance(freshness, dict):
            freshness["latest_green_gate"] = inputs["verification_gate_report"]
            freshness.setdefault("material_change_id", packet.get("material_change_id", "current"))
            freshness.setdefault("review_packet_generated_after_latest_green_gate", True)
            freshness.setdefault("stale_evidence_marked_or_excluded", True)
    return packet


def prepare_artifacts(
    root: Path,
    contract_path: Path,
    shared_packet_path: Path,
    preparation_path: Path,
    include_paths: list[str],
    exclusions: dict[str, str],
    material_change_id: str | None,
) -> dict[str, Any]:
    contract = load_yaml(contract_path)
    shared_packet = load_json(shared_packet_path)
    validate_embedded_file_snapshots(root, shared_packet, shared_packet_path)
    inputs = contract.setdefault("inputs", {})
    reviewers = reviewer_by_id(contract)
    assignments = assignment_by_reviewer(contract)
    packet_entries = packet_entry_by_reviewer(contract)
    prompt_entries = prompt_by_reviewer(contract)
    if not assignments:
        raise ValueError("review prompt contract must declare reviewer_assignments")
    if sorted(assignments) != sorted(reviewers):
        raise ValueError("reviewer_assignments must cover reviewer_set exactly")

    inputs["artifact_preparation_report"] = rel_ref(root, preparation_path)
    inputs.setdefault("review_invocation_set", rel_ref(root, contract_path.parent / "review-invocation-set.json"))
    contract_ref = rel_ref(root, contract_path)
    status_entries = collect_worktree_status(root)

    generated_paths = {rel_ref(root, preparation_path), contract_ref}
    for packet in packet_entries.values():
        generated_paths.add(rel_ref(root, resolve_ref(root, packet.get("path"), "review packet path")))
    for prompt in prompt_entries.values():
        generated_paths.add(rel_ref(root, resolve_ref(root, prompt.get("prompt_path"), "rendered prompt path")))
    if packet_entries:
        first_packet = resolve_ref(root, next(iter(packet_entries.values())).get("path"), "review packet path")
        generated_paths.add(rel_ref(root, first_packet.parent / "shared-content.json"))
    covered_paths = set(include_paths) | generated_paths | {rel_ref(root, shared_packet_path)}
    fail_on_uncovered_dirty_paths(status_entries, covered_paths, exclusions)

    input_artifacts = collect_input_artifacts(root, contract, shared_packet_path, include_paths)
    output_schema_hash = sha256_file(resolve_ref(root, inputs.get("output_schema"), "inputs.output_schema"))
    rubric_hash = sha256_text(json.dumps(contract.get("prompt_policy", {}) or {}, sort_keys=True))

    generated_packets: list[dict[str, Any]] = []
    generated_prompts: list[dict[str, Any]] = []
    packets_by_reviewer: dict[str, dict[str, Any]] = {}
    role_data_by_reviewer: dict[str, dict[str, Any]] = {}
    role_hash_by_reviewer: dict[str, str] = {}

    for reviewer_id, reviewer in reviewers.items():
        packet_entry = packet_entries.get(reviewer_id)
        prompt_entry = prompt_entries.get(reviewer_id)
        assignment = assignments.get(reviewer_id)
        if not packet_entry or not prompt_entry or not assignment:
            raise ValueError(f"reviewer {reviewer_id} must have packet, prompt and assignment entries")
        role_ref = reviewer.get("role_contract")
        role_path = resolve_ref(root, role_ref, f"reviewer_set.{reviewer_id}.role_contract")
        role_data = load_yaml(role_path)
        role_hash = sha256_file(role_path)
        packet = apply_common_packet_fields(shared_packet, contract, contract_ref)
        packet["reviewer_instance_id"] = reviewer_id
        packet["reviewer_role"] = reviewer.get("role_id")
        packet["role_contract"] = role_ref
        packet["role_contract_hash"] = role_hash
        if assignment.get("provider"):
            packet["provider"] = assignment["provider"]
        if reviewer.get("focus_zone"):
            packet["focus_zone"] = reviewer["focus_zone"]
        elif "focus_zone" in packet:
            packet.pop("focus_zone", None)
        packet_path = resolve_ref(root, packet_entry.get("path"), f"inputs.review_packets.{reviewer_id}.path")
        packet["review_packet_path"] = rel_ref(root, packet_path)
        write_json(packet_path, packet)
        packet_hash = sha256_file(packet_path)
        packet_entry["packet_hash"] = packet_hash
        assignment["packet_path"] = rel_ref(root, packet_path)
        packets_by_reviewer[reviewer_id] = packet
        role_data_by_reviewer[reviewer_id] = role_data
        role_hash_by_reviewer[reviewer_id] = role_hash
        generated_packets.append(
            {
                "reviewer": reviewer_id,
                "path": rel_ref(root, packet_path),
                "hash": packet_hash,
            }
        )

    shared_content_path: Path | None = None
    shared_packet_hash: str | None = None
    shared_prompt_hash: str | None = None
    if (contract.get("identity", {}) or {}).get("review_profile") == "homogeneous-dual":
        first_reviewer = next(iter(reviewers))
        first_packet_path = resolve_ref(
            root,
            packet_entries[first_reviewer].get("path"),
            f"inputs.review_packets.{first_reviewer}.path",
        )
        shared_content_path = first_packet_path.parent / "shared-content.json"
        shared_content = packet_shared_payload(packets_by_reviewer[first_reviewer])
        shared_content["excluded_envelope_fields"] = sorted(ENVELOPE_FIELDS)
        write_json(shared_content_path, shared_content)
        shared_packet_hash = sha256_file(shared_content_path)
        shared_prompt_hash = sha256_text(
            render_review_prompt(packet_shared_payload(packets_by_reviewer[first_reviewer]), role_data_by_reviewer[first_reviewer])
        )
        for packet_entry in packet_entries.values():
            packet_entry["shared_packet_content_hash"] = shared_packet_hash
        for packet in generated_packets:
            packet["shared_packet_content_hash"] = shared_packet_hash

    for reviewer_id, reviewer in reviewers.items():
        prompt_entry = prompt_entries[reviewer_id]
        packet_entry = packet_entries[reviewer_id]
        prompt_path = resolve_ref(root, prompt_entry.get("prompt_path"), f"rendered_prompts.{reviewer_id}.prompt_path")
        prompt_text = render_review_prompt(packets_by_reviewer[reviewer_id], role_data_by_reviewer[reviewer_id])
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt_text, encoding="utf-8")
        prompt_hash = sha256_file(prompt_path)
        prompt_entry["prompt_hash"] = prompt_hash
        prompt_entry["packet_hash"] = packet_entry["packet_hash"]
        prompt_entry["schema_hash"] = output_schema_hash
        prompt_entry["rubric_hash"] = rubric_hash
        prompt_entry["role_contract_hash"] = role_hash_by_reviewer[reviewer_id]
        if shared_packet_hash:
            prompt_entry["shared_packet_content_hash"] = shared_packet_hash
        if shared_prompt_hash:
            prompt_entry["shared_prompt_content_hash"] = shared_prompt_hash
        generated_prompts.append(
            {
                "reviewer": reviewer_id,
                "path": rel_ref(root, prompt_path),
                "hash": prompt_hash,
                "packet_hash": prompt_entry["packet_hash"],
                "schema_hash": output_schema_hash,
                "rubric_hash": rubric_hash,
                "role_contract_hash": role_hash_by_reviewer[reviewer_id],
            }
        )

    write_yaml(contract_path, contract)
    contract_hash = sha256_file(contract_path)

    preparation: dict[str, Any] = {
        "version": 1,
        "artifact_kind": "review_artifact_preparation",
        "artifact_scope": "run",
        "status": "completed",
        "prepared_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "review_prompt_contract": {
            "path": contract_ref,
            "hash": contract_hash,
        },
        "source_context": {
            "dirty_policy": "fail-closed",
            "worktree": {
                "status_command": "git status --porcelain=v1 --untracked-files=all",
                "status_entries": status_entries,
                "included_dirty_paths": sorted(
                    entry["path"] for entry in status_entries if entry.get("path") in set(include_paths)
                ),
                "excluded_dirty_paths": [
                    {"path": path, "reason": reason}
                    for path, reason in sorted(exclusions.items())
                    if any(entry.get("path") == path for entry in status_entries)
                ],
            },
        },
        "input_artifacts": input_artifacts,
        "generated_artifacts": {
            "review_packets": generated_packets,
            "rendered_prompts": generated_prompts,
            "review_invocation_set": {
                "path": str(inputs["review_invocation_set"]),
                "status": "predeclared",
            },
        },
        "reviewer_assignments": contract.get("reviewer_assignments", []) or [],
        "validation": {
            "schema": "schemas/review-artifact-preparation.schema.json",
            "deterministic_script": "scripts/reviewers/prepare_review_set_artifacts.py",
            "script_contract": "scripts/contracts/prepare_review_set_artifacts.yaml",
        },
    }
    if material_change_id:
        preparation["source_context"]["material_change_id"] = material_change_id
    if shared_content_path and shared_packet_hash:
        preparation["generated_artifacts"]["shared_packet_content"] = {
            "path": rel_ref(root, shared_content_path),
            "hash": shared_packet_hash,
        }
    write_json(preparation_path, preparation)
    invocation_set_path = resolve_ref(root, inputs["review_invocation_set"], "inputs.review_invocation_set")
    provider_model_families = sorted(
        {
            f"{assignment.get('provider')}/{assignment.get('model_family')}"
            for assignment in contract.get("reviewer_assignments", []) or []
            if isinstance(assignment, dict)
            and assignment.get("provider")
            and assignment.get("model_family")
        }
    )
    invocation_reviewers: list[dict[str, Any]] = []
    for assignment in contract.get("reviewer_assignments", []) or []:
        if not isinstance(assignment, dict):
            continue
        entry = {
            "reviewer": assignment.get("reviewer"),
            "provider": assignment.get("provider"),
            "model_family": assignment.get("model_family"),
            "packet_path": assignment.get("packet_path"),
            "report_path": assignment.get("report_path"),
            "status": "predeclared",
        }
        for key in ["raw_output_path", "invocation_metadata_path"]:
            if assignment.get(key):
                entry[key] = assignment[key]
        invocation_reviewers.append(entry)
    invocation_set: dict[str, Any] = {
        "artifact_kind": "review_invocation_set",
        "review_prompt_contract": contract_ref,
        "artifact_preparation_report": rel_ref(root, preparation_path),
        "artifact_preparation_report_hash": sha256_file(preparation_path),
        "status": "predeclared",
        "provider_model_families": provider_model_families,
        "reviewers": invocation_reviewers,
    }
    if any(item.get("provider") == "claude-code" for item in invocation_reviewers):
        invocation_set["runner_scheduling"] = "external-first-async"
    write_json(invocation_set_path, invocation_set)
    return preparation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Repository/project root.")
    parser.add_argument("--contract", required=True, help="Review prompt contract YAML, relative to root.")
    parser.add_argument("--shared-packet", required=True, help="Shared review packet source JSON, relative to root.")
    parser.add_argument("--preparation-output", required=True, help="Preparation evidence JSON, relative to root.")
    parser.add_argument("--include", action="append", default=[], help="Declared input artifact path.")
    parser.add_argument("--exclude", action="append", default=[], help="Dirty path exclusion as path=reason.")
    parser.add_argument("--material-change-id", help="Optional material change id for freshness binding.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    try:
        include_paths = [normalize_rel(path) for path in args.include]
        exclusions = parse_exclusions(args.exclude)
        contract_path = resolve_ref(root, args.contract, "--contract")
        shared_packet_path = resolve_ref(root, args.shared_packet, "--shared-packet")
        preparation_path = resolve_ref(root, args.preparation_output, "--preparation-output")
        prepare_artifacts(
            root,
            contract_path,
            shared_packet_path,
            preparation_path,
            include_paths,
            exclusions,
            args.material_change_id,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"review artifact preparation failed: {exc}", file=sys.stderr)
        return 2
    print(f"Review artifact preparation written to {preparation_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
