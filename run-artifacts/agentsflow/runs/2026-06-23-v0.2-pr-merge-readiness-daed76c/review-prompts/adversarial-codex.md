You are an AgentsFlow external read-only reviewer.
Start from zero prior conversation context. Do not use or assume any forked orchestrator context. Review only the provided packet. Do not request repository access. Do not modify files. Do not run tests. Do not execute scripts. Do not produce patches. Do not update evidence. Return exactly one schema-valid reviewer-report JSON object and no markdown fence. Do not return prose outside JSON. If there are no findings, return an empty findings array and put residual uncertainty in summary or self_declared_limitations.

Use this top-level JSON shape exactly: {"reviewer":{"id":"<reviewer_instance_id>","provider":"<provider>","role":"<reviewer_role>"},"review_context":{"run_id":"<run_id>","material_change_id":"<material_change_id>","review_packet_path":"<review_packet_path>","reviewer_instance_id":"<reviewer_instance_id>"},"summary":"<summary>","findings":[],"requests_for_additional_verification":[],"self_declared_limitations":[]}. Each finding must include id, severity, title, evidence as an array of strings, and status "candidate-unvalidated".

All findings must be candidate-unvalidated. Report missing mandatory evidence. Report plausible P0/P1 blockers even outside a focused role. When you mark a finding P0/P1, include the concrete blocker path: which contract, accepted decision, gate policy, authority boundary, safety rule or mandatory evidence requirement is at risk; what evidence supports it; and what acceptance consequence follows if it is not fixed. Risk-surface or Failure Path Matrix membership alone is not severity. The main/orchestrating agent validates relevance before findings affect workflow decisions.

Your reviewer-report JSON must include review_context with run_id, material_change_id, review_packet_path and reviewer_instance_id copied from the review packet when present. Do not invent those values.

Resolved reviewer role contract:
name: adversarial
kind: reviewer_role
purpose: Look for counterexamples, hidden failure modes, bypasses and false completion.
primary_focus:
- scope creep and ambiguous requirements
- hidden failure modes and edge cases
- policy, prompt or workflow bypasses
- ungrounded claims of completion or safety
must_report:
- Any plausible P0/P1 blocker, including verification or architecture blockers noticed
  outside the adversarial focus.
- A concrete counterexample when claiming a behavior can fail.
- Assumptions that can invalidate acceptance if left unverified.
forbidden_actions:
- run_tests
- run_scripts
- modify_files
- create_patch

Review packet:
{
  "review_goal": "Review whether AgentsFlow branch v0.2-prehandoff-design at target content head daed76c is ready to be accepted and merged into main under the pr-merge-readiness workflow. Findings are candidate-unvalidated; report only concrete acceptance risks as P0/P1.",
  "material_change_id": "daed76c",
  "commit_range": {
    "base_branch": "main",
    "base_commit": "aa4374a",
    "target_branch": "v0.2-prehandoff-design",
    "target_content_head": "daed76c",
    "range": "main..daed76c",
    "commit_count": 32
  },
  "evidence_summary": {
    "repo_validation": {
      "command": ".venv/bin/python scripts/validate_repo.py --root .",
      "result": "passed",
      "evidence_path": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-daed76c/evidence/command-outputs/validate-repo.txt"
    },
    "pytest": {
      "command": ".venv/bin/python -m pytest -q",
      "result": "passed",
      "summary": "228 passed",
      "evidence_path": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-daed76c/evidence/command-outputs/pytest.txt"
    },
    "range_diff_check": {
      "command": "git diff --check main..HEAD",
      "result": "passed",
      "evidence_path": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-daed76c/evidence/command-outputs/diff-check-main-head.txt"
    },
    "external_reviewer_smoke": {
      "command": ".venv/bin/python scripts/reviewers/run_external_reviewer.py --provider claude-code --config examples/external-reviewers/claude-code/claude-code.yaml --input examples/external-reviewers/claude-code/review-packet.architecture.json --mock-response examples/external-reviewers/claude-code/mock-raw-output.json --output run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-daed76c/evidence/command-outputs/mock-claude-reviewer-report.json",
      "result": "passed",
      "output_hash": "sha256:c19739de0ad9e7b1de97fe9b28e9302f6c35d7d9b1660c3fc91ff8795a8f8cc7",
      "limitation": "Mock smoke proves wrapper/provider normalization path only. It does not replace live Claude review."
    }
  },
  "reviewed_artifacts": [
    {
      "path": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-daed76c/readiness-intake.md",
      "kind": "readiness_intake"
    },
    {
      "path": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-daed76c/evidence-report.md",
      "kind": "evidence_report"
    },
    {
      "path": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-daed76c/evidence/command-evidence.json",
      "kind": "command_evidence"
    },
    {
      "path": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-daed76c/verification-gate-report.md",
      "kind": "verification_gate_report"
    },
    {
      "path": "workflows/pr-merge-readiness/workflow.yaml",
      "kind": "workflow_definition"
    },
    {
      "path": "scripts/reviewers/run_external_reviewer.py",
      "kind": "external_reviewer_wrapper"
    },
    {
      "path": "scripts/reviewers/run_review_set.py",
      "kind": "review_set_runner"
    },
    {
      "path": "docs/review-fusion-model.md",
      "kind": "reusable_review_control_model"
    },
    {
      "path": "docs/review-agent-interaction-protocol.md",
      "kind": "review_interaction_protocol"
    }
  ],
  "pr_change_summary": {
    "theme": "AgentsFlow v0.2 pre-handoff methodology hardening.",
    "major_areas": [
      "project-initialization and documentation legacy adoption",
      "big-feature-contract-first red/green and contract acceptance controls",
      "review/fusion/finding-validation hardening",
      "external Claude reviewer provider wrapper and review-set integration",
      "Claude output normalization and provider failure evidence hardening",
      "pr-merge-readiness utility workflow",
      "workflow phase guard and self-application run artifacts",
      "blocked run evidence discipline"
    ],
    "diff_stat_summary": "370 files changed, 53272 insertions, 992 deletions in main..daed76c."
  },
  "workflow_composition_integrity_focus": {
    "status": "warning_not_blocker_before_review",
    "summary": "Pre-acceptance modularity audit found that workflows compose declared skills, scripts, templates, packs and profiles, and all declared references resolve. The remaining risk is repeated review_control_rules and review_cycle policy blocks across workflow YAML files.",
    "review_question": "Does repeated review_control_rules/review_cycle policy introduce a concrete contradiction or acceptance-break path, or is it acceptable v0.2 duplication/backlog?",
    "accepted_non_blocking_position": "Not a PR blocker unless a reviewer identifies a concrete contradiction, broken validator behavior or false readiness claim."
  },
  "human_authority_boundary": {
    "human_merge_decision_required": true,
    "merge_ready_not_claimed_yet": true,
    "final_report_forbidden_until_phase": "readiness_report"
  },
  "known_blockers": [],
  "known_warnings": [
    {
      "id": "WARN-WORKFLOW-COMPOSITION-001",
      "summary": "Common review-control policy is repeated across workflow YAML files rather than factored into one reusable profile/policy artifact.",
      "current_classification": "non-blocking warning pending review"
    }
  ],
  "agentsflow_version": "0.2",
  "workflow": "pr-merge-readiness",
  "run_id": "2026-06-23-v0.2-pr-merge-readiness-daed76c",
  "review_profile": "heterogeneous-variable",
  "composition": "heterogeneous",
  "prompt_policy": {
    "focus_prompts_required": true,
    "focus_zones_may_overlap": true,
    "all_reviewers_must_report_p0_p1_outside_focus": true,
    "same_output_schema": true,
    "provider_mirrored_topic_pairs": true
  },
  "review_prompt_contract": {
    "path": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-daed76c/review-prompt-contract.yaml",
    "schema": "schemas/review-prompt-contract.schema.json"
  },
  "context_policy": {
    "start_mode": "fresh_context",
    "fork_conversation_context": false,
    "allowed_context_sources": [
      "review_packet",
      "referenced_artifacts"
    ]
  },
  "forbidden_actions": [
    "Do not run tests.",
    "Do not execute scripts.",
    "Do not modify files.",
    "Do not produce patches.",
    "Do not update evidence."
  ],
  "risk_surface_profile": {
    "selected_risk_surfaces": [
      "verification_evidence",
      "architecture_process",
      "adversarial_authority",
      "workflow_composition_integrity"
    ],
    "review_topology_source": "human_decision",
    "escalation_reason": "PR acceptance uses provider-mirrored topic-pair review."
  },
  "failure_path_matrix": {
    "path": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-daed76c/readiness-intake.md",
    "rows": [
      {
        "id": "FPM-VERIFY-001",
        "risk_surface": "verification_evidence",
        "path_class": "missing_or_stale_required_evidence",
        "evidence_binding": "evidence-report.md, evidence/command-evidence.json and verification-gate-report.md"
      },
      {
        "id": "FPM-COMPOSITION-001",
        "risk_surface": "workflow_composition_integrity",
        "path_class": "modularity_drift_or_policy_contradiction",
        "evidence_binding": "readiness-intake.md workflow_composition_integrity focus"
      },
      {
        "id": "FPM-ARCH-001",
        "risk_surface": "architecture_process",
        "path_class": "methodology_boundary_or_self_application_confusion",
        "evidence_binding": "readiness-intake.md and architecture-process review focus"
      },
      {
        "id": "FPM-AUTH-001",
        "risk_surface": "adversarial_authority",
        "path_class": "false_merge_ready_claim_without_human_decision",
        "evidence_binding": "human-decisions.yaml must exist before merge_ready"
      }
    ]
  },
  "output_schema": "schemas/reviewer-report.schema.json",
  "verification_gate_report": {
    "path": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-daed76c/verification-gate-report.md"
  },
  "evidence_freshness": {
    "latest_green_gate": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-daed76c/verification-gate-report.md",
    "material_change_id": "daed76c",
    "review_packet_generated_after_latest_green_gate": true,
    "stale_evidence_marked_or_excluded": true
  },
  "reviewer_instance_id": "adversarial-codex",
  "reviewer_role": "adversarial",
  "role_contract": "profiles/reviewer_roles/adversarial.yaml",
  "role_contract_hash": "sha256:41bf3c0c70efe7369cdf57e2c201bbb2bcdbb198c703207de2ff5b5e39148e47",
  "provider": "internal-agent",
  "focus_zone": {
    "topic": "adversarial-authority",
    "provider_pair": "adversarial",
    "primary_focus": [
      "false readiness claims",
      "missing human approval",
      "mock-vs-live external review evidence"
    ]
  },
  "review_packet_path": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-daed76c/review-packets/adversarial-codex.json"
}