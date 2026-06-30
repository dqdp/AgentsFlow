from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from reviewers.prompt_rendering import render_review_prompt  # noqa: E402

PR_REVIEW_MATRIX = [
    ("generalist-a", "generalist-readiness", "internal-agent", False, "generalist"),
    ("generalist-b", "generalist-readiness", "internal-agent", False, "generalist"),
    ("adversarial-codex", "adversarial-authority", "internal-agent", False, "adversarial"),
]
CLAUDE_REVIEW = ("generalist-claude", "generalist-readiness", "claude-code", True, "generalist")
DEFAULT_REQUIREMENTS_SOURCE = "review-requirements/default.yaml"
WITH_CLAUDE_REQUIREMENTS_SOURCE = "review-requirements/with-claude.yaml"
PROVIDER_CONFIG_CONTENT = (ROOT / "templates" / "external-review-provider.yaml").read_text(
    encoding="utf-8"
)
FORBIDDEN_CLAUDE_ENV = [
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
]
GITHUB_PUBLICATION_BODY = "PR readiness summary fixture.\n"


def load_evaluator():
    from repo_validation.pr_merge_readiness import evaluate_pr_merge_readiness_report

    return evaluate_pr_merge_readiness_report


def write_evidence(root: Path, *paths: str) -> None:
    for ref in paths:
        path = root / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"evidence for {ref}\n", encoding="utf-8")


def write_github_publication_evidence(root: Path) -> None:
    body_path = root / "github-publication.md"
    body_path.write_text(GITHUB_PUBLICATION_BODY, encoding="utf-8")
    (root / "github-publication-result.json").write_text(
        json.dumps(
            {
                "provider": "github",
                "tool": "gh",
                "action": "pr comment",
                "status": "published",
                "pr": 1,
                "url": "https://github.com/org/repo/pull/1#issuecomment-1",
                "body_path": "github-publication.md",
                "body_hash": file_sha(body_path),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_report(root: Path, report: dict) -> Path:
    path = root / "pr-merge-readiness-report.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    human_decisions_path = root / "human-decisions.yaml"
    if human_decisions_path.is_file():
        data = yaml.safe_load(human_decisions_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("decisions"), list):
            changed = False
            for item in data["decisions"]:
                if not isinstance(item, dict):
                    continue
                if item.get("decision_id") != "merge.acceptance":
                    continue
                affected = item.get("affected_artifacts")
                if not isinstance(affected, list) or "pr-merge-readiness-report.json" not in affected:
                    continue
                if item.get("status") != "confirmed" or item.get("answered_by") != "human":
                    continue
                item["material_change_id"] = report.get("material_change_id")
                item["report_hash"] = file_sha(path)
                changed = True
            if changed:
                human_decisions_path.write_text(
                    yaml.safe_dump(data, sort_keys=False),
                    encoding="utf-8",
                )
    return path


def file_sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def required_reviews_from_matrix(matrix: list[tuple[str, str, str, bool, str]]) -> list[dict]:
    return [
        {
            "id": reviewer,
            "topic": topic,
            "role": role,
            "provider": provider,
            "required_live": required_live,
        }
        for reviewer, topic, provider, required_live, role in matrix
    ]


def review_requirements_source_content(matrix: list[tuple[str, str, str, bool, str]]) -> str:
    return yaml.safe_dump(
        {
            "version": 1,
            "artifact_kind": "review_requirements",
            "required_reviews": required_reviews_from_matrix(matrix),
        },
        sort_keys=False,
    )


def review_requirements_source(
    path: str,
    matrix: list[tuple[str, str, str, bool, str]],
) -> dict:
    return {
        "kind": "explicit_review_gate",
        "path": path,
        "artifact_hash": text_sha(review_requirements_source_content(matrix)),
    }


def grounded_blocker_fields() -> dict[str, object]:
    return {
        "validated_severity": "P1",
        "evidence": ["reviewer-report.generalist-a.json"],
        "blocker_path": "required PR readiness evidence -> review finding -> unsafe merge acceptance",
        "acceptance_impact": "Accepting the branch unchanged would approve a PR without required readiness evidence.",
    }


def redacted_raw_summary(reviewer: str) -> str:
    return f"Redacted raw provider output summary for {reviewer}.\n"


def attach_raw_provider_output(root: Path, reviewer: str, content: str = '{"result":"ok"}\n') -> None:
    raw_path = root / "raw" / f"{reviewer}.raw.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(content, encoding="utf-8")
    invocation_path = root / f"reviewer-invocation.{reviewer}.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation["raw_output_path"] = f"raw/{reviewer}.raw.json"
    invocation["raw_output_hash"] = file_sha(raw_path)
    invocation_path.write_text(json.dumps(invocation, indent=2) + "\n", encoding="utf-8")


def review_context(reviewer: str) -> dict:
    return {
        "run_id": "2026-06-22-pr-merge-readiness-example",
        "material_change_id": "pr-merge-readiness-example-change",
        "review_packet_path": f"review-packets/{reviewer}.json",
        "reviewer_instance_id": reviewer,
    }


def invocation_metadata(reviewer: str) -> dict:
    reviewer_role = reviewer.removesuffix("-claude").removesuffix("-codex")
    return {
        "provider": "claude-code",
        "reviewer_role": reviewer_role,
        "billing_mode": "subscription-local",
        "api_key_usage_forbidden": True,
        "context_policy": {
            "start_mode": "fresh_context",
            "fork_conversation_context": False,
            "session_persistence": False,
            "input_mode": "review_bundle",
        },
        "forbidden_env_checked": FORBIDDEN_CLAUDE_ENV,
        "command": "claude -p agentsflow-review-prompt.md --output-format json --permission-mode default --tools Read --model opus --effort max --max-turns 42 --no-session-persistence",
        "wrapper": "scripts/reviewers/run_external_review_lite.py",
        "provider_config_path": "external-reviewers/claude-code.yaml",
        "provider_config_hash": "sha256:" + hashlib.sha256(PROVIDER_CONFIG_CONTENT.encode("utf-8")).hexdigest(),
        "effective_provider_config_path": "external-reviewers/claude-code.yaml",
        "effective_provider_config_hash": "sha256:" + hashlib.sha256(PROVIDER_CONFIG_CONTENT.encode("utf-8")).hexdigest(),
        "execution_mode": "real",
        "permission_mode": "default",
        "prompt_transport": "file",
        "sandbox_mode": "require_escalated",
        "tools": "Read",
        "output_format": "json",
        "requested_model": "opus",
        "requested_effort": "max",
        "provider_models_used": ["claude-opus-4-8"],
        "max_turns": 42,
        "timeout_seconds": 1500,
        "started_at": "2026-06-22T10:00:00Z",
        "finished_at": "2026-06-22T10:01:00Z",
        "exit_code": 0,
        "raw_output_path": "",
        "raw_output_hash": "sha256:" + "1" * 64,
        "normalized_output_path": f"reviewer-report.{reviewer}.json",
        "normalized_output_hash": "sha256:" + "2" * 64,
        "input_hash": "sha256:" + "3" * 64,
        "prompt_hash": "sha256:" + "4" * 64,
        "schema_hash": "sha256:" + "8" * 64,
    }


def lite_invocation_metadata(root: Path, reviewer: str = "generalist-claude") -> dict:
    request_path = root / "external-review-lite" / "external-review-lite-request.json"
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(
            {
                "version": 1,
                "artifact_kind": "external_review_lite_request",
                "context_mode": "lite",
                "provider": "claude-code",
                "reviewer": {"id": reviewer, "role": "generalist"},
                "run_id": "2026-06-22-pr-merge-readiness-example",
                "material_change_id": "pr-merge-readiness-example-change",
                "review_goal": "Review PR readiness evidence for acceptance-blocking risks.",
                "branch": {
                    "base_ref": "main",
                    "head_ref": "codex/pr-merge-readiness",
                    "base_commit": "base",
                    "head_commit": "head",
                },
                "changed_files": ["scripts/repo_validation/pr_merge_readiness.py"],
                "dirty_worktree": {
                    "status": "clean",
                    "included": False,
                    "policy": "clean_required",
                },
                "artifacts": [
                    {
                        "kind": "verification_evidence",
                        "path": "evidence/repo-validation.log",
                        "hash": file_sha(root / "evidence/repo-validation.log"),
                    }
                ],
                "context_policy": {
                    "start_mode": "fresh_context",
                    "fork_conversation_context": False,
                    "allowed_context_sources": ["review_request", "referenced_artifacts"],
                },
                "forbidden_actions": [
                    "Do not modify files.",
                    "Do not run tests.",
                ],
                "output_schema": "schemas/reviewer-report.schema.json",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    provider_config = root / "external-reviewers" / "claude-code.yaml"
    return {
        "provider": "claude-code",
        "reviewer_role": "generalist",
        "context_mode": "lite",
        "billing_mode": "subscription-local",
        "api_key_usage_forbidden": True,
        "context_policy": {
            "start_mode": "fresh_context",
            "fork_conversation_context": False,
            "session_persistence": False,
            "input_mode": "review_bundle",
        },
        "forbidden_env_checked": FORBIDDEN_CLAUDE_ENV,
        "command": "claude -p agentsflow-review-prompt.md --output-format json --permission-mode default --tools Read --model opus --effort max --max-turns 42 --no-session-persistence",
        "wrapper": "scripts/reviewers/run_external_review_lite.py",
        "provider_config_path": "external-reviewers/claude-code.yaml",
        "provider_config_hash": file_sha(provider_config),
        "effective_provider_config_path": "external-reviewers/claude-code.yaml",
        "effective_provider_config_hash": file_sha(provider_config),
        "execution_mode": "real",
        "permission_mode": "default",
        "prompt_transport": "file",
        "sandbox_mode": "require_escalated",
        "tools": "Read",
        "output_format": "json",
        "requested_model": "opus",
        "requested_effort": "max",
        "review_request_path": "external-review-lite/external-review-lite-request.json",
        "review_request_hash": file_sha(request_path),
        "review_bundle_path": "external-review-lite",
        "input_hash": file_sha(request_path),
        "prompt_hash": file_sha(root / "review-prompts" / f"{reviewer}.md"),
        "schema_hash": file_sha(root / "schemas" / "reviewer-report.schema.json"),
        "started_at": "2026-06-22T10:00:00Z",
        "finished_at": "2026-06-22T10:01:00Z",
        "exit_code": 0,
        "raw_output_path": "",
        "raw_output_hash": "sha256:" + "1" * 64,
        "raw_output_disposition": {
            "stored": False,
            "kind": "omission_reason",
            "reason": "raw provider output not persisted in lite fixture",
        },
        "normalized_output_path": f"reviewer-report.{reviewer}.json",
        "normalized_output_hash": file_sha(root / f"reviewer-report.{reviewer}.json"),
    }


def complete_report() -> dict:
    return {
        "version": 1,
        "artifact_kind": "pr_merge_readiness_report",
        "workflow": "pr-merge-readiness",
        "run_id": "2026-06-22-pr-merge-readiness-example",
        "material_change_id": "pr-merge-readiness-example-change",
        "branch": {
            "name": "codex/pr-merge-readiness",
            "base": "main",
            "commit_range": "main..HEAD",
            "worktree_state": "clean",
            "pull_request": 1,
            "repository": "org/repo",
        },
        "status": "accepted_merge_ready",
        "checks": [
            {
                "id": "repo-validation",
                "category": "verification",
                "status": "pass",
                "evidence_path": "evidence/repo-validation.log",
            },
            {
                "id": "pytest",
                "category": "test",
                "status": "pass",
                "evidence_path": "evidence/pytest.log",
            },
        ],
        "review_requirements": {
            "source": review_requirements_source(DEFAULT_REQUIREMENTS_SOURCE, PR_REVIEW_MATRIX),
            "required_reviews": required_reviews_from_matrix(PR_REVIEW_MATRIX),
        },
        "reviews": [
            {
                "id": reviewer,
                "topic": topic,
                "provider": provider,
                "status": "pass",
                "packet_path": f"review-packets/{reviewer}.json",
                "prompt_path": f"review-prompts/{reviewer}.md",
                "role_contract_path": f"profiles/reviewer_roles/{role}.yaml",
                "report_path": f"reviewer-report.{reviewer}.json",
                "packet_prepared_at": "2026-06-22T10:00:00Z",
                "latest_material_change_at": "2026-06-22T09:30:00Z",
            }
            for reviewer, topic, provider, _required_live, role in PR_REVIEW_MATRIX
        ],
        "external_review_evidence": [
            {
                "provider": "claude-code",
                "mode": "live",
                "required_live": True,
                "status": "pass",
                "normalized_report_path": f"reviewer-report.{reviewer}.json",
                "invocation_metadata_path": f"reviewer-invocation.{reviewer}.json",
                "raw_output": {
                    "persistence": "redacted",
                    "redaction_reason": "live output may contain local workspace context",
                    "artifact_path": f"evidence/raw/{reviewer}.redacted-summary.md",
                    "artifact_hash": text_sha(redacted_raw_summary(reviewer)),
                },
            }
            for reviewer, _topic, provider, _required_live, _role in PR_REVIEW_MATRIX
            if provider == "claude-code"
        ],
        "candidate_findings": [],
        "human_decision": {
            "status": "accepted",
            "decision_id": "merge.acceptance",
            "path": "human-decisions.yaml",
        },
        "github_publication": {
            "status": "published",
            "required_for_merge_readiness": True,
            "publication_mode": "summary_comment",
            "target": "pull_request",
            "tool": "gh",
            "action": "pr comment",
            "body_path": "github-publication.md",
            "result_path": "github-publication-result.json",
            "pr": 1,
            "body_hash": text_sha(GITHUB_PUBLICATION_BODY),
            "url": "https://github.com/org/repo/pull/1#issuecomment-1",
        },
        "self_application": {
            "enabled": True,
            "application_mode": "self_application_bootstrap",
            "proof_claim": "bootstrap_not_self_proof",
        },
        "residual_limitations": [],
    }


def add_claude_review(report: dict, reviewer: str = "generalist-claude") -> dict:
    if reviewer != CLAUDE_REVIEW[0]:
        raise ValueError("test helper currently supports only generalist-claude")
    reviewer, topic, provider, required_live, role = CLAUDE_REVIEW
    report["review_requirements"]["source"] = review_requirements_source(
        WITH_CLAUDE_REQUIREMENTS_SOURCE,
        PR_REVIEW_MATRIX + [CLAUDE_REVIEW],
    )
    report["review_requirements"]["required_reviews"].append(
        {
            "id": reviewer,
            "topic": topic,
            "role": role,
            "provider": provider,
            "required_live": required_live,
        }
    )
    report["reviews"].append(
        {
            "id": reviewer,
            "topic": topic,
            "provider": provider,
            "status": "pass",
            "packet_path": f"review-packets/{reviewer}.json",
            "prompt_path": f"review-prompts/{reviewer}.md",
            "role_contract_path": f"profiles/reviewer_roles/{role}.yaml",
            "report_path": f"reviewer-report.{reviewer}.json",
            "packet_prepared_at": "2026-06-22T10:00:00Z",
            "latest_material_change_at": "2026-06-22T09:30:00Z",
        }
    )
    report["external_review_evidence"].append(
        {
            "provider": "claude-code",
            "mode": "live",
            "required_live": True,
            "status": "pass",
            "normalized_report_path": f"reviewer-report.{reviewer}.json",
            "invocation_metadata_path": f"reviewer-invocation.{reviewer}.json",
            "raw_output": {
                "persistence": "redacted",
                "redaction_reason": "live output may contain local workspace context",
                "artifact_path": f"evidence/raw/{reviewer}.redacted-summary.md",
                "artifact_hash": text_sha(redacted_raw_summary(reviewer)),
            },
        }
    )
    return report


def reviewer_role_manifest(role: str) -> dict[str, object]:
    return {
        "kind": "reviewer_role",
        "name": role,
        "description": f"{role} reviewer fixture role.",
        "responsibilities": ["Review the packet and report candidate findings."],
    }


def review_prompt_policy() -> dict[str, object]:
    return {
        "baseline_same_prompt": True,
        "baseline_same_packet": True,
        "baseline_same_rubric": True,
        "focused_reviewers_require_explicit_focus_zone": True,
        "focus_zones_may_overlap": True,
        "all_reviewers_must_report_p0_p1_outside_focus": True,
    }


def base_review_packet(reviewer: str, provider: str, role: str) -> dict[str, object]:
    return {
        "agentsflow_version": "0.2",
        "workflow": "pr-merge-readiness",
        "run_id": "2026-06-22-pr-merge-readiness-example",
        "material_change_id": "pr-merge-readiness-example-change",
        "reviewer_role": role,
        "reviewer_instance_id": reviewer,
        "provider": provider,
        "review_packet_path": f"review-packets/{reviewer}.json",
        "review_goal": "Review PR readiness evidence for acceptance-blocking risks.",
        "review_profile": "homogeneous-plus-focused",
        "composition": "homogeneous-plus-focused",
        "prompt_policy": review_prompt_policy(),
        "role_contract": f"profiles/reviewer_roles/{role}.yaml",
        "context_policy": {
            "start_mode": "fresh_context",
            "fork_conversation_context": False,
            "allowed_context_sources": ["review_packet", "referenced_artifacts"],
        },
        "task_contract": {
            "path": "task.contract.md",
            "summary": "PR readiness fixture contract.",
        },
        "risk_surface_profile": {
            "selected_risk_surfaces": ["review_evidence_integrity"],
            "review_topology_source": "project_policy",
            "escalation_reason": "PR readiness requires review-evidence integrity checks.",
        },
        "failure_path_matrix": {
            "path": "task.contract.md#failure-path-matrix",
            "rows": [
                {
                    "id": "FPM-REVIEW-EVIDENCE-001",
                    "risk_surface": "review_evidence_integrity",
                    "path_class": "review gate evidence binding",
                    "evidence_binding": "review-packets/<reviewer>.json + reviewer-report.<reviewer>.json",
                    "status": "covered",
                }
            ],
        },
        "diff_summary": "Fixture PR readiness evidence.",
        "changed_files": ["scripts/repo_validation/pr_merge_readiness.py"],
        "verification_gate_report": {
            "path": "verification-gate-report.json",
            "summary": "Fixture green verification.",
        },
        "evidence_freshness": {
            "material_change_id": "pr-merge-readiness-example-change",
            "review_packet_generated_after_latest_green_gate": True,
            "stale_evidence_marked_or_excluded": True,
        },
        "evidence_summary": "Fixture evidence is present.",
        "known_blockers": [],
        "forbidden_actions": [
            "Do not use or assume forked orchestrator conversation context.",
            "Do not modify files.",
            "Do not run tests.",
            "Do not execute scripts.",
            "Do not produce patches.",
            "Do not update evidence.",
            "Return candidate findings only.",
        ],
        "output_schema": "schemas/reviewer-report.schema.json",
    }


def prepare_complete_evidence(root: Path) -> None:
    (root / "schemas").mkdir(parents=True, exist_ok=True)
    for schema_name in [
        "human-decisions.schema.json",
        "external-review-lite-invocation.schema.json",
        "external-review-lite-request.schema.json",
        "review-packet.schema.json",
        "reviewer-report.schema.json",
    ]:
        (root / "schemas" / schema_name).write_text(
            (ROOT / "schemas" / schema_name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    write_evidence(
        root,
        "evidence/repo-validation.log",
        "evidence/pytest.log",
    )
    write_github_publication_evidence(root)
    for source_path, matrix in [
        (DEFAULT_REQUIREMENTS_SOURCE, PR_REVIEW_MATRIX),
        (WITH_CLAUDE_REQUIREMENTS_SOURCE, PR_REVIEW_MATRIX + [CLAUDE_REVIEW]),
    ]:
        path = root / source_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(review_requirements_source_content(matrix), encoding="utf-8")
    (root / "task.contract.md").write_text("# Task Contract\n\nFixture contract.\n", encoding="utf-8")
    (root / "verification-gate-report.json").write_text(
        json.dumps(
            {
                "kind": "verification_gate_report",
                "result_state": "pass",
                "checks": [
                    {
                        "id": "repo-validation",
                        "command": "python3 scripts/validate_repo.py --root .",
                        "status": "pass",
                        "exit_code": 0,
                        "raw_log_path": "evidence/repo-validation.log",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "templates" / "review-prompts").mkdir(parents=True, exist_ok=True)
    (root / "templates" / "review-prompts" / "base.md").write_text(
        "Fixture base review prompt.\n",
        encoding="utf-8",
    )
    provider_config = root / "external-reviewers" / "claude-code.yaml"
    provider_config.parent.mkdir(parents=True, exist_ok=True)
    provider_config.write_text(PROVIDER_CONFIG_CONTENT, encoding="utf-8")
    (root / "rubric.json").write_text('{"same_output_schema":true}\n', encoding="utf-8")
    active_reviews = PR_REVIEW_MATRIX + [CLAUDE_REVIEW]
    for role in sorted({item[4] for item in active_reviews}):
        role_path = root / "profiles" / "reviewer_roles" / f"{role}.yaml"
        role_path.parent.mkdir(parents=True, exist_ok=True)
        role_path.write_text(
            yaml.safe_dump(reviewer_role_manifest(role), sort_keys=False),
            encoding="utf-8",
        )
    common_generalist_packet = base_review_packet("generalist-a", "internal-agent", "generalist")
    common_generalist_packet["topic"] = "generalist-readiness"
    for field in ["reviewer_instance_id", "review_packet_path", "provider"]:
        common_generalist_packet.pop(field, None)
    shared_content = {
        **common_generalist_packet,
        "excluded_envelope_fields": ["review_packet_path", "reviewer_instance_id", "provider"],
    }
    shared_content_path = root / "review-packets" / "shared-content.json"
    shared_content_path.parent.mkdir(parents=True, exist_ok=True)
    shared_content_path.write_text(json.dumps(shared_content, indent=2) + "\n", encoding="utf-8")
    for reviewer, topic, provider, _required_live, role in active_reviews:
        packet_path = root / "review-packets" / f"{reviewer}.json"
        packet_path.parent.mkdir(parents=True, exist_ok=True)
        packet = base_review_packet(reviewer, provider, role)
        packet["topic"] = topic
        if reviewer in {"adversarial-codex", "generalist-claude"}:
            packet["focus_zone"] = {
                "primary_focus": [
                    "false readiness claims",
                    "stale review evidence",
                    "external provider evidence",
                ],
                "may_report_outside_focus": True,
            }
        packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
        prompt_path = root / "review-prompts" / f"{reviewer}.md"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        role_data = reviewer_role_manifest(role)
        prompt_path.write_text(render_review_prompt(packet, role_data), encoding="utf-8")
        (root / f"reviewer-report.{reviewer}.json").write_text(
            json.dumps(
                {
                    "reviewer": {
                        "id": reviewer,
                        "provider": provider,
                        "role": role,
                        "model": "opus" if provider == "claude-code" else "codex",
                    },
                    "summary": "No blockers in fixture.",
                    "review_context": review_context(reviewer),
                    "findings": [],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if provider == "claude-code":
            redacted_summary_path = root / "evidence" / "raw" / f"{reviewer}.redacted-summary.md"
            redacted_summary_path.parent.mkdir(parents=True, exist_ok=True)
            redacted_summary_path.write_text(redacted_raw_summary(reviewer), encoding="utf-8")
            invocation = lite_invocation_metadata(root, reviewer)
            (root / f"reviewer-invocation.{reviewer}.json").write_text(
                json.dumps(invocation, indent=2) + "\n",
                encoding="utf-8",
            )
    (root / "human-decisions.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-22-pr-merge-readiness-example",
                "decisions": [
                    {
                        "decision_id": "merge.acceptance",
                        "phase_id": "final_human_merge_decision",
                        "question_ref": "merge.acceptance",
                        "answer": "accepted",
                        "status": "confirmed",
                        "answered_by": "human",
                        "classification": "blocking-material",
                        "affected_artifacts": ["pr-merge-readiness-report.json"],
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def evaluate(tmp_path: Path, report: dict) -> dict:
    prepare_complete_evidence(tmp_path)
    path = write_report(tmp_path, report)
    return load_evaluator()(tmp_path, path)


def test_complete_evidence_requires_human_decision(tmp_path: Path) -> None:
    report = complete_report()

    result = evaluate(tmp_path, report)

    assert result["state"] == "accepted_merge_ready"
    assert result["accepted"] is True
    assert result["missing_evidence"] == []
    assert result["blockers"] == []
    assert result["human_decision"]["required"] is True
    assert result["human_decision"]["status"] == "accepted"


def test_merge_readiness_rejects_schema_invalid_review_packet(tmp_path: Path) -> None:
    report = complete_report()
    prepare_complete_evidence(tmp_path)
    packet_path = tmp_path / "review-packets" / "adversarial-codex.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet.pop("review_goal")
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["accepted"] is False
    assert "review_packet_invalid:adversarial-codex" in result["blockers"]


def test_green_evidence_without_human_decision_is_not_accepted(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "awaiting_human_decision"
    report["human_decision"] = {"status": "missing"}

    result = evaluate(tmp_path, report)

    assert result["state"] == "awaiting_human_decision"
    assert result["accepted"] is False
    assert "human_decision_missing" in result["warnings"]
    assert "accepted_merge_ready" not in result.get("allowed_statuses", [])


def test_hash_bound_human_decision_accepts_candidate_report_without_self_status(
    tmp_path: Path,
) -> None:
    report = complete_report()
    report["status"] = "awaiting_human_decision"
    report["human_decision"] = {
        "status": "missing",
        "decision_id": "merge.acceptance",
        "path": "human-decisions.yaml",
    }

    result = evaluate(tmp_path, report)

    assert result["state"] == "accepted_merge_ready"
    assert result["accepted"] is True
    assert result["human_decision"]["status"] == "accepted"


def test_github_publication_is_required_before_human_decision(
    tmp_path: Path,
) -> None:
    report = complete_report()
    report.pop("github_publication")
    prepare_complete_evidence(tmp_path)
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "github_publication_evidence_missing" in result["blockers"]


def test_requested_github_publication_blocks_before_human_decision(tmp_path: Path) -> None:
    report = complete_report()
    report["github_publication"]["status"] = "requested"
    prepare_complete_evidence(tmp_path)
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "github_publication_evidence_missing" in result["blockers"]


def test_published_github_publication_with_evidence_can_pass(tmp_path: Path) -> None:
    report = complete_report()
    report["github_publication"] = {
        "status": "published",
        "required_for_merge_readiness": True,
        "publication_mode": "summary_comment",
        "target": "pull_request",
        "tool": "gh",
        "action": "pr comment",
        "body_path": "github-publication.md",
        "result_path": "github-publication-result.json",
        "pr": 1,
        "body_hash": text_sha(GITHUB_PUBLICATION_BODY),
        "url": "https://github.com/org/repo/pull/1#issuecomment-1",
    }
    prepare_complete_evidence(tmp_path)
    write_github_publication_evidence(tmp_path)
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "accepted_merge_ready"
    assert result["accepted"] is True
    assert result["blockers"] == []


def test_github_publication_must_be_required_for_merge_readiness(
    tmp_path: Path,
) -> None:
    report = complete_report()
    report["github_publication"]["required_for_merge_readiness"] = False

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "github_publication_evidence_invalid" in result["blockers"]


def test_github_publication_must_match_pull_request_number(tmp_path: Path) -> None:
    report = complete_report()
    report["github_publication"]["pr"] = 2

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "github_publication_evidence_invalid" in result["blockers"]


def test_github_publication_url_must_match_exact_pull_request_number(tmp_path: Path) -> None:
    report = complete_report()
    wrong_url = "https://github.com/org/repo/pull/10#issuecomment-1"
    report["github_publication"]["url"] = wrong_url
    prepare_complete_evidence(tmp_path)
    result_path = tmp_path / "github-publication-result.json"
    result_payload = json.loads(result_path.read_text(encoding="utf-8"))
    result_payload["url"] = wrong_url
    result_path.write_text(json.dumps(result_payload, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "github_publication_evidence_invalid" in result["blockers"]


def test_github_publication_url_must_match_repository(tmp_path: Path) -> None:
    report = complete_report()
    wrong_url = "https://github.com/other/repo/pull/1#issuecomment-1"
    report["github_publication"]["url"] = wrong_url
    prepare_complete_evidence(tmp_path)
    result_path = tmp_path / "github-publication-result.json"
    result_payload = json.loads(result_path.read_text(encoding="utf-8"))
    result_payload["url"] = wrong_url
    result_path.write_text(json.dumps(result_payload, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "github_publication_evidence_invalid" in result["blockers"]


def test_github_publication_url_must_be_comment_url(tmp_path: Path) -> None:
    report = complete_report()
    wrong_url = "https://github.com/org/repo/pull/1"
    report["github_publication"]["url"] = wrong_url
    prepare_complete_evidence(tmp_path)
    result_path = tmp_path / "github-publication-result.json"
    result_payload = json.loads(result_path.read_text(encoding="utf-8"))
    result_payload["url"] = wrong_url
    result_path.write_text(json.dumps(result_payload, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "github_publication_evidence_invalid" in result["blockers"]


def test_github_publication_body_hash_must_match_body_file(tmp_path: Path) -> None:
    report = complete_report()
    report["github_publication"]["body_hash"] = "sha256:" + "0" * 64

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "github_publication_evidence_invalid" in result["blockers"]


def test_github_publication_body_rejects_absolute_local_paths(tmp_path: Path) -> None:
    report = complete_report()
    prepare_complete_evidence(tmp_path)
    body_path = tmp_path / "github-publication.md"
    body_path.write_text("Leaked local path: /Users/alex/AgentsFlow/private.log\n", encoding="utf-8")
    report["github_publication"]["body_hash"] = file_sha(body_path)
    result_path = tmp_path / "github-publication-result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["body_hash"] = file_sha(body_path)
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "github_publication_evidence_invalid" in result["blockers"]


def test_github_publication_body_rejects_linux_absolute_local_paths(tmp_path: Path) -> None:
    report = complete_report()
    prepare_complete_evidence(tmp_path)
    body_path = tmp_path / "github-publication.md"
    body_path.write_text("Leaked local path: /home/alex/project/private.log\n", encoding="utf-8")
    report["github_publication"]["body_hash"] = file_sha(body_path)
    result_path = tmp_path / "github-publication-result.json"
    result_payload = json.loads(result_path.read_text(encoding="utf-8"))
    result_payload["body_hash"] = file_sha(body_path)
    result_path.write_text(json.dumps(result_payload, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "github_publication_evidence_invalid" in result["blockers"]


def test_published_github_publication_requires_result_artifact_url(
    tmp_path: Path,
) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    report["github_publication"] = {
        "status": "published",
        "required_for_merge_readiness": True,
        "publication_mode": "summary_comment",
        "target": "pull_request",
        "tool": "gh",
        "action": "pr comment",
        "body_path": "github-publication.md",
        "result_path": "github-publication-result.json",
        "pr": 1,
        "body_hash": text_sha(GITHUB_PUBLICATION_BODY),
        "url": "https://github.com/org/repo/pull/1#issuecomment-1",
    }
    prepare_complete_evidence(tmp_path)
    write_evidence(tmp_path, "github-publication.md")
    (tmp_path / "github-publication-result.json").write_text(
        json.dumps(
            {
                "provider": "github",
                "tool": "gh",
                "action": "pr comment",
                "status": "published",
                "pr": 1,
                "body_path": "github-publication.md",
                "body_hash": text_sha("evidence for github-publication.md\n"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "github_publication_evidence_missing" in result["blockers"]


def test_published_github_publication_requires_default_result_shape(
    tmp_path: Path,
) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    report["github_publication"] = {
        "status": "published",
        "required_for_merge_readiness": True,
        "publication_mode": "summary_comment",
        "target": "pull_request",
        "tool": "gh",
        "action": "pr comment",
        "body_path": "github-publication.md",
        "result_path": "github-publication-result.json",
        "pr": 1,
        "body_hash": text_sha(GITHUB_PUBLICATION_BODY),
        "url": "https://github.com/org/repo/pull/1#issuecomment-1",
    }
    prepare_complete_evidence(tmp_path)
    write_evidence(tmp_path, "github-publication.md")
    (tmp_path / "github-publication-result.json").write_text(
        '{"provider":"github","tool":"gh","action":"pr review","status":"published"}\n',
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "github_publication_evidence_invalid" in result["blockers"]


def test_missing_required_evidence_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["checks"][0]["evidence_path"] = "evidence/missing-repo-validation.log"

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "evidence/missing-repo-validation.log" in result["missing_evidence"]
    assert "missing_required_evidence" in result["blockers"]


def test_failed_check_status_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    report["checks"][0]["status"] = "fail"

    result = evaluate(tmp_path, report)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "failed_check:repo-validation" in result["blockers"]


def test_failed_review_status_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    report["reviews"][0]["status"] = "blocked"

    result = evaluate(tmp_path, report)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "failed_review:generalist-a" in result["blockers"]


def test_missing_required_review_topology_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    report["reviews"] = []
    report["external_review_evidence"] = []

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "missing_required_review:generalist-a" in result["blockers"]
    assert "missing_required_review:generalist-b" in result["blockers"]
    assert "missing_required_review:adversarial-codex" in result["blockers"]
    assert "live_claude_absent" not in result["blockers"]


def test_underdeclared_pr_merge_review_topology_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    report["review_requirements"]["required_reviews"] = report["review_requirements"]["required_reviews"][:2]
    report["reviews"] = report["reviews"][:2]
    report["external_review_evidence"] = report["external_review_evidence"][:1]

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "review_requirements_source_mismatch" in result["blockers"]
    assert "missing_required_review:adversarial-codex" not in result["blockers"]


def test_single_reviewer_pr_merge_review_topology_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    report["review_requirements"]["required_reviews"] = report["review_requirements"]["required_reviews"][:1]
    report["reviews"] = report["reviews"][:1]
    report["external_review_evidence"] = []

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "review_requirements_minimum_not_met" in result["blockers"]


def test_missing_review_requirements_source_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    report["review_requirements"].pop("source")

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "review_requirements_source_missing" in result["blockers"]


def test_review_requirements_source_hash_mismatch_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    report["review_requirements"]["source"]["artifact_hash"] = "sha256:" + "0" * 64

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "review_requirements_source_hash_mismatch" in result["blockers"]


def test_review_requirements_source_requires_normalized_artifact_kind(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    prepare_complete_evidence(tmp_path)
    source_path = tmp_path / DEFAULT_REQUIREMENTS_SOURCE
    source = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    source.pop("artifact_kind")
    source_path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
    report["review_requirements"]["source"]["artifact_hash"] = file_sha(source_path)
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "review_requirements_source_invalid" in result["blockers"]


def test_review_packet_missing_green_gate_reference_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    prepare_complete_evidence(tmp_path)
    packet_path = tmp_path / "review-packets" / "generalist-a.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["verification_gate_report"]["path"] = "missing-verification-gate-report.json"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "review_packet_invalid:generalist-a" in result["blockers"]


def test_review_packet_failed_green_gate_reference_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    prepare_complete_evidence(tmp_path)
    gate_path = tmp_path / "verification-gate-report.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["result_state"] = "fail"
    gate_path.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "review_packet_invalid:generalist-a" in result["blockers"]


def test_review_packet_pass_gate_with_failed_check_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    prepare_complete_evidence(tmp_path)
    gate_path = tmp_path / "verification-gate-report.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate["result_state"] = "pass"
    gate["checks"] = [{"id": "repo-validation", "status": "fail", "exit_code": 1}]
    gate_path.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "review_packet_invalid:generalist-a" in result["blockers"]


def test_review_packet_failed_markdown_green_gate_reference_blocks_readiness(
    tmp_path: Path,
) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    prepare_complete_evidence(tmp_path)
    gate_path = tmp_path / "verification-gate-report.md"
    gate_path.write_text("# Verification Gate Report\n\nStatus: fail\n", encoding="utf-8")
    packet_path = tmp_path / "review-packets" / "generalist-a.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["verification_gate_report"]["path"] = "verification-gate-report.md"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "review_packet_invalid:generalist-a" in result["blockers"]


def test_review_packet_nested_material_change_mismatch_blocks_readiness(
    tmp_path: Path,
) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    prepare_complete_evidence(tmp_path)
    packet_path = tmp_path / "review-packets" / "generalist-a.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["evidence_freshness"]["material_change_id"] = "older-change"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "review_packet_context_mismatch:generalist-a:evidence_freshness.material_change_id" in result["blockers"]


def test_review_packet_reviewer_identity_mismatch_blocks_readiness(
    tmp_path: Path,
) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    prepare_complete_evidence(tmp_path)
    packet_path = tmp_path / "review-packets" / "generalist-a.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["reviewer_instance_id"] = "generalist-b"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "review_packet_context_mismatch:generalist-a:reviewer_instance_id" in result["blockers"]


def test_required_live_false_for_claude_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_missing_evidence"
    for required in report["review_requirements"]["required_reviews"]:
        if required["id"] == "generalist-claude":
            required["required_live"] = False

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "required_live_claude_not_declared:generalist-claude" in result["blockers"]


def test_required_review_role_binding_blocks_wrong_role(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    report["reviews"][0]["role_contract_path"] = "profiles/reviewer_roles/architecture.yaml"
    prepare_complete_evidence(tmp_path)
    (tmp_path / "reviewer-report.generalist-a.json").write_text(
        json.dumps(
            {
                "reviewer": {
                    "id": "generalist-a",
                    "provider": "internal-agent",
                    "role": "architecture",
                    "model": "codex",
                },
                "summary": "Wrong-role reviewer fixture.",
                "findings": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "required_review_mismatch:generalist-a:role_contract_path" in result["blockers"]
    assert "reviewer_report_role_mismatch:generalist-a" in result["blockers"]


def test_mock_external_review_is_not_live_claude_evidence(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    for entry in report["external_review_evidence"]:
        entry["mode"] = "mock"

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "live_claude_absent" in result["blockers"]
    assert result["external_review"]["claude_code_live"] is False


def test_omitted_external_review_evidence_for_claude_review_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    report["external_review_evidence"] = []

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_evidence_missing:generalist-claude" in result["blockers"]


def test_lite_claude_invocation_satisfies_pr_readiness_without_strict_artifacts(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    prepare_complete_evidence(tmp_path)
    invocation_path = tmp_path / "reviewer-invocation.generalist-claude.json"
    invocation_path.write_text(
        json.dumps(lite_invocation_metadata(tmp_path), indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "accepted_merge_ready"
    assert result["accepted"] is True


def test_mock_invocation_metadata_does_not_satisfy_live_claude_evidence(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    invocation = lite_invocation_metadata(tmp_path)
    invocation["execution_mode"] = "mock"
    (tmp_path / "reviewer-invocation.generalist-claude.json").write_text(
        json.dumps(invocation, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_not_real:generalist-claude" in result["blockers"]


def test_missing_claude_forbidden_env_guardrails_block_readiness(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    invocation = json.loads((tmp_path / "reviewer-invocation.generalist-claude.json").read_text(encoding="utf-8"))
    invocation["forbidden_env_checked"] = ["ANTHROPIC_API_KEY"]
    invocation["normalized_output_hash"] = file_sha(tmp_path / "reviewer-report.generalist-claude.json")
    invocation["input_hash"] = file_sha(tmp_path / "review-packets" / "generalist-claude.json")
    invocation["prompt_hash"] = file_sha(tmp_path / "review-prompts" / "generalist-claude.md")
    invocation["schema_hash"] = file_sha(tmp_path / "schemas" / "reviewer-report.schema.json")
    (tmp_path / "reviewer-invocation.generalist-claude.json").write_text(
        json.dumps(invocation, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_guardrail_forbidden_env_missing:generalist-claude" in result["blockers"]


def test_invalid_claude_provider_config_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    provider_config = tmp_path / "external-reviewers" / "claude-code.yaml"
    provider_config.write_text("provider: claude-code\n", encoding="utf-8")
    invocation_path = tmp_path / "reviewer-invocation.generalist-claude.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation["provider_config_hash"] = file_sha(provider_config)
    invocation_path.write_text(json.dumps(invocation, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_provider_config_invalid:generalist-claude" in result["blockers"]


def test_missing_claude_wrapper_metadata_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    invocation = json.loads((tmp_path / "reviewer-invocation.generalist-claude.json").read_text(encoding="utf-8"))
    invocation.pop("wrapper")
    invocation["normalized_output_hash"] = file_sha(tmp_path / "reviewer-report.generalist-claude.json")
    invocation["input_hash"] = file_sha(tmp_path / "review-packets" / "generalist-claude.json")
    invocation["prompt_hash"] = file_sha(tmp_path / "review-prompts" / "generalist-claude.md")
    invocation["schema_hash"] = file_sha(tmp_path / "schemas" / "reviewer-report.schema.json")
    (tmp_path / "reviewer-invocation.generalist-claude.json").write_text(
        json.dumps(invocation, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_invocation_invalid:generalist-claude" in result["blockers"]
    assert "external_review_guardrail_wrapper_missing:generalist-claude" in result["blockers"]


def test_plan_mode_claude_invocation_metadata_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    invocation = json.loads((tmp_path / "reviewer-invocation.generalist-claude.json").read_text(encoding="utf-8"))
    invocation["permission_mode"] = "plan"
    invocation["prompt_transport"] = "file"
    invocation["tools"] = "Read"
    invocation["normalized_output_hash"] = file_sha(tmp_path / "reviewer-report.generalist-claude.json")
    (tmp_path / "reviewer-invocation.generalist-claude.json").write_text(
        json.dumps(invocation, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_invocation_invalid:generalist-claude" in result["blockers"]
    assert "external_review_invocation_unsafe_permission_mode:generalist-claude" in result["blockers"]


def test_claude_invocation_hash_mismatch_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    invocation = json.loads((tmp_path / "reviewer-invocation.generalist-claude.json").read_text(encoding="utf-8"))
    invocation["normalized_output_hash"] = "sha256:" + "0" * 64
    (tmp_path / "reviewer-invocation.generalist-claude.json").write_text(
        json.dumps(invocation, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_normalized_output_hash_mismatch:generalist-claude" in result["blockers"]


def test_claude_invocation_role_mismatch_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    invocation = json.loads((tmp_path / "reviewer-invocation.generalist-claude.json").read_text(encoding="utf-8"))
    invocation["reviewer_role"] = "architecture"
    invocation["normalized_output_hash"] = file_sha(tmp_path / "reviewer-report.generalist-claude.json")
    (tmp_path / "reviewer-invocation.generalist-claude.json").write_text(
        json.dumps(invocation, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_invocation_role_mismatch:generalist-claude" in result["blockers"]


def test_claude_lite_request_material_change_mismatch_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    request_path = tmp_path / "external-review-lite" / "external-review-lite-request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request["material_change_id"] = "older-material-change"
    request_path.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
    invocation_path = tmp_path / "reviewer-invocation.generalist-claude.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation["review_request_hash"] = file_sha(request_path)
    invocation["input_hash"] = file_sha(request_path)
    invocation["normalized_output_hash"] = file_sha(tmp_path / "reviewer-report.generalist-claude.json")
    invocation_path.write_text(json.dumps(invocation, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_request_context_mismatch:generalist-claude:material_change_id" in result["blockers"]


def test_claude_lite_request_reviewer_mismatch_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    request_path = tmp_path / "external-review-lite" / "external-review-lite-request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request["reviewer"]["id"] = "other-claude-reviewer"
    request_path.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
    invocation_path = tmp_path / "reviewer-invocation.generalist-claude.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation["review_request_hash"] = file_sha(request_path)
    invocation["input_hash"] = file_sha(request_path)
    invocation["normalized_output_hash"] = file_sha(tmp_path / "reviewer-report.generalist-claude.json")
    invocation_path.write_text(json.dumps(invocation, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_request_reviewer_mismatch:generalist-claude" in result["blockers"]


def test_claude_lite_request_missing_artifact_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    (tmp_path / "evidence" / "repo-validation.log").unlink()
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "external_review_request_artifact_missing:generalist-claude" in result["blockers"]


def test_claude_lite_request_artifact_hash_mismatch_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    (tmp_path / "evidence" / "repo-validation.log").write_text(
        "Repository validation output was changed after external review.\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_request_artifact_hash_mismatch:generalist-claude" in result["blockers"]


def test_claude_reviewer_report_context_mismatch_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    report_path = tmp_path / "reviewer-report.generalist-claude.json"
    reviewer_report = json.loads(report_path.read_text(encoding="utf-8"))
    reviewer_report["review_context"]["run_id"] = "older-run"
    report_path.write_text(json.dumps(reviewer_report, indent=2) + "\n", encoding="utf-8")
    invocation_path = tmp_path / "reviewer-invocation.generalist-claude.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation["normalized_output_hash"] = file_sha(report_path)
    invocation_path.write_text(json.dumps(invocation, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "reviewer_report_context_mismatch:generalist-claude" in result["blockers"]


def test_claude_invocation_input_hash_mismatch_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    invocation = json.loads((tmp_path / "reviewer-invocation.generalist-claude.json").read_text(encoding="utf-8"))
    invocation["input_hash"] = "sha256:" + "0" * 64
    invocation["normalized_output_hash"] = file_sha(tmp_path / "reviewer-report.generalist-claude.json")
    invocation["prompt_hash"] = file_sha(tmp_path / "review-prompts" / "generalist-claude.md")
    invocation["schema_hash"] = file_sha(tmp_path / "schemas" / "reviewer-report.schema.json")
    (tmp_path / "reviewer-invocation.generalist-claude.json").write_text(
        json.dumps(invocation, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_input_hash_mismatch:generalist-claude" in result["blockers"]


def test_malformed_reviewer_report_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    prepare_complete_evidence(tmp_path)
    (tmp_path / "reviewer-report.generalist-a.json").write_text(
        json.dumps({"summary": "missing reviewer and findings"}) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "reviewer_report_invalid:generalist-a" in result["blockers"]


def test_internal_reviewer_report_without_current_context_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    prepare_complete_evidence(tmp_path)
    stale_report = {
        "reviewer": {
            "id": "generalist-a",
            "provider": "internal-agent",
            "role": "generalist",
            "model": "codex",
        },
        "summary": "Old report with matching reviewer identity but no current packet context.",
        "findings": [],
    }
    (tmp_path / "reviewer-report.generalist-a.json").write_text(
        json.dumps(stale_report, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "reviewer_report_context_missing:generalist-a" in result["blockers"]


def test_internal_reviewer_report_wrong_run_context_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    prepare_complete_evidence(tmp_path)
    stale_context = review_context("generalist-a")
    stale_context["run_id"] = "older-run"
    stale_report = {
        "reviewer": {
            "id": "generalist-a",
            "provider": "internal-agent",
            "role": "generalist",
            "model": "codex",
        },
        "review_context": stale_context,
        "summary": "Old report with matching packet path but wrong run.",
        "findings": [],
    }
    (tmp_path / "reviewer-report.generalist-a.json").write_text(
        json.dumps(stale_report, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "reviewer_report_context_mismatch:generalist-a" in result["blockers"]


def test_internal_reviewer_report_missing_reviewer_instance_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    prepare_complete_evidence(tmp_path)
    incomplete_context = review_context("generalist-a")
    incomplete_context.pop("reviewer_instance_id")
    stale_report = {
        "reviewer": {
            "id": "generalist-a",
            "provider": "internal-agent",
            "role": "generalist",
            "model": "codex",
        },
        "review_context": incomplete_context,
        "summary": "Old report without the assigned reviewer instance in context.",
        "findings": [],
    }
    (tmp_path / "reviewer-report.generalist-a.json").write_text(
        json.dumps(stale_report, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "reviewer_report_context_mismatch:generalist-a" in result["blockers"]


def test_old_packet_and_matching_internal_report_pair_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    prepare_complete_evidence(tmp_path)

    packet_path = tmp_path / "review-packets" / "generalist-a.json"
    old_packet = json.loads(packet_path.read_text(encoding="utf-8"))
    old_packet["run_id"] = "older-run"
    old_packet["material_change_id"] = "older-change"
    packet_path.write_text(
        json.dumps(old_packet, indent=2) + "\n",
        encoding="utf-8",
    )
    old_report = {
        "reviewer": {
            "id": "generalist-a",
            "provider": "internal-agent",
            "role": "generalist",
            "model": "codex",
        },
        "review_context": {
            "run_id": "older-run",
            "material_change_id": "older-change",
            "review_packet_path": "review-packets/generalist-a.json",
            "reviewer_instance_id": "generalist-a",
        },
        "summary": "Old packet and old report are internally consistent.",
        "findings": [],
    }
    (tmp_path / "reviewer-report.generalist-a.json").write_text(
        json.dumps(old_report, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "review_packet_context_mismatch:generalist-a:run_id" in result["blockers"]
    assert "review_packet_context_mismatch:generalist-a:material_change_id" in result["blockers"]


def test_reviewer_report_p1_omitted_from_candidate_findings_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    prepare_complete_evidence(tmp_path)
    (tmp_path / "reviewer-report.generalist-a.json").write_text(
        json.dumps(
            {
                "reviewer": {
                    "id": "generalist-a",
                    "provider": "internal-agent",
                    "role": "generalist",
                },
                "summary": "Found blocker.",
                "review_context": review_context("generalist-a"),
                "findings": [
                    {
                        "id": "P1-SOURCE",
                        "severity": "P1",
                        "title": "Source blocker",
                        "evidence": ["example evidence"],
                        "status": "candidate-unvalidated",
                        **grounded_blocker_fields(),
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "unhandled_source_blocking_finding:generalist-a:P1-SOURCE" in result["blockers"]


def test_reviewer_report_mandatory_gap_omitted_from_candidate_findings_blocks_readiness(
    tmp_path: Path,
) -> None:
    report = complete_report()
    report["status"] = "rejected"
    prepare_complete_evidence(tmp_path)
    (tmp_path / "reviewer-report.generalist-a.json").write_text(
        json.dumps(
            {
                "reviewer": {
                    "id": "generalist-a",
                    "provider": "internal-agent",
                    "role": "generalist",
                },
                "summary": "Found missing mandatory evidence.",
                "review_context": review_context("generalist-a"),
                "findings": [
                    {
                        "id": "MANDATORY-GAP",
                        "severity": "NOTE",
                        "title": "Missing mandatory evidence",
                        "evidence": ["required gate evidence is absent"],
                        "status": "candidate-unvalidated",
                        "mandatory_evidence_gap": True,
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "unhandled_source_blocking_finding:generalist-a:MANDATORY-GAP" in result["blockers"]


def test_reviewer_report_p1_can_be_rejected_with_calibration(tmp_path: Path) -> None:
    report = complete_report()
    report["candidate_findings"] = [
        {
            "id": "P1-SOURCE",
            "severity": "P3",
            "status": "rejected",
            "validation_rationale": "Main agent judged this irrelevant.",
            "source_findings": [{"reviewer": "generalist-a", "id": "P1-SOURCE"}],
        }
    ]
    prepare_complete_evidence(tmp_path)
    (tmp_path / "reviewer-report.generalist-a.json").write_text(
        json.dumps(
            {
                "reviewer": {
                    "id": "generalist-a",
                    "provider": "internal-agent",
                    "role": "generalist",
                    "model": "codex",
                },
                "summary": "Found blocker.",
                "review_context": review_context("generalist-a"),
                "findings": [
                    {
                        "id": "P1-SOURCE",
                        "severity": "P1",
                        "title": "Source blocker",
                        "evidence": ["example evidence"],
                        "status": "candidate-unvalidated",
                        **grounded_blocker_fields(),
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "accepted_merge_ready"
    assert result["accepted"] is True
    assert "unhandled_source_blocking_finding:generalist-a:P1-SOURCE" not in result["blockers"]
    assert "unresolved_blocking_finding:P1-SOURCE" not in result["blockers"]


def test_reviewer_report_p1_rejection_requires_calibration(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    report["candidate_findings"] = [
        {
            "id": "P1-SOURCE",
            "severity": "P3",
            "status": "rejected",
            "source_findings": [{"reviewer": "generalist-a", "id": "P1-SOURCE"}],
        }
    ]
    prepare_complete_evidence(tmp_path)
    (tmp_path / "reviewer-report.generalist-a.json").write_text(
        json.dumps(
            {
                "reviewer": {
                    "id": "generalist-a",
                    "provider": "internal-agent",
                    "role": "generalist",
                    "model": "codex",
                },
                "summary": "Found blocker.",
                "review_context": review_context("generalist-a"),
                "findings": [
                    {
                        "id": "P1-SOURCE",
                        "severity": "P1",
                        "title": "Source blocker",
                        "evidence": ["example evidence"],
                        "status": "candidate-unvalidated",
                        **grounded_blocker_fields(),
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "source_finding_calibration_reason_missing:generalist-a:P1-SOURCE" in result["blockers"]


def test_reviewer_report_p1_cannot_disappear_as_duplicate_without_resolution(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    report["candidate_findings"] = [
        {
            "id": "P1-SOURCE",
            "severity": "P1",
            "status": "duplicate",
            "source_findings": [{"reviewer": "generalist-a", "id": "P1-SOURCE"}],
            **grounded_blocker_fields(),
        }
    ]
    prepare_complete_evidence(tmp_path)
    (tmp_path / "reviewer-report.generalist-a.json").write_text(
        json.dumps(
            {
                "reviewer": {
                    "id": "generalist-a",
                    "provider": "internal-agent",
                    "role": "generalist",
                    "model": "codex",
                },
                "summary": "Found blocker.",
                "review_context": review_context("generalist-a"),
                "findings": [
                    {
                        "id": "P1-SOURCE",
                        "severity": "P1",
                        "title": "Source blocker",
                        "evidence": ["example evidence"],
                        "status": "candidate-unvalidated",
                        **grounded_blocker_fields(),
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "unresolved_duplicate_blocking_finding:P1-SOURCE" in result["blockers"]


def test_duplicate_local_source_finding_ids_require_reviewer_identity(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P1",
            "status": "accepted",
            "source_findings": [{"reviewer": "generalist-a", "id": "F-001"}],
            **grounded_blocker_fields(),
        }
    ]
    prepare_complete_evidence(tmp_path)
    for reviewer, provider, role in [
        ("generalist-a", "internal-agent", "generalist"),
        ("generalist-b", "internal-agent", "generalist"),
    ]:
        (tmp_path / f"reviewer-report.{reviewer}.json").write_text(
            json.dumps(
                {
                    "reviewer": {
                        "id": reviewer,
                        "provider": provider,
                        "role": role,
                        "model": "codex",
                    },
                    "summary": "Found blocker.",
                    "review_context": review_context(reviewer),
                    "findings": [
                        {
                            "id": "F-001",
                            "severity": "P1",
                            "title": f"Source blocker from {reviewer}",
                            "evidence": ["example evidence"],
                            "status": "candidate-unvalidated",
                            **grounded_blocker_fields(),
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "unhandled_source_blocking_finding:generalist-b:F-001" in result["blockers"]


def test_sensitive_raw_external_output_requires_redaction_reason(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_sensitive_raw_evidence"
    report["external_review_evidence"][0]["raw_output"] = {
        "persistence": "redacted",
    }

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_sensitive_raw_evidence"
    assert result["accepted"] is False
    assert "raw_redaction_reason_missing" in result["blockers"]


def test_redacted_live_external_output_requires_redacted_artifact(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_sensitive_raw_evidence"
    report["external_review_evidence"][0]["raw_output"].pop("artifact_path")
    report["external_review_evidence"][0]["raw_output"].pop("artifact_hash")
    prepare_complete_evidence(tmp_path)
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_sensitive_raw_evidence"
    assert result["accepted"] is False
    assert "raw_output_artifact_missing:generalist-claude" in result["blockers"]


def test_redacted_live_external_output_does_not_require_raw_provider_artifact(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    prepare_complete_evidence(tmp_path)
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "accepted_merge_ready"
    assert result["accepted"] is True
    assert "external_review_raw_output_missing:generalist-claude" not in result["blockers"]


def test_redacted_live_external_output_rejects_persisted_raw_provider_artifact(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_sensitive_raw_evidence"
    prepare_complete_evidence(tmp_path)
    attach_raw_provider_output(tmp_path, "generalist-claude")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_sensitive_raw_evidence"
    assert result["accepted"] is False
    assert "raw_output_unexpected_persisted:generalist-claude" in result["blockers"]


def test_redacted_live_external_output_rejects_invocation_normalization_raw_source(
    tmp_path: Path,
) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_sensitive_raw_evidence"
    prepare_complete_evidence(tmp_path)
    raw_path = tmp_path / "raw" / "generalist-claude.raw.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text('{"result":"raw"}\n', encoding="utf-8")
    invocation_path = tmp_path / "reviewer-invocation.generalist-claude.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation["normalization"] = {
        "method": "native-json",
        "source_path": "raw/generalist-claude.raw.json",
        "source_hash": file_sha(raw_path),
        "output_path": "reviewer-report.generalist-claude.json",
        "output_hash": file_sha(tmp_path / "reviewer-report.generalist-claude.json"),
        "schema_validation": "passed",
        "normalized_by": "scripts/reviewers/run_external_review_lite.py",
    }
    invocation_path.write_text(json.dumps(invocation, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_sensitive_raw_evidence"
    assert result["accepted"] is False
    assert "raw_output_unexpected_persisted:generalist-claude" in result["blockers"]


def test_redacted_live_external_output_rejects_report_normalization_raw_source(
    tmp_path: Path,
) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_sensitive_raw_evidence"
    prepare_complete_evidence(tmp_path)
    raw_path = tmp_path / "raw" / "generalist-claude.raw.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text('{"result":"raw"}\n', encoding="utf-8")
    reviewer_report_path = tmp_path / "reviewer-report.generalist-claude.json"
    reviewer_report = json.loads(reviewer_report_path.read_text(encoding="utf-8"))
    reviewer_report["normalization"] = {
        "method": "native-json",
        "source_path": "raw/generalist-claude.raw.json",
        "source_hash": file_sha(raw_path),
        "schema_validation": "passed",
        "normalized_by": "scripts/reviewers/run_external_review_lite.py",
    }
    reviewer_report_path.write_text(json.dumps(reviewer_report, indent=2) + "\n", encoding="utf-8")
    invocation_path = tmp_path / "reviewer-invocation.generalist-claude.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation["normalized_output_hash"] = file_sha(reviewer_report_path)
    invocation_path.write_text(json.dumps(invocation, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_sensitive_raw_evidence"
    assert result["accepted"] is False
    assert "raw_output_unexpected_persisted:generalist-claude" in result["blockers"]


def test_raw_live_external_output_requires_non_sensitive_declaration(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_sensitive_raw_evidence"
    report["external_review_evidence"][0]["raw_output"] = {
        "persistence": "raw",
    }
    prepare_complete_evidence(tmp_path)
    attach_raw_provider_output(tmp_path, "generalist-claude")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_sensitive_raw_evidence"
    assert result["accepted"] is False
    assert "raw_output_non_sensitive_declaration_missing" in result["blockers"]


def test_non_sensitive_raw_live_external_output_is_hash_bound(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["external_review_evidence"][0]["raw_output"] = {
        "persistence": "raw",
        "non_sensitive": True,
    }
    prepare_complete_evidence(tmp_path)
    attach_raw_provider_output(tmp_path, "generalist-claude")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "accepted_merge_ready"
    assert result["accepted"] is True
    assert result["blockers"] == []


def test_non_sensitive_raw_live_external_output_hash_mismatch_blocks(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    report["external_review_evidence"][0]["raw_output"] = {
        "persistence": "raw",
        "non_sensitive": True,
    }
    prepare_complete_evidence(tmp_path)
    attach_raw_provider_output(tmp_path, "generalist-claude")
    invocation_path = tmp_path / "reviewer-invocation.generalist-claude.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation["raw_output_hash"] = "sha256:" + "0" * 64
    invocation_path.write_text(json.dumps(invocation, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_raw_output_hash_mismatch:generalist-claude" in result["blockers"]


def test_non_sensitive_raw_live_external_output_missing_hash_blocks_with_precise_label(
    tmp_path: Path,
) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_external_review"
    report["external_review_evidence"][0]["raw_output"] = {
        "persistence": "raw",
        "non_sensitive": True,
    }
    prepare_complete_evidence(tmp_path)
    attach_raw_provider_output(tmp_path, "generalist-claude")
    invocation_path = tmp_path / "reviewer-invocation.generalist-claude.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation.pop("raw_output_hash")
    invocation_path.write_text(json.dumps(invocation, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_invocation_missing_raw_output_hash:generalist-claude" in result["blockers"]
    assert "external_review_raw_output_hash_mismatch:generalist-claude" not in result["blockers"]


def test_live_external_output_not_persisted_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    add_claude_review(report)
    report["status"] = "blocked_sensitive_raw_evidence"
    report["external_review_evidence"][0]["raw_output"] = {
        "persistence": "not_persisted",
    }

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_sensitive_raw_evidence"
    assert result["accepted"] is False
    assert "raw_output_not_persisted:generalist-claude" in result["blockers"]


def test_fixture_report_is_not_real_merge_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "incomplete"
    report["fixture"] = {
        "enabled": True,
        "not_real_readiness_evidence": True,
    }

    result = evaluate(tmp_path, report)

    assert result["state"] == "incomplete"
    assert result["accepted"] is False
    assert "fixture_not_real_readiness_evidence" in result["warnings"]


def test_accepted_blocker_finding_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P1",
            "status": "accepted",
            **grounded_blocker_fields(),
        }
    ]

    result = evaluate(tmp_path, report)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "unresolved_blocking_finding:F-001" in result["blockers"]


def test_validated_blocker_severity_overrides_lower_candidate_severity(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P3",
            "validated_severity": "P1",
            "status": "accepted",
            "evidence": ["finding-validation-report.md records the validated blocker"],
            "blocker_path": "validated readiness finding -> required merge gate -> unsafe acceptance",
            "acceptance_impact": "Accepting the branch unchanged would approve a validated blocker.",
        }
    ]

    result = evaluate(tmp_path, report)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "unresolved_blocking_finding:F-001" in result["blockers"]


def test_accepted_p1_without_blocker_path_is_invalid_calibration(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P1",
            "status": "accepted",
        }
    ]

    result = evaluate(tmp_path, report)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "finding_blocker_path_missing:F-001" in result["blockers"]
    assert "unresolved_blocking_finding:F-001" not in result["blockers"]


def test_needs_more_evidence_blocker_finding_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P1",
            "status": "needs-more-evidence",
            **grounded_blocker_fields(),
        }
    ]

    result = evaluate(tmp_path, report)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "unresolved_blocking_finding:F-001" in result["blockers"]


def test_mandatory_evidence_gap_blocks_regardless_of_candidate_severity(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "NOTE",
            "status": "needs-more-evidence",
            "mandatory_evidence_gap": True,
        }
    ]

    result = evaluate(tmp_path, report)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "unresolved_blocking_finding:F-001" in result["blockers"]


def test_needs_more_evidence_p1_without_blocker_path_is_invalid_calibration(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P1",
            "status": "needs-more-evidence",
        }
    ]

    result = evaluate(tmp_path, report)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "finding_blocker_path_missing:F-001" in result["blockers"]
    assert "unresolved_blocking_finding:F-001" not in result["blockers"]


def test_rejected_p1_without_blocker_path_is_calibrated_non_blocking(tmp_path: Path) -> None:
    report = complete_report()
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P1",
            "status": "rejected",
            "validation_rationale": "No grounded blocker path; reviewer severity was candidate-only.",
        }
    ]

    result = evaluate(tmp_path, report)

    assert result["state"] == "accepted_merge_ready"
    assert result["accepted"] is True


def test_rejected_blocker_findings_fail_closed_in_pr_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P1",
            "status": "rejected",
            "validation_rationale": "Main agent judged this irrelevant.",
            **grounded_blocker_fields(),
        }
    ]

    result = evaluate(tmp_path, report)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "unresolved_blocking_finding:F-001" in result["blockers"]


def test_collision_control_claim_does_not_clear_rejected_blocker(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P1",
            "status": "rejected",
            **grounded_blocker_fields(),
            "collision_control": {"status": "completed"},
        }
    ]

    result = evaluate(tmp_path, report)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "unresolved_blocking_finding:F-001" in result["blockers"]


def test_review_packet_older_than_material_change_is_stale(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_stale_review"
    report["reviews"][0]["packet_prepared_at"] = "2026-06-22T08:00:00Z"
    report["reviews"][0]["latest_material_change_at"] = "2026-06-22T09:30:00Z"

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_stale_review"
    assert result["accepted"] is False
    assert "stale_review:generalist-a" in result["blockers"]
    assert result["stale_reviews"] == ["generalist-a"]


def test_malformed_review_timestamp_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_stale_review"
    report["reviews"][0]["packet_prepared_at"] = "not-a-timestamp"

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_stale_review"
    assert result["accepted"] is False
    assert "invalid_review_timestamp:generalist-a" in result["blockers"]


def test_mixed_timezone_review_timestamps_do_not_false_accept(tmp_path: Path) -> None:
    report = complete_report()
    report["reviews"][0]["packet_prepared_at"] = "2026-06-22T10:00:00"
    report["reviews"][0]["latest_material_change_at"] = "2026-06-22T09:30:00Z"

    result = evaluate(tmp_path, report)

    assert result["state"] == "accepted_merge_ready"
    assert result["accepted"] is True
    assert not any(blocker.startswith("invalid_review_timestamp:") for blocker in result["blockers"])


def test_accepted_human_decision_requires_record_path_and_matching_human_decision(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    report["human_decision"] = {"status": "accepted", "decision_id": "merge.acceptance"}

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "human_decision_record_missing" in result["blockers"]


def test_accepted_human_decision_rejects_non_matching_record(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "awaiting_human_decision"
    prepare_complete_evidence(tmp_path)
    (tmp_path / "human-decisions.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "decisions": [
                    {
                        "decision_id": "merge.acceptance",
                        "status": "accepted",
                        "answered_by": "agent",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "human_decision_record_invalid" in result["blockers"]


def test_accepted_human_decision_rejects_legacy_ad_hoc_record(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "awaiting_human_decision"
    prepare_complete_evidence(tmp_path)
    (tmp_path / "human-decisions.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "decisions": [
                    {
                        "decision_id": "merge.acceptance",
                        "status": "accepted",
                        "answered_by": "human",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "human_decision_record_invalid" in result["blockers"]


def test_accepted_human_decision_rejects_unrelated_confirmed_decision(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "awaiting_human_decision"
    prepare_complete_evidence(tmp_path)
    (tmp_path / "human-decisions.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-22-pr-merge-readiness-example",
                "decisions": [
                    {
                        "decision_id": "merge.acceptance",
                        "phase_id": "contract_acceptance",
                        "question_ref": "contract.acceptance",
                        "answer": "accepted",
                        "status": "confirmed",
                        "answered_by": "human",
                        "classification": "blocking-material",
                        "affected_artifacts": ["task.contract.md"],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "human_decision_record_invalid" in result["blockers"]


def test_accepted_human_decision_rejects_preliminary_merge_decision_phase(
    tmp_path: Path,
) -> None:
    report = complete_report()
    report["status"] = "awaiting_human_decision"
    prepare_complete_evidence(tmp_path)
    human_decisions_path = tmp_path / "human-decisions.yaml"
    human_decisions = yaml.safe_load(human_decisions_path.read_text(encoding="utf-8"))
    decision = human_decisions["decisions"][0]
    decision["phase_id"] = "human_merge_decision"
    human_decisions_path.write_text(
        yaml.safe_dump(human_decisions, sort_keys=False),
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "human_decision_record_invalid" in result["blockers"]


def test_accepted_human_decision_must_target_exact_report_artifact(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "awaiting_human_decision"
    prepare_complete_evidence(tmp_path)
    (tmp_path / "human-decisions.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-22-pr-merge-readiness-example",
                "decisions": [
                    {
                        "decision_id": "merge.acceptance",
                        "phase_id": "final_human_merge_decision",
                        "question_ref": "merge.acceptance",
                        "answer": "accepted",
                        "status": "confirmed",
                        "answered_by": "human",
                        "classification": "blocking-material",
                        "affected_artifacts": ["other/pr-merge-readiness-report.json"],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "human_decision_record_invalid" in result["blockers"]


def test_duplicate_merge_human_decisions_block_acceptance(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "awaiting_human_decision"
    prepare_complete_evidence(tmp_path)
    (tmp_path / "human-decisions.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-22-pr-merge-readiness-example",
                "decisions": [
                    {
                        "decision_id": "merge.acceptance",
                        "phase_id": "final_human_merge_decision",
                        "question_ref": "merge.acceptance",
                        "answer": "accepted",
                        "status": "confirmed",
                        "answered_by": "human",
                        "classification": "blocking-material",
                        "affected_artifacts": ["pr-merge-readiness-report.json"],
                    },
                    {
                        "decision_id": "merge.acceptance",
                        "phase_id": "final_human_merge_decision",
                        "question_ref": "merge.acceptance",
                        "answer": "rejected",
                        "status": "rejected",
                        "answered_by": "human",
                        "classification": "blocking-material",
                        "affected_artifacts": ["pr-merge-readiness-report.json"],
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "human_decision_record_invalid" in result["blockers"]


def test_accepted_human_decision_must_bind_material_change_and_report_hash(
    tmp_path: Path,
) -> None:
    report = complete_report()
    report["status"] = "awaiting_human_decision"
    prepare_complete_evidence(tmp_path)
    path = write_report(tmp_path, report)
    human_decisions_path = tmp_path / "human-decisions.yaml"
    human_decisions = yaml.safe_load(human_decisions_path.read_text(encoding="utf-8"))
    decision = human_decisions["decisions"][0]
    decision["material_change_id"] = "older-material-change"
    decision["report_hash"] = "sha256:" + "0" * 64
    human_decisions_path.write_text(
        yaml.safe_dump(human_decisions, sort_keys=False),
        encoding="utf-8",
    )

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "human_decision_record_invalid" in result["blockers"]


def test_self_application_bootstrap_does_not_claim_self_proof(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_cyclic_self_proof"
    report["self_application"]["proof_claim"] = "self_proof"

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_cyclic_self_proof"
    assert result["accepted"] is False
    assert "cyclic_self_proof_claim" in result["blockers"]


def test_pr_merge_readiness_workflow_manifest_declares_utility_policy() -> None:
    workflow_path = ROOT / "workflows" / "pr-merge-readiness" / "workflow.yaml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    assert workflow["name"] == "pr-merge-readiness"
    assert workflow["mvp_status"] == "v0.2-utility"
    assert workflow["utility_shape"] == "lightweight_gate_recipe"
    assert workflow["default_strictness"] == "L1"
    assert "project-initialization" not in workflow.get("outputs", [])
    assert workflow["uses"]["skills"] == ["pr-merge-readiness"]
    assert workflow["review"]["default_evidence_mode"] == "lite"
    assert workflow["review"]["evidence_modes"] == ["lite"]
    assert workflow["review"]["owns_review_execution"] is False
    assert workflow["review"]["consumes_review_evidence"] is True
    assert workflow["review"]["required_for_merge_ready"] is True
    assert "strict_mode_when" not in workflow["review"]
    assert "topology" not in workflow["review"]
    assert "reviewers" not in workflow["review"]
    assert workflow["review"]["topology_source"] == "source_workflow_or_project_binding"
    phases = {item["id"]: item for item in workflow["phases"]}
    assert set(phases) == {"assemble_readiness_report", "readiness_gate"}
    assert phases["assemble_readiness_report"]["skills"] == ["pr-merge-readiness"]
    assert "review" not in {phase.get("kind") for phase in workflow["phases"]}
    assert "fusion" not in {phase.get("kind") for phase in workflow["phases"]}
    assert "finding_validation" not in {phase.get("kind") for phase in workflow["phases"]}
    assert phases["readiness_gate"]["runs_after"] == ["assemble_readiness_report"]
    assert phases["readiness_gate"]["gate"] == "evidence_gate"
    assert phases["readiness_gate"]["scripts"] == ["validate_repo"]
    assert workflow["actor_model"]["review_execution"]["status"] == "out_of_scope"


def test_example_pr_merge_readiness_report_validates() -> None:
    from repo_validation.pr_merge_readiness import validate_pr_merge_readiness_report

    report_path = (
        ROOT
        / "examples"
        / "pr-merge-readiness"
        / "complete"
        / "pr-merge-readiness-report.json"
    )

    errors = validate_pr_merge_readiness_report(ROOT, report_path)

    assert errors == []
