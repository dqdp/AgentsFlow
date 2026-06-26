#!/usr/bin/env python3
"""Run a lite external reviewer over a generated review bundle.

Lite mode is the default helper for ordinary standalone external review. It
keeps the provider invocation project-bound and evidence-backed without
requiring strict review prompt contracts or per-reviewer packet materialization.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import external_common  # noqa: E402
from providers import claude_code  # noqa: E402
from repo_validation.common import (  # noqa: E402
    parse_json_mapping as load_json,
    parse_yaml_mapping as load_yaml,
    raise_schema_validation_error,
    sha256_file,
    sha256_text,
)


WRAPPER = "scripts/reviewers/run_external_review_lite.py"
REQUEST_SCHEMA = "schemas/external-review-lite-request.schema.json"
INVOCATION_SCHEMA = "schemas/external-review-lite-invocation.schema.json"
OUTPUT_SCHEMA = "schemas/reviewer-report.schema.json"
DEFAULT_FORBIDDEN_ACTIONS = [
    "Do not use or assume forked orchestrator conversation context.",
    "Do not modify files.",
    "Do not run tests.",
    "Do not execute scripts.",
    "Do not produce patches.",
    "Do not update evidence.",
    "Return candidate findings only.",
]


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel_ref(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def portable_ref(root: Path, path: Path) -> str:
    try:
        return rel_ref(root, path)
    except ValueError:
        return str(path.resolve())


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def prepare_output_dir(output_dir: Path, replace: bool) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        if not replace:
            raise ValueError(
                f"--output-dir must be empty for lite review evidence: {output_dir}. "
                "Use --replace-output-dir only when intentionally discarding a previous attempt."
            )
        if output_dir.name != "external-review-lite" or not (output_dir / "external-review-lite-request.json").is_file():
            raise ValueError(
                "--replace-output-dir only replaces a previous external-review-lite bundle. "
                f"Refusing to delete: {output_dir}"
            )
        shutil.rmtree(output_dir)


def write_artifact(output_dir: Path, bundle_path: str, text: str, kind: str) -> dict[str, Any]:
    path = output_dir / bundle_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {
        "kind": kind,
        "path": portable_ref(Path.cwd(), path),
        "bundle_path": bundle_rel(output_dir, path),
        "hash": sha256_file(path),
    }


def safe_repo_ref(root: Path, ref: str, label: str) -> Path:
    path = Path(ref)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must be relative and non-escaping: {ref}")
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside repository root: {ref}") from exc
    return resolved


def resolve_artifact_ref(root: Path, output_dir: Path, ref: str, label: str) -> Path:
    path = Path(ref)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        if ".." in path.parts:
            raise ValueError(f"{label} must be relative and non-escaping: {ref}")
        root_candidate = (root / path).resolve()
        output_candidate = (output_dir / path).resolve()
        resolved = root_candidate if root_candidate.exists() else output_candidate
    root_resolved = root.resolve()
    output_resolved = output_dir.resolve()
    try:
        resolved.relative_to(root_resolved)
        return resolved
    except ValueError:
        pass
    try:
        resolved.relative_to(output_resolved)
        return resolved
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside repository root or review bundle: {ref}") from exc


def bundle_rel(output_dir: Path, path: Path) -> str:
    return path.resolve().relative_to(output_dir.resolve()).as_posix()


def dirty_material_change_id(head_commit: str, status_text: str, staged_diff: str, unstaged_diff: str) -> tuple[str, str]:
    basis = json.dumps(
        {
            "head_commit": head_commit,
            "git_status_hash": sha256_text(status_text),
            "staged_diff_hash": sha256_text(staged_diff),
            "unstaged_diff_hash": sha256_text(unstaged_diff),
        },
        sort_keys=True,
    )
    basis_hash = sha256_text(basis)
    return f"{head_commit}+dirty-{basis_hash.removeprefix('sha256:')[:16]}", basis_hash


def copy_include_artifact(root: Path, output_dir: Path, include_ref: str) -> dict[str, Any]:
    source = safe_repo_ref(root, include_ref, "--include")
    if not source.is_file():
        raise ValueError(f"--include must point to a file: {include_ref}")
    target = output_dir / "artifacts" / include_ref
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return {
        "kind": "included_file_snapshot",
        "path": portable_ref(root, target),
        "bundle_path": bundle_rel(output_dir, target),
        "source_path": rel_ref(root, source),
        "source_hash": sha256_file(source),
        "hash": sha256_file(target),
    }


def lite_provider_config(config: dict[str, Any]) -> dict[str, Any]:
    lite_config = copy.deepcopy(config)
    execution = lite_config.setdefault("execution", {})
    execution["prompt_transport"] = "file"
    execution["tools"] = "Read"
    execution["max_turns"] = max(int(execution.get("max_turns", 3) or 3), 10)
    context_policy = lite_config.setdefault("context_policy", {})
    context_policy["input_mode"] = "review_bundle"
    permissions = lite_config.setdefault("permissions", {})
    permissions["read_packet_only"] = False
    permissions["read_review_bundle_only"] = True
    inputs = lite_config.setdefault("inputs", {})
    inputs.pop("review_packet_schema", None)
    inputs["review_request_schema"] = REQUEST_SCHEMA
    outputs = lite_config.setdefault("outputs", {})
    outputs["invocation_metadata_schema"] = INVOCATION_SCHEMA
    return lite_config


def validate_lite_provider_config(config: dict[str, Any]) -> None:
    execution = config.get("execution", {}) or {}
    if execution.get("prompt_transport") != "file":
        raise ValueError("lite provider config must use file prompt transport")
    if execution.get("tools") != "Read":
        raise ValueError('lite provider config must set execution.tools to "Read"')
    context_policy = config.get("context_policy", {}) or {}
    if context_policy.get("input_mode") != "review_bundle":
        raise ValueError("lite provider config must use review_bundle input mode")
    permissions = config.get("permissions", {}) or {}
    if permissions.get("read_packet_only") is not False:
        raise ValueError("lite provider config must set read_packet_only to false")
    if permissions.get("read_review_bundle_only") is not True:
        raise ValueError("lite provider config must set read_review_bundle_only to true")
    inputs = config.get("inputs", {}) or {}
    if inputs.get("review_request_schema") != REQUEST_SCHEMA:
        raise ValueError("lite provider config must reference the lite review request schema")
    if "review_packet_schema" in inputs:
        raise ValueError("lite provider config must not advertise strict review packet input")
    outputs = config.get("outputs", {}) or {}
    if outputs.get("invocation_metadata_schema") != INVOCATION_SCHEMA:
        raise ValueError("lite provider config must reference the lite invocation schema")


def build_lite_request(
    root: Path,
    output_dir: Path,
    provider: str,
    reviewer_id: str,
    reviewer_role: str,
    review_goal: str,
    run_id: str,
    base_ref: str,
    head_ref: str,
    includes: list[str],
    verification_summary: str,
    include_uncommitted: bool,
) -> tuple[dict[str, Any], Path]:
    base_commit = run_git(root, "rev-parse", "--short", base_ref).strip()
    head_commit = run_git(root, "rev-parse", "--short", head_ref).strip()
    diff_text = run_git(root, "diff", "--no-ext-diff", f"{base_ref}...{head_ref}")
    changed_files = run_git(root, "diff", "--name-only", f"{base_ref}...{head_ref}").splitlines()
    status_text = run_git(root, "status", "--porcelain=v1")
    status_lines = status_text.splitlines()
    if status_lines and not include_uncommitted:
        raise ValueError(
            "worktree has uncommitted changes; pass --include-uncommitted after staging intended "
            "new files, or review a clean branch"
        )
    untracked = [line[3:] for line in status_lines if line.startswith("?? ")]
    if include_uncommitted and untracked:
        raise ValueError(
            "lite review cannot include untracked files. Stage intended new files first: "
            + ", ".join(untracked)
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    diff_path = output_dir / "artifacts" / "branch.diff"
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    diff_path.write_text(diff_text, encoding="utf-8")
    artifacts: list[dict[str, Any]] = [
        {
            "kind": "branch_diff",
            "path": portable_ref(root, diff_path),
            "bundle_path": bundle_rel(output_dir, diff_path),
            "hash": sha256_file(diff_path),
        }
    ]
    dirty_worktree = {
        "status": "dirty" if status_lines else "clean",
        "included": bool(status_lines and include_uncommitted),
        "policy": "include_staged_and_unstaged_diffs" if include_uncommitted else "clean_required",
    }
    material_change_id = head_commit
    if include_uncommitted:
        artifacts.append(write_artifact(output_dir, "artifacts/git-status.txt", status_text, "git_status"))
        staged_diff = run_git(root, "diff", "--no-ext-diff", "--cached")
        unstaged_diff = run_git(root, "diff", "--no-ext-diff")
        artifacts.append(write_artifact(output_dir, "artifacts/staged.diff", staged_diff, "staged_diff"))
        artifacts.append(write_artifact(output_dir, "artifacts/unstaged.diff", unstaged_diff, "unstaged_diff"))
        if status_lines:
            material_change_id, basis_hash = dirty_material_change_id(
                head_commit,
                status_text,
                staged_diff,
                unstaged_diff,
            )
            dirty_worktree["material_change_id_basis_hash"] = basis_hash
        changed_files = sorted(
            set(
                changed_files
                + run_git(root, "diff", "--name-only", "--cached").splitlines()
                + run_git(root, "diff", "--name-only").splitlines()
            )
        )
    for include_ref in includes:
        artifacts.append(copy_include_artifact(root, output_dir, include_ref))

    request = {
        "version": 1,
        "artifact_kind": "external_review_lite_request",
        "context_mode": "lite",
        "provider": provider,
        "reviewer": {
            "id": reviewer_id,
            "role": reviewer_role,
        },
        "run_id": run_id,
        "material_change_id": material_change_id,
        "review_goal": review_goal,
        "branch": {
            "base_ref": base_ref,
            "head_ref": head_ref,
            "base_commit": base_commit,
            "head_commit": head_commit,
        },
        "changed_files": changed_files,
        "dirty_worktree": dirty_worktree,
        "artifacts": artifacts,
        "context_policy": {
            "start_mode": "fresh_context",
            "fork_conversation_context": False,
            "allowed_context_sources": ["review_request", "referenced_artifacts"],
        },
        "forbidden_actions": DEFAULT_FORBIDDEN_ACTIONS,
        "output_schema": OUTPUT_SCHEMA,
        "verification_summary": verification_summary,
        "review_instructions": [
            "Start from the review request and referenced artifacts in this bundle.",
            "Use branch.diff plus any staged.diff or unstaged.diff artifacts as the primary code-change evidence.",
            "Cite only generated bundle artifacts. If outside context seems necessary, report that limitation.",
            "Prefer a few high-confidence findings over broad process commentary.",
        ],
    }
    request_path = output_dir / "external-review-lite-request.json"
    write_json(request_path, request)
    return request, request_path


def validate_lite_request(root: Path, output_dir: Path, request: dict[str, Any], request_path: Path) -> None:
    raise_schema_validation_error(request, load_json(root / REQUEST_SCHEMA), "external review lite request")
    forbidden_text = " ".join(str(item).lower() for item in request.get("forbidden_actions", []) or [])
    for phrase in ["modify files", "run tests", "produce patches", "execute scripts", "update evidence"]:
        if phrase not in forbidden_text:
            raise ValueError(f"lite request forbidden_actions must include: {phrase}")
    if request_path.resolve().parent != output_dir.resolve():
        raise ValueError("lite request must live at the review bundle root")
    for artifact in request.get("artifacts", []) or []:
        path = resolve_artifact_ref(root, output_dir, str(artifact.get("path", "")), "artifact.path")
        if not path.is_file():
            raise ValueError(f"lite request artifact does not exist: {artifact.get('path')}")
        declared_hash = artifact.get("hash")
        actual_hash = sha256_file(path)
        if declared_hash != actual_hash:
            raise ValueError(
                f"lite request artifact hash mismatch for {artifact.get('path')}: "
                f"declared {declared_hash}, computed {actual_hash}"
            )
        bundle_path = artifact.get("bundle_path")
        if bundle_path:
            resolved_bundle = output_dir / str(bundle_path)
            if resolved_bundle.resolve() != path.resolve():
                raise ValueError(f"lite request artifact bundle_path must match path: {bundle_path}")
    dirty = request.get("dirty_worktree", {}) or {}
    if dirty.get("status") == "dirty":
        artifact_kinds = {str(artifact.get("kind")) for artifact in request.get("artifacts", []) or []}
        required_dirty_artifacts = {"git_status", "staged_diff", "unstaged_diff"}
        if not required_dirty_artifacts.issubset(artifact_kinds):
            raise ValueError("dirty lite requests must include git status, staged diff and unstaged diff artifacts")


def render_lite_prompt(request: dict[str, Any]) -> str:
    reviewer = request.get("reviewer", {}) or {}
    artifact_lines = []
    for artifact in request.get("artifacts", []) or []:
        ref = artifact.get("bundle_path") or artifact.get("path")
        artifact_lines.append(f"- {artifact.get('kind')}: {ref} ({artifact.get('hash')})")
    artifact_list = "\n".join(artifact_lines) or "- <none>"
    return (
        "You are an AgentsFlow external read-only reviewer.\n"
        "Start from zero prior conversation context. Do not use or assume any forked orchestrator context.\n"
        "This is lite review mode: the generated review bundle is the declared review input.\n"
        "Read the review request and referenced artifacts in this directory when needed. "
        "Cite only generated bundle artifacts. If outside context seems necessary, report that limitation. "
        "Do not modify files. Do not run tests. "
        "Do not execute scripts. Do not produce patches. Do not update evidence.\n\n"
        "Return exactly one schema-valid reviewer-report JSON object and no markdown fence. "
        "Do not return prose outside JSON. If there are no findings, return an empty findings array "
        "and put residual uncertainty in summary or self_declared_limitations.\n\n"
        "Use this top-level JSON shape exactly: "
        '{"reviewer":{"id":"<reviewer_instance_id>","provider":"claude-code","role":"<reviewer_role>"},'
        '"review_context":{"run_id":"<run_id>","material_change_id":"<material_change_id>",'
        '"review_packet_path":"<review_request_path>","reviewer_instance_id":"<reviewer_instance_id>"},'
        '"summary":"<summary>","findings":[],"requests_for_additional_verification":[],'
        '"self_declared_limitations":[]}. '
        "Each finding must include id, severity, title, evidence as an array of strings, and status "
        '"candidate-unvalidated". P0/P1 findings must include blocker_path and acceptance_impact.\n\n'
        f"Reviewer id: {reviewer.get('id')}\n"
        f"Reviewer role: {reviewer.get('role')}\n"
        f"Run id: {request.get('run_id')}\n"
        f"Material change id: {request.get('material_change_id')}\n"
        f"Review request path: external-review-lite-request.json\n"
        f"Review goal: {request.get('review_goal')}\n\n"
        "Artifacts available in this bundle:\n"
        f"{artifact_list}\n\n"
        "Review request JSON:\n"
        + json.dumps(request, ensure_ascii=False, indent=2)
    )


def packet_like_from_request(request: dict[str, Any], request_path: Path, root: Path) -> dict[str, Any]:
    reviewer = request.get("reviewer", {}) or {}
    return {
        "reviewer_instance_id": str(reviewer.get("id") or "reviewer"),
        "reviewer_role": str(reviewer.get("role") or "reviewer"),
        "run_id": str(request.get("run_id") or ""),
        "material_change_id": str(request.get("material_change_id") or ""),
        "review_packet_path": portable_ref(root, request_path),
    }


def output_paths(output_dir: Path, args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    report = Path(args.output) if args.output else output_dir / "reviewer-report.claude-lite.json"
    raw = Path(args.raw_output) if args.raw_output else output_dir / "reviewer-report.claude-lite.raw.json"
    invocation = (
        Path(args.invocation_output)
        if args.invocation_output
        else output_dir / "reviewer-invocation.claude-lite.json"
    )
    stderr = report.with_suffix(".stderr.txt")
    return report, raw, invocation, stderr


def failure_invocation_base(
    args: argparse.Namespace,
    config: dict[str, Any],
    effective_config: dict[str, Any],
    request: dict[str, Any],
    request_path: Path,
    output_dir: Path,
    report_path: Path,
    started: str,
    prompt_hash: str,
    effective_config_path: Path,
) -> dict[str, Any]:
    execution = effective_config.get("execution", {}) or {}
    return {
        "provider": args.provider,
        "reviewer_role": str((request.get("reviewer") or {}).get("role", "reviewer")),
        "context_mode": "lite",
        "billing_mode": "subscription-local",
        "api_key_usage_forbidden": True,
        "context_policy": {
            "start_mode": "fresh_context",
            "fork_conversation_context": False,
            "session_persistence": False,
            "input_mode": "review_bundle",
        },
        "forbidden_env_checked": [
            str(item)
            for item in (config.get("billing", {}) or {}).get("fail_if_env_present", []) or []
        ],
        "command": "provider-call-not-completed",
        "wrapper": WRAPPER,
        "provider_config_path": str(args.config),
        "provider_config_hash": sha256_file(Path(args.config)),
        "effective_provider_config_path": portable_ref(Path.cwd(), effective_config_path),
        "effective_provider_config_hash": sha256_file(effective_config_path),
        "execution_mode": "mock" if args.mock_response else "real",
        "permission_mode": str(execution.get("permission_mode", "default")),
        "prompt_transport": "file",
        "sandbox_mode": str(execution.get("sandbox_mode", "require_escalated")),
        "tools": "Read",
        "output_format": str(execution.get("output_format", "json")),
        "requested_model": str(execution.get("model", external_common.DEFAULT_CLAUDE_MODEL)),
        "requested_effort": str(execution.get("effort", external_common.DEFAULT_CLAUDE_EFFORT)),
        "max_turns": int(execution.get("max_turns", 3)),
        "timeout_seconds": int(execution.get("timeout_seconds", 900)),
        "review_request_path": portable_ref(Path.cwd(), request_path),
        "review_request_hash": sha256_file(request_path),
        "review_bundle_path": portable_ref(Path.cwd(), output_dir),
        "input_hash": sha256_file(request_path),
        "prompt_hash": prompt_hash,
        "schema_hash": sha256_file(Path(OUTPUT_SCHEMA)),
        "started_at": started,
        "normalized_output_path": str(report_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="claude-code")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True, help="Review bundle output directory.")
    parser.add_argument("--goal", required=True, help="Review goal for the external reviewer.")
    parser.add_argument("--run-id", default="external-review-lite")
    parser.add_argument("--reviewer-id", default="generalist-claude")
    parser.add_argument("--reviewer-role", default="generalist")
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--head-ref", default="HEAD")
    parser.add_argument("--include", action="append", default=[], help="Relative file to snapshot into the bundle.")
    parser.add_argument(
        "--include-uncommitted",
        action="store_true",
        help="Include staged and unstaged tracked diffs; untracked files must be staged first.",
    )
    parser.add_argument(
        "--replace-output-dir",
        action="store_true",
        help="Delete an existing non-empty output directory before generating a fresh bundle.",
    )
    parser.add_argument("--verification-summary", default="")
    parser.add_argument("--output", help="Normalized reviewer report path.")
    parser.add_argument("--raw-output", help="Raw provider output path.")
    parser.add_argument("--invocation-output", help="Lite invocation metadata path.")
    parser.add_argument("--mock-response", help="Read provider raw JSON from this path instead of invoking CLI.")
    args = parser.parse_args()

    root = Path.cwd()
    output_dir = Path(args.output_dir).resolve()
    report_path, raw_path, invocation_path, stderr_path = output_paths(output_dir, args)
    failure_invocation: dict[str, Any] | None = None

    try:
        prepare_output_dir(output_dir, args.replace_output_dir)
        config = load_yaml(Path(args.config))
        external_common.validate_provider_config(config, args.provider)
        external_common.enforce_billing_policy(config)
        effective_config = lite_provider_config(config)
        validate_lite_provider_config(effective_config)
        request, request_path = build_lite_request(
            root=root,
            output_dir=output_dir,
            provider=args.provider,
            reviewer_id=args.reviewer_id,
            reviewer_role=args.reviewer_role,
            review_goal=args.goal,
            run_id=args.run_id,
            base_ref=args.base_ref,
            head_ref=args.head_ref,
            includes=args.include,
            verification_summary=args.verification_summary,
            include_uncommitted=args.include_uncommitted,
        )
        validate_lite_request(root, output_dir, request, request_path)
        effective_config_path = output_dir / "effective-provider-config.json"
        write_json(effective_config_path, effective_config)
        prompt = render_lite_prompt(request)
        prompt_path = output_dir / "agentsflow-review-prompt.md"
        prompt_path.write_text(prompt, encoding="utf-8")
        prompt_hash = sha256_text(prompt)
        started = now_utc()
        failure_invocation = failure_invocation_base(
            args,
            config,
            effective_config,
            request,
            request_path,
            output_dir,
            report_path,
            started,
            prompt_hash,
            effective_config_path,
        )

        if args.mock_response:
            raw_text = Path(args.mock_response).read_text(encoding="utf-8")
            stderr = ""
            exit_code = 0
            command_display = "mock-response"
        else:
            try:
                result = claude_code.invoke(effective_config, prompt, cwd=output_dir)
            except Exception as provider_exc:  # noqa: BLE001
                finished = now_utc()
                invocation = dict(failure_invocation)
                invocation.update(
                    {
                        "finished_at": finished,
                        "exit_code": 2,
                        "raw_output_path": "",
                        "raw_output_hash": "sha256:" + "0" * 64,
                        "raw_output_disposition": {
                            "stored": False,
                            "kind": "omission_reason",
                            "reason": "provider invocation raised before raw output was available",
                        },
                        "stderr_path": "",
                        "failure_stage": "provider_invocation_exception",
                        "failure_message": str(provider_exc),
                    }
                )
                invocation_path.parent.mkdir(parents=True, exist_ok=True)
                raise_schema_validation_error(
                    invocation,
                    load_json(root / INVOCATION_SCHEMA),
                    "external review lite failure invocation",
                )
                write_json(invocation_path, invocation)
                raise RuntimeError(invocation["failure_message"]) from provider_exc
            raw_text = result.stdout
            stderr = result.stderr
            exit_code = result.exit_code
            command_display = result.command_display
        failure_invocation["command"] = command_display

        normalization = config.get("normalization", {}) or {}
        preserve_raw_output = normalization.get("preserve_raw_output") is True
        raw_output_hash = sha256_text(raw_text)
        raw_source_path = ""
        raw_output_disposition = {
            "stored": False,
            "kind": "omission_reason",
            "reason": "normalization.preserve_raw_output is false; normalized report and provider metadata are retained",
        }
        if preserve_raw_output:
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(raw_text, encoding="utf-8")
            raw_output_hash = sha256_file(raw_path)
            raw_source_path = str(raw_path)
            raw_output_disposition = {
                "stored": True,
                "kind": "raw_output",
                "path": raw_source_path,
                "hash": raw_output_hash,
            }
        if failure_invocation is not None:
            failure_invocation.update(
                {
                    "exit_code": exit_code,
                    "raw_output_path": raw_source_path,
                    "raw_output_hash": raw_output_hash,
                    "raw_output_disposition": raw_output_disposition,
                    "stderr_path": str(stderr_path) if stderr else "",
                }
            )
        if exit_code != 0:
            finished = now_utc()
            detail = external_common.provider_failure_detail(raw_text, stderr)
            if stderr:
                stderr_path.parent.mkdir(parents=True, exist_ok=True)
                stderr_path.write_text(stderr, encoding="utf-8")
            invocation = dict(failure_invocation)
            invocation.update(
                {
                    "finished_at": finished,
                    "exit_code": exit_code,
                    "raw_output_path": raw_source_path,
                    "raw_output_hash": raw_output_hash,
                    "raw_output_disposition": raw_output_disposition,
                    "stderr_path": str(stderr_path) if stderr else "",
                    "failure_stage": "provider_execution",
                    "failure_message": f"external reviewer provider failed with exit code {exit_code}: {detail}",
                }
            )
            invocation_path.parent.mkdir(parents=True, exist_ok=True)
            raise_schema_validation_error(
                invocation,
                load_json(root / INVOCATION_SCHEMA),
                "external review lite failure invocation",
            )
            write_json(invocation_path, invocation)
            raise RuntimeError(invocation["failure_message"])

        raw_json = json.loads(raw_text)
        if not isinstance(raw_json, dict):
            raise ValueError("raw provider output must be a JSON object")
        provider_diagnostic = external_common.provider_output_diagnostic(raw_json)
        reviewer_report = external_common.extract_provider_reviewer_report(raw_json, args.provider)
        normalized = external_common.normalize_report(
            reviewer_report,
            packet_like_from_request(request, request_path, root),
            args.provider,
        )
        normalization_trace = {
            "method": external_common.normalization_method(raw_json, args.provider),
            "source_path": raw_source_path,
            "source_hash": raw_output_hash,
            "schema_validation": "passed",
            "normalized_by": WRAPPER,
        }
        normalized["normalization"] = normalization_trace
        if normalization.get("require_schema_validation") is True:
            external_common.validate_normalized_report_schema(normalized, root / OUTPUT_SCHEMA)
        external_common.validate_normalized_report(normalized)

        report_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(report_path, normalized)
        normalized_output_hash = sha256_file(report_path)
        if stderr:
            stderr_path.parent.mkdir(parents=True, exist_ok=True)
            stderr_path.write_text(stderr, encoding="utf-8")

        finished = now_utc()
        invocation = dict(failure_invocation)
        invocation.update(
            {
                "finished_at": finished,
                "exit_code": exit_code,
                "raw_output_path": raw_source_path,
                "raw_output_hash": raw_output_hash,
                "raw_output_disposition": raw_output_disposition,
                "stderr_path": str(stderr_path) if stderr else "",
                "normalized_output_hash": normalized_output_hash,
                "normalization": {
                    **normalization_trace,
                    "output_path": str(report_path),
                    "output_hash": normalized_output_hash,
                },
            }
        )
        invocation.update(external_common.provider_invocation_metadata(raw_json))
        raise_schema_validation_error(
            invocation,
            load_json(root / INVOCATION_SCHEMA),
            "external review lite invocation",
        )
        invocation_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(invocation_path, invocation)
        print(f"Lite external reviewer report written to {report_path}")
        return 0
    except Exception as exc:  # noqa: BLE001
        if failure_invocation is not None and not invocation_path.exists():
            invocation = dict(failure_invocation)
            invocation.update(
                {
                    "finished_at": now_utc(),
                    "exit_code": invocation.get("exit_code", 2),
                    "raw_output_path": invocation.get("raw_output_path", ""),
                    "raw_output_hash": invocation.get("raw_output_hash", "sha256:" + "0" * 64),
                    "raw_output_disposition": invocation.get(
                        "raw_output_disposition",
                        {
                            "stored": False,
                            "kind": "omission_reason",
                            "reason": "provider output was not available before failure",
                        },
                    ),
                    "failure_stage": "provider_output_processing",
                    "failure_message": str(exc),
                }
            )
            if "provider_diagnostic" in locals():
                invocation["provider_output_diagnostic"] = provider_diagnostic
            invocation_path.parent.mkdir(parents=True, exist_ok=True)
            raise_schema_validation_error(
                invocation,
                load_json(Path.cwd() / INVOCATION_SCHEMA),
                "external review lite failure invocation",
            )
            write_json(invocation_path, invocation)
        print(f"lite external reviewer failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
