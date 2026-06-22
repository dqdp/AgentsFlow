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

PR_REVIEW_MATRIX = [
    ("verification-codex", "verification-evidence", "internal-agent", False, "verification"),
    ("verification-claude", "verification-evidence", "claude-code", True, "verification"),
    ("architecture-codex", "architecture-process", "internal-agent", False, "architecture"),
    ("architecture-claude", "architecture-process", "claude-code", True, "architecture"),
    ("adversarial-codex", "adversarial-authority", "internal-agent", False, "adversarial"),
    ("adversarial-claude", "adversarial-authority", "claude-code", True, "adversarial"),
]
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


def load_evaluator():
    from repo_validation.pr_merge_readiness import evaluate_pr_merge_readiness_report

    return evaluate_pr_merge_readiness_report


def write_evidence(root: Path, *paths: str) -> None:
    for ref in paths:
        path = root / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"evidence for {ref}\n", encoding="utf-8")


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


def grounded_blocker_fields() -> dict[str, object]:
    return {
        "validated_severity": "P1",
        "blocker_path": "review finding -> required PR readiness evidence -> unsafe merge acceptance",
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
            "input_mode": "review_packet",
        },
        "forbidden_env_checked": FORBIDDEN_CLAUDE_ENV,
        "command": "claude -p <stdin> --output-format json --permission-mode default --tools \"\" --model opus --effort max --max-turns 3 --no-session-persistence",
        "wrapper": "scripts/reviewers/run_external_reviewer.py",
        "provider_config_path": "external-reviewers/claude-code.yaml",
        "provider_config_hash": "sha256:" + hashlib.sha256(PROVIDER_CONFIG_CONTENT.encode("utf-8")).hexdigest(),
        "execution_mode": "real",
        "permission_mode": "default",
        "prompt_transport": "stdin",
        "sandbox_mode": "require_escalated",
        "tools": "",
        "output_format": "json",
        "requested_model": "opus",
        "requested_effort": "max",
        "provider_models_used": ["claude-opus-4-8"],
        "max_turns": 3,
        "timeout_seconds": 900,
        "started_at": "2026-06-22T10:00:00Z",
        "finished_at": "2026-06-22T10:01:00Z",
        "exit_code": 0,
        "raw_output_path": "",
        "raw_output_hash": "sha256:" + "1" * 64,
        "normalized_output_path": f"reviewer-report.{reviewer}.json",
        "normalized_output_hash": "sha256:" + "2" * 64,
        "input_hash": "sha256:" + "3" * 64,
        "prompt_hash": "sha256:" + "4" * 64,
        "review_prompt_contract_hash": "sha256:" + "5" * 64,
        "role_contract_hash": "sha256:" + "6" * 64,
        "rubric_hash": "sha256:" + "7" * 64,
        "schema_hash": "sha256:" + "8" * 64,
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
            "review_prompt_contract_path": "review-prompt-contract.yaml",
            "rubric_path": "rubric.json",
            "required_reviews": [
                {
                    "id": reviewer,
                    "topic": topic,
                    "role": role,
                    "provider": provider,
                    "required_live": required_live,
                }
                for reviewer, topic, provider, required_live, role in PR_REVIEW_MATRIX
            ]
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
        "self_application": {
            "enabled": True,
            "application_mode": "self_application_bootstrap",
            "proof_claim": "bootstrap_not_self_proof",
        },
        "residual_limitations": [],
    }


def prepare_complete_evidence(root: Path) -> None:
    (root / "schemas").mkdir(parents=True, exist_ok=True)
    for schema_name in [
        "human-decisions.schema.json",
        "review-prompt-contract.schema.json",
        "reviewer-invocation.schema.json",
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
    provider_config = root / "external-reviewers" / "claude-code.yaml"
    provider_config.parent.mkdir(parents=True, exist_ok=True)
    provider_config.write_text(PROVIDER_CONFIG_CONTENT, encoding="utf-8")
    (root / "review-prompt-contract.yaml").write_text("reviewer_set: []\n", encoding="utf-8")
    (root / "rubric.json").write_text('{"same_output_schema":true}\n', encoding="utf-8")
    for role in sorted({item[4] for item in PR_REVIEW_MATRIX} | {"generalist"}):
        role_path = root / "profiles" / "reviewer_roles" / f"{role}.yaml"
        role_path.parent.mkdir(parents=True, exist_ok=True)
        role_path.write_text(f"id: {role}\n", encoding="utf-8")
    for reviewer, topic, provider, _required_live, role in PR_REVIEW_MATRIX:
        packet_path = root / "review-packets" / f"{reviewer}.json"
        packet_path.parent.mkdir(parents=True, exist_ok=True)
        packet_path.write_text(
            json.dumps(
                {
                    "agentsflow_version": "0.2",
                    "workflow": "pr-merge-readiness",
                    "run_id": "2026-06-22-pr-merge-readiness-example",
                    "material_change_id": "pr-merge-readiness-example-change",
                    "review_packet_path": f"review-packets/{reviewer}.json",
                    "reviewer_instance_id": reviewer,
                    "reviewer_role": role,
                    "topic": topic,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        prompt_path = root / "review-prompts" / f"{reviewer}.md"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(f"Review prompt for {reviewer}\n", encoding="utf-8")
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
            invocation = invocation_metadata(reviewer)
            invocation["normalized_output_hash"] = file_sha(root / f"reviewer-report.{reviewer}.json")
            invocation["input_hash"] = file_sha(root / "review-packets" / f"{reviewer}.json")
            invocation["prompt_hash"] = file_sha(root / "review-prompts" / f"{reviewer}.md")
            invocation["review_prompt_contract_hash"] = file_sha(root / "review-prompt-contract.yaml")
            invocation["role_contract_hash"] = file_sha(root / "profiles" / "reviewer_roles" / f"{role}.yaml")
            invocation["rubric_hash"] = file_sha(root / "rubric.json")
            invocation["schema_hash"] = file_sha(root / "schemas" / "reviewer-report.schema.json")
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
                        "phase_id": "human_merge_decision",
                        "question_ref": "merge.acceptance",
                        "answer": "accepted",
                        "status": "confirmed",
                        "answered_by": "human",
                        "classification": "blocking-material",
                        "affected_artifacts": ["pr-merge-readiness-report.json"],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def write_collision_control_fixture(
    root: Path,
    *,
    finding_id: str = "F-001",
    collision_batch_id: str = "collision-F-001",
    control_conclusion: str = "orchestrator-disposition-supported",
    completed_at: str = "2026-06-22T10:00:00Z",
    prepared_at: str = "2026-06-22T10:00:00Z",
) -> None:
    for reviewer in ["collision-control-a", "collision-control-b"]:
        (root / f"reviewer-report.{reviewer}.json").write_text(
            json.dumps(
                {
                    "reviewer": {
                        "id": reviewer,
                        "provider": "internal-agent",
                        "role": "generalist",
                        "model": "codex",
                    },
                    "summary": "Control reviewer accepts the orchestrator disposition.",
                    "findings": [],
                    "collision_control": {
                        "collision_batch_id": collision_batch_id,
                        "disputed_finding_ids": [finding_id],
                        "control_conclusion": control_conclusion,
                        "completed_at": completed_at,
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    (root / "collision-control-review-prompt-contract.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "artifact_kind": "review_prompt_contract",
                "artifact_scope": "run",
                "identity": {
                    "run_id": "2026-06-22-pr-merge-readiness-example",
                    "workflow": "pr-merge-readiness",
                    "phase_id": "collision_control",
                    "review_profile": "collision-control",
                    "composition": "control",
                    "primary_gate": False,
                },
                "inputs": {
                    "review_packet_schema": "schemas/review-packet.schema.json",
                    "review_packets": [
                        {
                            "reviewer": "collision-control-a",
                            "path": "review-packets/collision-control-a.json",
                            "schema": "schemas/review-packet.schema.json",
                            "packet_hash": "sha256:" + "a" * 64,
                        },
                        {
                            "reviewer": "collision-control-b",
                            "path": "review-packets/collision-control-b.json",
                            "schema": "schemas/review-packet.schema.json",
                            "packet_hash": "sha256:" + "b" * 64,
                        },
                    ],
                    "output_schema": "schemas/reviewer-report.schema.json",
                    "verification_gate_report": "evidence/repo-validation.log",
                },
                "reviewer_set": [
                    {
                        "instance_id": "collision-control-a",
                        "role_id": "generalist",
                        "role_contract": "profiles/reviewer_roles/generalist.yaml",
                        "independent": True,
                    },
                    {
                        "instance_id": "collision-control-b",
                        "role_id": "generalist",
                        "role_contract": "profiles/reviewer_roles/generalist.yaml",
                        "independent": True,
                    },
                ],
                "context_policy": {
                    "start_mode": "fresh_context",
                    "fork_conversation_context": False,
                    "allowed_context_sources": ["review_packet", "referenced_artifacts"],
                },
                "permission_policy": {
                    "read_only": True,
                    "forbidden_actions": ["run_tests", "modify_files"],
                },
                "prompt_components": {
                    "shared_base_instructions": "templates/review-prompts/base.md",
                    "role_contract_source": "profiles/reviewer_roles/*.yaml",
                    "finding_lifecycle": "candidate-unvalidated",
                    "output_instructions": "schemas/reviewer-report.schema.json",
                },
                "prompt_policy": {
                    "same_output_schema": True,
                },
                "rendered_prompts": [
                    {
                        "reviewer": "collision-control-a",
                        "prompt_path": "review-prompts/collision-control-a.md",
                        "prompt_hash": "sha256:" + "c" * 64,
                        "packet_hash": "sha256:" + "a" * 64,
                        "schema_hash": "sha256:" + "d" * 64,
                        "rubric_hash": "sha256:" + "e" * 64,
                        "role_contract_hash": "sha256:" + "f" * 64,
                    },
                    {
                        "reviewer": "collision-control-b",
                        "prompt_path": "review-prompts/collision-control-b.md",
                        "prompt_hash": "sha256:" + "1" * 64,
                        "packet_hash": "sha256:" + "b" * 64,
                        "schema_hash": "sha256:" + "d" * 64,
                        "rubric_hash": "sha256:" + "e" * 64,
                        "role_contract_hash": "sha256:" + "f" * 64,
                    },
                ],
                "collision_control": {
                    "trigger": "rejected_or_downgraded_blocker_collision",
                    "collision_batch_id": collision_batch_id,
                    "control_reviewer_count": 2,
                    "prepared_at": prepared_at,
                    "disputed_findings": [
                        {
                            "finding_id": finding_id,
                            "original_severity": "P1",
                            "source_reviewer_report": "reviewer-report.verification-codex.json",
                            "orchestrator_action": "rejected",
                        }
                    ],
                    "orchestrator_collision_reason": "Fixture rejected P1 requires control review.",
                    "evidence_references_checked": ["reviewer-report.verification-codex.json"],
                },
                "validation": {
                    "schema": "schemas/review-prompt-contract.schema.json",
                    "assembly_invariants": ["collision-control uses two reviewers"],
                },
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


def test_green_evidence_without_human_decision_is_not_accepted(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "awaiting_human_decision"
    report["human_decision"] = {"status": "missing"}

    result = evaluate(tmp_path, report)

    assert result["state"] == "awaiting_human_decision"
    assert result["accepted"] is False
    assert "human_decision_missing" in result["warnings"]
    assert "accepted_merge_ready" not in result.get("allowed_statuses", [])


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
    assert "failed_review:verification-codex" in result["blockers"]


def test_missing_required_review_topology_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    report["reviews"] = []
    report["external_review_evidence"] = []

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "missing_required_review:verification-codex" in result["blockers"]
    assert "missing_required_review:verification-claude" in result["blockers"]
    assert "live_claude_absent" in result["blockers"]


def test_underdeclared_pr_merge_review_topology_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    report["review_requirements"]["required_reviews"] = report["review_requirements"]["required_reviews"][:2]
    report["reviews"] = report["reviews"][:2]
    report["external_review_evidence"] = report["external_review_evidence"][:1]

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "review_requirements_undeclared:architecture-codex" in result["blockers"]
    assert "missing_required_review:architecture-codex" in result["blockers"]
    assert "review_requirements_undeclared:adversarial-claude" in result["blockers"]


def test_required_live_false_for_claude_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    for required in report["review_requirements"]["required_reviews"]:
        if required["id"] == "verification-claude":
            required["required_live"] = False

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "required_live_claude_not_declared:verification-claude" in result["blockers"]


def test_required_review_role_binding_blocks_wrong_role(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    report["reviews"][0]["role_contract_path"] = "profiles/reviewer_roles/architecture.yaml"
    prepare_complete_evidence(tmp_path)
    (tmp_path / "reviewer-report.verification-codex.json").write_text(
        json.dumps(
            {
                "reviewer": {
                    "id": "verification-codex",
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
    assert "required_review_mismatch:verification-codex:role_contract_path" in result["blockers"]
    assert "reviewer_report_role_mismatch:verification-codex" in result["blockers"]


def test_mock_external_review_is_not_live_claude_evidence(tmp_path: Path) -> None:
    report = complete_report()
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
    report["status"] = "blocked_external_review"
    report["external_review_evidence"] = []

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_evidence_missing:verification-claude" in result["blockers"]


def test_mock_invocation_metadata_does_not_satisfy_live_claude_evidence(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    (tmp_path / "reviewer-invocation.verification-claude.json").write_text(
        json.dumps({**invocation_metadata("verification-claude"), "execution_mode": "mock"}) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_not_real:verification-claude" in result["blockers"]


def test_missing_claude_forbidden_env_guardrails_block_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    invocation = invocation_metadata("verification-claude")
    invocation["forbidden_env_checked"] = ["ANTHROPIC_API_KEY"]
    invocation["normalized_output_hash"] = file_sha(tmp_path / "reviewer-report.verification-claude.json")
    invocation["input_hash"] = file_sha(tmp_path / "review-packets" / "verification-claude.json")
    invocation["prompt_hash"] = file_sha(tmp_path / "review-prompts" / "verification-claude.md")
    invocation["review_prompt_contract_hash"] = file_sha(tmp_path / "review-prompt-contract.yaml")
    invocation["role_contract_hash"] = file_sha(tmp_path / "profiles" / "reviewer_roles" / "verification.yaml")
    invocation["rubric_hash"] = file_sha(tmp_path / "rubric.json")
    invocation["schema_hash"] = file_sha(tmp_path / "schemas" / "reviewer-report.schema.json")
    (tmp_path / "reviewer-invocation.verification-claude.json").write_text(
        json.dumps(invocation, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_guardrail_forbidden_env_missing:verification-claude" in result["blockers"]


def test_invalid_claude_provider_config_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    provider_config = tmp_path / "external-reviewers" / "claude-code.yaml"
    provider_config.write_text("provider: claude-code\n", encoding="utf-8")
    for reviewer in ["verification-claude", "architecture-claude", "adversarial-claude"]:
        invocation_path = tmp_path / f"reviewer-invocation.{reviewer}.json"
        invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
        invocation["provider_config_hash"] = file_sha(provider_config)
        invocation_path.write_text(json.dumps(invocation, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_provider_config_invalid:verification-claude" in result["blockers"]


def test_missing_claude_wrapper_metadata_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    invocation = invocation_metadata("verification-claude")
    invocation.pop("wrapper")
    invocation["normalized_output_hash"] = file_sha(tmp_path / "reviewer-report.verification-claude.json")
    invocation["input_hash"] = file_sha(tmp_path / "review-packets" / "verification-claude.json")
    invocation["prompt_hash"] = file_sha(tmp_path / "review-prompts" / "verification-claude.md")
    invocation["review_prompt_contract_hash"] = file_sha(tmp_path / "review-prompt-contract.yaml")
    invocation["role_contract_hash"] = file_sha(tmp_path / "profiles" / "reviewer_roles" / "verification.yaml")
    invocation["rubric_hash"] = file_sha(tmp_path / "rubric.json")
    invocation["schema_hash"] = file_sha(tmp_path / "schemas" / "reviewer-report.schema.json")
    (tmp_path / "reviewer-invocation.verification-claude.json").write_text(
        json.dumps(invocation, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_invocation_invalid:verification-claude" in result["blockers"]
    assert "external_review_guardrail_wrapper_missing:verification-claude" in result["blockers"]


def test_plan_mode_claude_invocation_metadata_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    invocation = invocation_metadata("verification-claude")
    invocation["permission_mode"] = "plan"
    invocation["prompt_transport"] = "file"
    invocation["tools"] = "Read"
    invocation["normalized_output_hash"] = file_sha(tmp_path / "reviewer-report.verification-claude.json")
    (tmp_path / "reviewer-invocation.verification-claude.json").write_text(
        json.dumps(invocation, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_invocation_invalid:verification-claude" in result["blockers"]
    assert "external_review_invocation_unsafe_permission_mode:verification-claude" in result["blockers"]


def test_claude_invocation_hash_mismatch_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    invocation = invocation_metadata("verification-claude")
    invocation["normalized_output_hash"] = "sha256:" + "0" * 64
    (tmp_path / "reviewer-invocation.verification-claude.json").write_text(
        json.dumps(invocation, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_normalized_output_hash_mismatch:verification-claude" in result["blockers"]


def test_claude_invocation_role_mismatch_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    invocation = invocation_metadata("verification-claude")
    invocation["reviewer_role"] = "architecture"
    invocation["normalized_output_hash"] = file_sha(tmp_path / "reviewer-report.verification-claude.json")
    (tmp_path / "reviewer-invocation.verification-claude.json").write_text(
        json.dumps(invocation, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_invocation_role_mismatch:verification-claude" in result["blockers"]


def test_claude_invocation_input_hash_mismatch_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_external_review"
    prepare_complete_evidence(tmp_path)
    invocation = invocation_metadata("verification-claude")
    invocation["input_hash"] = "sha256:" + "0" * 64
    invocation["normalized_output_hash"] = file_sha(tmp_path / "reviewer-report.verification-claude.json")
    invocation["prompt_hash"] = file_sha(tmp_path / "review-prompts" / "verification-claude.md")
    invocation["review_prompt_contract_hash"] = file_sha(tmp_path / "review-prompt-contract.yaml")
    invocation["role_contract_hash"] = file_sha(tmp_path / "profiles" / "reviewer_roles" / "verification.yaml")
    invocation["rubric_hash"] = file_sha(tmp_path / "rubric.json")
    invocation["schema_hash"] = file_sha(tmp_path / "schemas" / "reviewer-report.schema.json")
    (tmp_path / "reviewer-invocation.verification-claude.json").write_text(
        json.dumps(invocation, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_input_hash_mismatch:verification-claude" in result["blockers"]


def test_claude_invocation_rubric_hash_may_match_prompt_contract(tmp_path: Path) -> None:
    report = complete_report()
    prepare_complete_evidence(tmp_path)
    prompt_contract = {
        "rendered_prompts": [
            {
                "reviewer": "verification-claude",
                "rubric_hash": "sha256:" + "a" * 64,
            }
        ]
    }
    (tmp_path / "review-prompt-contract.yaml").write_text(
        yaml.safe_dump(prompt_contract, sort_keys=False),
        encoding="utf-8",
    )
    contract_hash = file_sha(tmp_path / "review-prompt-contract.yaml")
    for reviewer, _topic, provider, _required_live, _role in PR_REVIEW_MATRIX:
        if provider != "claude-code":
            continue
        path = tmp_path / f"reviewer-invocation.{reviewer}.json"
        invocation = json.loads(path.read_text(encoding="utf-8"))
        invocation["review_prompt_contract_hash"] = contract_hash
        if reviewer == "verification-claude":
            invocation["rubric_hash"] = "sha256:" + "a" * 64
        path.write_text(json.dumps(invocation, indent=2) + "\n", encoding="utf-8")

    result = load_evaluator()(tmp_path, write_report(tmp_path, report))

    assert result["state"] == "accepted_merge_ready"
    assert result["accepted"] is True
    assert "external_review_rubric_hash_mismatch:verification-claude" not in result["blockers"]


def test_malformed_reviewer_report_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    prepare_complete_evidence(tmp_path)
    (tmp_path / "reviewer-report.verification-codex.json").write_text(
        json.dumps({"summary": "missing reviewer and findings"}) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "reviewer_report_invalid:verification-codex" in result["blockers"]


def test_internal_reviewer_report_without_current_context_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    prepare_complete_evidence(tmp_path)
    stale_report = {
        "reviewer": {
            "id": "verification-codex",
            "provider": "internal-agent",
            "role": "verification",
            "model": "codex",
        },
        "summary": "Old report with matching reviewer identity but no current packet context.",
        "findings": [],
    }
    (tmp_path / "reviewer-report.verification-codex.json").write_text(
        json.dumps(stale_report, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "reviewer_report_context_missing:verification-codex" in result["blockers"]


def test_internal_reviewer_report_wrong_run_context_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    prepare_complete_evidence(tmp_path)
    stale_context = review_context("verification-codex")
    stale_context["run_id"] = "older-run"
    stale_report = {
        "reviewer": {
            "id": "verification-codex",
            "provider": "internal-agent",
            "role": "verification",
            "model": "codex",
        },
        "review_context": stale_context,
        "summary": "Old report with matching packet path but wrong run.",
        "findings": [],
    }
    (tmp_path / "reviewer-report.verification-codex.json").write_text(
        json.dumps(stale_report, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "reviewer_report_context_mismatch:verification-codex" in result["blockers"]


def test_internal_reviewer_report_missing_reviewer_instance_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_missing_evidence"
    prepare_complete_evidence(tmp_path)
    incomplete_context = review_context("verification-codex")
    incomplete_context.pop("reviewer_instance_id")
    stale_report = {
        "reviewer": {
            "id": "verification-codex",
            "provider": "internal-agent",
            "role": "verification",
            "model": "codex",
        },
        "review_context": incomplete_context,
        "summary": "Old report without the assigned reviewer instance in context.",
        "findings": [],
    }
    (tmp_path / "reviewer-report.verification-codex.json").write_text(
        json.dumps(stale_report, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_missing_evidence"
    assert result["accepted"] is False
    assert "reviewer_report_context_mismatch:verification-codex" in result["blockers"]


def test_old_packet_and_matching_internal_report_pair_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    prepare_complete_evidence(tmp_path)

    old_packet = {
        "agentsflow_version": "0.2",
        "workflow": "pr-merge-readiness",
        "run_id": "older-run",
        "material_change_id": "older-change",
        "review_packet_path": "review-packets/verification-codex.json",
        "reviewer_instance_id": "verification-codex",
        "reviewer_role": "verification",
        "topic": "verification-evidence",
    }
    (tmp_path / "review-packets" / "verification-codex.json").write_text(
        json.dumps(old_packet, indent=2) + "\n",
        encoding="utf-8",
    )
    old_report = {
        "reviewer": {
            "id": "verification-codex",
            "provider": "internal-agent",
            "role": "verification",
            "model": "codex",
        },
        "review_context": {
            "run_id": "older-run",
            "material_change_id": "older-change",
            "review_packet_path": "review-packets/verification-codex.json",
            "reviewer_instance_id": "verification-codex",
        },
        "summary": "Old packet and old report are internally consistent.",
        "findings": [],
    }
    (tmp_path / "reviewer-report.verification-codex.json").write_text(
        json.dumps(old_report, indent=2) + "\n",
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "rejected"
    assert result["accepted"] is False
    assert "review_packet_context_mismatch:verification-codex:run_id" in result["blockers"]
    assert "review_packet_context_mismatch:verification-codex:material_change_id" in result["blockers"]


def test_reviewer_report_p1_omitted_from_candidate_findings_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    prepare_complete_evidence(tmp_path)
    (tmp_path / "reviewer-report.verification-codex.json").write_text(
        json.dumps(
            {
                "reviewer": {
                    "id": "verification-codex",
                    "provider": "internal-agent",
                    "role": "verification",
                },
                "summary": "Found blocker.",
                "review_context": review_context("verification-codex"),
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
    assert "unhandled_source_blocking_finding:verification-codex:P1-SOURCE" in result["blockers"]


def test_reviewer_report_mandatory_gap_omitted_from_candidate_findings_blocks_readiness(
    tmp_path: Path,
) -> None:
    report = complete_report()
    report["status"] = "rejected"
    prepare_complete_evidence(tmp_path)
    (tmp_path / "reviewer-report.verification-codex.json").write_text(
        json.dumps(
            {
                "reviewer": {
                    "id": "verification-codex",
                    "provider": "internal-agent",
                    "role": "verification",
                },
                "summary": "Found missing mandatory evidence.",
                "review_context": review_context("verification-codex"),
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
    assert "unhandled_source_blocking_finding:verification-codex:MANDATORY-GAP" in result["blockers"]


def test_reviewer_report_p1_cannot_be_cleared_by_p3_candidate(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_collision_control"
    report["candidate_findings"] = [
        {
            "id": "P1-SOURCE",
            "severity": "P3",
            "status": "rejected",
            "validation_rationale": "Main agent judged this irrelevant.",
            "source_findings": [{"reviewer": "verification-codex", "id": "P1-SOURCE"}],
        }
    ]
    prepare_complete_evidence(tmp_path)
    (tmp_path / "reviewer-report.verification-codex.json").write_text(
        json.dumps(
            {
                "reviewer": {
                    "id": "verification-codex",
                    "provider": "internal-agent",
                    "role": "verification",
                    "model": "codex",
                },
                "summary": "Found blocker.",
                "review_context": review_context("verification-codex"),
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

    assert result["state"] == "blocked_collision_control"
    assert result["accepted"] is False
    assert "collision_control_missing:P1-SOURCE" in result["blockers"]


def test_reviewer_report_p1_cannot_disappear_as_duplicate_without_resolution(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "rejected"
    report["candidate_findings"] = [
        {
            "id": "P1-SOURCE",
            "severity": "P1",
            "status": "duplicate",
            "source_findings": [{"reviewer": "verification-codex", "id": "P1-SOURCE"}],
            **grounded_blocker_fields(),
        }
    ]
    prepare_complete_evidence(tmp_path)
    (tmp_path / "reviewer-report.verification-codex.json").write_text(
        json.dumps(
            {
                "reviewer": {
                    "id": "verification-codex",
                    "provider": "internal-agent",
                    "role": "verification",
                    "model": "codex",
                },
                "summary": "Found blocker.",
                "review_context": review_context("verification-codex"),
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
            "source_findings": [{"reviewer": "verification-codex", "id": "F-001"}],
            **grounded_blocker_fields(),
        }
    ]
    prepare_complete_evidence(tmp_path)
    for reviewer, provider, role in [
        ("verification-codex", "internal-agent", "verification"),
        ("architecture-codex", "internal-agent", "architecture"),
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
    assert "unhandled_source_blocking_finding:architecture-codex:F-001" in result["blockers"]


def test_sensitive_raw_external_output_requires_redaction_reason(tmp_path: Path) -> None:
    report = complete_report()
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
    report["status"] = "blocked_sensitive_raw_evidence"
    report["external_review_evidence"][0]["raw_output"].pop("artifact_path")
    report["external_review_evidence"][0]["raw_output"].pop("artifact_hash")
    prepare_complete_evidence(tmp_path)
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_sensitive_raw_evidence"
    assert result["accepted"] is False
    assert "raw_output_artifact_missing:verification-claude" in result["blockers"]


def test_redacted_live_external_output_does_not_require_raw_provider_artifact(tmp_path: Path) -> None:
    report = complete_report()
    prepare_complete_evidence(tmp_path)
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "accepted_merge_ready"
    assert result["accepted"] is True
    assert "external_review_raw_output_missing:verification-claude" not in result["blockers"]


def test_redacted_live_external_output_rejects_persisted_raw_provider_artifact(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_sensitive_raw_evidence"
    prepare_complete_evidence(tmp_path)
    attach_raw_provider_output(tmp_path, "verification-claude")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_sensitive_raw_evidence"
    assert result["accepted"] is False
    assert "raw_output_unexpected_persisted:verification-claude" in result["blockers"]


def test_redacted_live_external_output_rejects_invocation_normalization_raw_source(
    tmp_path: Path,
) -> None:
    report = complete_report()
    report["status"] = "blocked_sensitive_raw_evidence"
    prepare_complete_evidence(tmp_path)
    raw_path = tmp_path / "raw" / "verification-claude.raw.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text('{"result":"raw"}\n', encoding="utf-8")
    invocation_path = tmp_path / "reviewer-invocation.verification-claude.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation["normalization"] = {
        "method": "native-json",
        "source_path": "raw/verification-claude.raw.json",
        "source_hash": file_sha(raw_path),
        "output_path": "reviewer-report.verification-claude.json",
        "output_hash": file_sha(tmp_path / "reviewer-report.verification-claude.json"),
        "schema_validation": "passed",
        "normalized_by": "scripts/reviewers/run_external_reviewer.py",
    }
    invocation_path.write_text(json.dumps(invocation, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_sensitive_raw_evidence"
    assert result["accepted"] is False
    assert "raw_output_unexpected_persisted:verification-claude" in result["blockers"]


def test_redacted_live_external_output_rejects_report_normalization_raw_source(
    tmp_path: Path,
) -> None:
    report = complete_report()
    report["status"] = "blocked_sensitive_raw_evidence"
    prepare_complete_evidence(tmp_path)
    raw_path = tmp_path / "raw" / "verification-claude.raw.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text('{"result":"raw"}\n', encoding="utf-8")
    reviewer_report_path = tmp_path / "reviewer-report.verification-claude.json"
    reviewer_report = json.loads(reviewer_report_path.read_text(encoding="utf-8"))
    reviewer_report["normalization"] = {
        "method": "native-json",
        "source_path": "raw/verification-claude.raw.json",
        "source_hash": file_sha(raw_path),
        "schema_validation": "passed",
        "normalized_by": "scripts/reviewers/run_external_reviewer.py",
    }
    reviewer_report_path.write_text(json.dumps(reviewer_report, indent=2) + "\n", encoding="utf-8")
    invocation_path = tmp_path / "reviewer-invocation.verification-claude.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation["normalized_output_hash"] = file_sha(reviewer_report_path)
    invocation_path.write_text(json.dumps(invocation, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_sensitive_raw_evidence"
    assert result["accepted"] is False
    assert "raw_output_unexpected_persisted:verification-claude" in result["blockers"]


def test_raw_live_external_output_requires_non_sensitive_declaration(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_sensitive_raw_evidence"
    report["external_review_evidence"][0]["raw_output"] = {
        "persistence": "raw",
    }
    prepare_complete_evidence(tmp_path)
    attach_raw_provider_output(tmp_path, "verification-claude")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_sensitive_raw_evidence"
    assert result["accepted"] is False
    assert "raw_output_non_sensitive_declaration_missing" in result["blockers"]


def test_non_sensitive_raw_live_external_output_is_hash_bound(tmp_path: Path) -> None:
    report = complete_report()
    report["external_review_evidence"][0]["raw_output"] = {
        "persistence": "raw",
        "non_sensitive": True,
    }
    prepare_complete_evidence(tmp_path)
    attach_raw_provider_output(tmp_path, "verification-claude")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "accepted_merge_ready"
    assert result["accepted"] is True
    assert result["blockers"] == []


def test_non_sensitive_raw_live_external_output_hash_mismatch_blocks(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_external_review"
    report["external_review_evidence"][0]["raw_output"] = {
        "persistence": "raw",
        "non_sensitive": True,
    }
    prepare_complete_evidence(tmp_path)
    attach_raw_provider_output(tmp_path, "verification-claude")
    invocation_path = tmp_path / "reviewer-invocation.verification-claude.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation["raw_output_hash"] = "sha256:" + "0" * 64
    invocation_path.write_text(json.dumps(invocation, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_raw_output_hash_mismatch:verification-claude" in result["blockers"]


def test_non_sensitive_raw_live_external_output_missing_hash_blocks_with_precise_label(
    tmp_path: Path,
) -> None:
    report = complete_report()
    report["status"] = "blocked_external_review"
    report["external_review_evidence"][0]["raw_output"] = {
        "persistence": "raw",
        "non_sensitive": True,
    }
    prepare_complete_evidence(tmp_path)
    attach_raw_provider_output(tmp_path, "verification-claude")
    invocation_path = tmp_path / "reviewer-invocation.verification-claude.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation.pop("raw_output_hash")
    invocation_path.write_text(json.dumps(invocation, indent=2) + "\n", encoding="utf-8")
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_external_review"
    assert result["accepted"] is False
    assert "external_review_invocation_missing_raw_output_hash:verification-claude" in result["blockers"]
    assert "external_review_raw_output_hash_mismatch:verification-claude" not in result["blockers"]


def test_live_external_output_not_persisted_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_sensitive_raw_evidence"
    report["external_review_evidence"][0]["raw_output"] = {
        "persistence": "not_persisted",
    }

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_sensitive_raw_evidence"
    assert result["accepted"] is False
    assert "raw_output_not_persisted:verification-claude" in result["blockers"]


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


def test_rejected_p1_without_blocker_path_does_not_require_collision_control(tmp_path: Path) -> None:
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
    assert "collision_control_missing:F-001" not in result["blockers"]


def test_rejected_blocker_findings_require_collision_control(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_collision_control"
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

    assert result["state"] == "blocked_collision_control"
    assert result["accepted"] is False
    assert "collision_control_missing:F-001" in result["blockers"]


def test_placeholder_collision_control_does_not_clear_rejected_blocker(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_collision_control"
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

    assert result["state"] == "blocked_collision_control"
    assert result["accepted"] is False
    assert "collision_control_incomplete:F-001" in result["blockers"]


def test_arbitrary_files_do_not_satisfy_collision_control(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_collision_control"
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P1",
            "status": "rejected",
            **grounded_blocker_fields(),
            "collision_control": {
                "status": "completed",
                "evidence_path": "evidence/repo-validation.log",
                "control_reviewer_count": 2,
                "disputed_finding_ids": ["F-001"],
                "control_reports": [
                    {"path": "evidence/repo-validation.log"},
                    {"path": "evidence/pytest.log"},
                ],
            },
        }
    ]

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_collision_control"
    assert result["accepted"] is False
    assert "collision_control_report_invalid:F-001" in result["blockers"]


def test_unrelated_valid_reports_do_not_satisfy_collision_control(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_collision_control"
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P1",
            "status": "rejected",
            **grounded_blocker_fields(),
            "collision_control": {
                "status": "completed",
                "collision_batch_id": "collision-F-001",
                "evidence_path": "evidence/repo-validation.log",
                "control_reviewer_count": 2,
                "disputed_finding_ids": ["F-001"],
                "control_reports": [
                    {"path": "reviewer-report.verification-codex.json"},
                    {"path": "reviewer-report.architecture-codex.json"},
                ],
            },
        }
    ]

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_collision_control"
    assert result["accepted"] is False
    assert "collision_control_report_invalid:F-001" in result["blockers"]


def test_self_declared_collision_control_reports_require_prompt_contract(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_collision_control"
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P1",
            "status": "rejected",
            **grounded_blocker_fields(),
            "collision_control": {
                "status": "completed",
                "collision_batch_id": "collision-F-001",
                "evidence_path": "evidence/repo-validation.log",
                "control_reviewer_count": 2,
                "disputed_finding_ids": ["F-001"],
                "control_reports": [
                    {"path": "reviewer-report.collision-control-a.json"},
                    {"path": "reviewer-report.collision-control-b.json"},
                ],
            },
        }
    ]
    prepare_complete_evidence(tmp_path)
    write_collision_control_fixture(tmp_path)
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_collision_control"
    assert result["accepted"] is False
    assert "collision_control_incomplete:F-001" in result["blockers"]
    assert "collision_control_prompt_contract_missing:F-001" in result["blockers"]


def test_minimal_collision_control_prompt_contract_does_not_clear_rejected_blocker(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_collision_control"
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P1",
            "status": "rejected",
            **grounded_blocker_fields(),
            "collision_control": {
                "status": "completed",
                "collision_batch_id": "collision-F-001",
                "review_prompt_contract_path": "collision-control-review-prompt-contract.yaml",
                "evidence_path": "collision-control-review-prompt-contract.yaml",
                "control_reviewer_count": 2,
                "disputed_finding_ids": ["F-001"],
                "control_reports": [
                    {"path": "reviewer-report.collision-control-a.json"},
                    {"path": "reviewer-report.collision-control-b.json"},
                ],
            },
        }
    ]
    prepare_complete_evidence(tmp_path)
    write_collision_control_fixture(tmp_path)
    (tmp_path / "collision-control-review-prompt-contract.yaml").write_text(
        yaml.safe_dump(
            {
                "identity": {
                    "review_profile": "collision-control",
                    "primary_gate": False,
                },
                "reviewer_set": [
                    {"instance_id": "collision-control-a"},
                    {"instance_id": "collision-control-b"},
                ],
                "collision_control": {
                    "trigger": "rejected_or_downgraded_blocker_collision",
                    "collision_batch_id": "collision-F-001",
                    "control_reviewer_count": 2,
                    "prepared_at": "2026-06-22T10:00:00Z",
                    "disputed_findings": [
                        {
                            "finding_id": "F-001",
                            "original_severity": "P1",
                            "source_reviewer_report": "reviewer-report.verification-codex.json",
                            "orchestrator_action": "rejected",
                        }
                    ],
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_collision_control"
    assert result["accepted"] is False
    assert "collision_control_prompt_contract_invalid:F-001" in result["blockers"]


def test_stale_collision_control_does_not_clear_rejected_blocker(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_collision_control"
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P1",
            "status": "rejected",
            **grounded_blocker_fields(),
            "collision_control": {
                "status": "completed",
                "collision_batch_id": "collision-F-001",
                "review_prompt_contract_path": "collision-control-review-prompt-contract.yaml",
                "evidence_path": "collision-control-review-prompt-contract.yaml",
                "control_reviewer_count": 2,
                "disputed_finding_ids": ["F-001"],
                "control_reports": [
                    {"path": "reviewer-report.collision-control-a.json"},
                    {"path": "reviewer-report.collision-control-b.json"},
                ],
            },
        }
    ]
    prepare_complete_evidence(tmp_path)
    write_collision_control_fixture(
        tmp_path,
        completed_at="2026-06-22T08:00:00Z",
        prepared_at="2026-06-22T08:00:00Z",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_collision_control"
    assert result["accepted"] is False
    assert "collision_control_stale:F-001" in result["blockers"]


def test_unsupported_collision_control_conclusion_does_not_clear_rejected_blocker(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_collision_control"
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P1",
            "status": "rejected",
            **grounded_blocker_fields(),
            "collision_control": {
                "status": "completed",
                "collision_batch_id": "collision-F-001",
                "review_prompt_contract_path": "collision-control-review-prompt-contract.yaml",
                "evidence_path": "collision-control-review-prompt-contract.yaml",
                "control_reviewer_count": 2,
                "disputed_finding_ids": ["F-001"],
                "control_reports": [
                    {"path": "reviewer-report.collision-control-a.json"},
                    {"path": "reviewer-report.collision-control-b.json"},
                ],
            },
        }
    ]
    prepare_complete_evidence(tmp_path)
    write_collision_control_fixture(
        tmp_path,
        control_conclusion="orchestrator-disposition-unsupported",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_collision_control"
    assert result["accepted"] is False
    assert "collision_control_unsupported:F-001" in result["blockers"]


def test_collision_control_report_before_prompt_preparation_does_not_clear_rejected_blocker(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_collision_control"
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P1",
            "status": "rejected",
            **grounded_blocker_fields(),
            "collision_control": {
                "status": "completed",
                "collision_batch_id": "collision-F-001",
                "review_prompt_contract_path": "collision-control-review-prompt-contract.yaml",
                "evidence_path": "collision-control-review-prompt-contract.yaml",
                "control_reviewer_count": 2,
                "disputed_finding_ids": ["F-001"],
                "control_reports": [
                    {"path": "reviewer-report.collision-control-a.json"},
                    {"path": "reviewer-report.collision-control-b.json"},
                ],
            },
        }
    ]
    prepare_complete_evidence(tmp_path)
    write_collision_control_fixture(
        tmp_path,
        completed_at="2026-06-22T10:00:00Z",
        prepared_at="2026-06-22T10:05:00Z",
    )
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "blocked_collision_control"
    assert result["accepted"] is False
    assert "collision_control_stale:F-001" in result["blockers"]


def test_collision_control_prompt_contract_can_clear_rejected_blocker(tmp_path: Path) -> None:
    report = complete_report()
    report["candidate_findings"] = [
        {
            "id": "F-001",
            "severity": "P1",
            "status": "rejected",
            **grounded_blocker_fields(),
            "collision_control": {
                "status": "completed",
                "collision_batch_id": "collision-F-001",
                "review_prompt_contract_path": "collision-control-review-prompt-contract.yaml",
                "evidence_path": "collision-control-review-prompt-contract.yaml",
                "control_reviewer_count": 2,
                "disputed_finding_ids": ["F-001"],
                "control_reports": [
                    {"path": "reviewer-report.collision-control-a.json"},
                    {"path": "reviewer-report.collision-control-b.json"},
                ],
            },
        }
    ]
    prepare_complete_evidence(tmp_path)
    write_collision_control_fixture(tmp_path)
    path = write_report(tmp_path, report)

    result = load_evaluator()(tmp_path, path)

    assert result["state"] == "accepted_merge_ready"
    assert result["accepted"] is True
    assert result["blockers"] == []


def test_review_packet_older_than_material_change_is_stale(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_stale_review"
    report["reviews"][0]["packet_prepared_at"] = "2026-06-22T08:00:00Z"
    report["reviews"][0]["latest_material_change_at"] = "2026-06-22T09:30:00Z"

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_stale_review"
    assert result["accepted"] is False
    assert "stale_review:verification-codex" in result["blockers"]
    assert result["stale_reviews"] == ["verification-codex"]


def test_malformed_review_timestamp_blocks_readiness(tmp_path: Path) -> None:
    report = complete_report()
    report["status"] = "blocked_stale_review"
    report["reviews"][0]["packet_prepared_at"] = "not-a-timestamp"

    result = evaluate(tmp_path, report)

    assert result["state"] == "blocked_stale_review"
    assert result["accepted"] is False
    assert "invalid_review_timestamp:verification-codex" in result["blockers"]


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
                        "phase_id": "human_merge_decision",
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
                        "phase_id": "human_merge_decision",
                        "question_ref": "merge.acceptance",
                        "answer": "accepted",
                        "status": "confirmed",
                        "answered_by": "human",
                        "classification": "blocking-material",
                        "affected_artifacts": ["pr-merge-readiness-report.json"],
                    },
                    {
                        "decision_id": "merge.acceptance",
                        "phase_id": "human_merge_decision",
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
    assert workflow["default_strictness"] == "L3"
    assert "project-initialization" not in workflow.get("outputs", [])
    assert workflow["review"]["topology"] == "heterogeneous-variable"
    assert workflow["review"]["provider_strategy"] == "provider-mirrored-topic-pairs"
    topic_pairs = workflow["review"]["topic_pairs"]
    assert {item["topic"] for item in topic_pairs} == {
        "verification-evidence",
        "architecture-process",
        "adversarial-authority",
    }
    for pair in topic_pairs:
        assert pair["providers"] == ["internal-agent", "claude-code"]


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
