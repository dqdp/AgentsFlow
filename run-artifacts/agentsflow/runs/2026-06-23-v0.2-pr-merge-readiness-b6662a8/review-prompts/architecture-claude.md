You are an AgentsFlow external read-only reviewer.
Start from zero prior conversation context. Do not use or assume any forked orchestrator context. Review only the provided packet. Do not request repository access. Do not modify files. Do not run tests. Do not execute scripts. Do not produce patches. Do not update evidence. Return exactly one schema-valid reviewer-report JSON object and no markdown fence. Do not return prose outside JSON. If there are no findings, return an empty findings array and put residual uncertainty in summary or self_declared_limitations.

Use this top-level JSON shape exactly: {"reviewer":{"id":"<reviewer_instance_id>","provider":"<provider>","role":"<reviewer_role>"},"review_context":{"run_id":"<run_id>","material_change_id":"<material_change_id>","review_packet_path":"<review_packet_path>","reviewer_instance_id":"<reviewer_instance_id>"},"summary":"<summary>","findings":[],"requests_for_additional_verification":[],"self_declared_limitations":[]}. Each finding must include id, severity, title, evidence as an array of strings, and status "candidate-unvalidated".

All findings must be candidate-unvalidated. Report missing mandatory evidence. Report plausible P0/P1 blockers even outside a focused role. When you mark a finding P0/P1, include the concrete blocker path: which contract, accepted decision, gate policy, authority boundary, safety rule or mandatory evidence requirement is at risk; what evidence supports it; and what acceptance consequence follows if it is not fixed. Risk-surface or Failure Path Matrix membership alone is not severity. The main/orchestrating agent validates relevance before findings affect workflow decisions.

Your reviewer-report JSON must include review_context with run_id, material_change_id, review_packet_path and reviewer_instance_id copied from the review packet when present. Do not invent those values.

Resolved reviewer role contract:
name: architecture
kind: reviewer_role
purpose: Review design boundaries, modularity, ADR consistency and architectural risk.
primary_focus:
- module and ownership boundaries
- ADR and accepted-decision consistency
- hidden coupling and architecture drift
- overengineering or under-specified design changes
must_report:
- Any plausible P0/P1 blocker, including verification or scope blockers noticed outside
  the architecture focus.
- Architecture changes that require ADR or human approval.
- Boundary violations that invalidate the task contract.
forbidden_actions:
- run_tests
- run_scripts
- modify_files
- create_patch

Review packet:
{
  "review_goal": "Review whether AgentsFlow branch v0.2-prehandoff-design at target content head b6662a8 is ready to be accepted and merged into main under the pr-merge-readiness workflow. Findings are candidate-unvalidated; report only concrete acceptance risks as P0/P1.",
  "material_change_id": "b6662a8",
  "commit_range": "main..b6662a8",
  "evidence_summary": {
    "repo_validation": "passed",
    "pytest": "235 passed",
    "diff_check": "passed",
    "target_content_head": "b6662a8c052448bacd4b1312d457f8a75a424a97",
    "gh_pr_view": "HTTP 401; optional publication execution may require gh auth login",
    "structured_command_evidence": "refreshed after ARCH-P1-002 candidate; command-evidence.json now records cwd, started_at, finished_at, exit_code, result, output_summary, artifact_paths and raw_log_path for each gate-supporting command."
  },
  "reviewed_artifacts": [
    "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-b6662a8/readiness-intake.md",
    "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-b6662a8/evidence-report.md",
    "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-b6662a8/evidence/command-evidence.json",
    "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-b6662a8/verification-gate-report.md",
    "docs/pr-merge-readiness.md",
    "workflows/pr-merge-readiness/workflow.yaml",
    "scripts/repo_validation/pr_merge_readiness.py",
    "run-artifacts/agentsflow/runs/2026-06-23-pr-readiness-github-publication-focused-review-rerun/review-invocation-set.json"
  ],
  "pr_change_summary": [
    "New commit since prior PR readiness run: b6662a8 workflow: harden PR readiness publication gate",
    "The new commit hardens PR readiness publication gates and records focused mixed-provider review evidence.",
    "This run repeats the full provider-mirrored PR readiness review for the current HEAD."
  ],
  "workflow_composition_integrity_focus": {
    "status": "warning_not_blocker_before_review",
    "summary": "Pre-acceptance modularity audit found that workflows compose declared skills, scripts, templates, packs and profiles, and all declared references resolve. The remaining risk is repeated review_control_rules and review_cycle policy blocks across workflow YAML files.",
    "review_question": "Does repeated review_control_rules/review_cycle policy introduce a concrete contradiction or acceptance-break path, or is it acceptable v0.2 duplication/backlog?",
    "accepted_non_blocking_position": "Not a PR blocker unless a reviewer identifies a concrete contradiction, broken validator behavior or false readiness claim."
  },
  "human_authority_boundary": "github.publication was confirmed as publish during readiness_intake. Final merge acceptance is still open and must be recorded separately in final_human_merge_decision with report_hash.",
  "known_blockers": [],
  "known_warnings": [
    "GitHub CLI is not authenticated in this environment; optional GitHub publication may be blocked until gh auth is restored."
  ],
  "risk_surface_definitions": {
    "verification_evidence": {
      "definition": "Run-local PR readiness surface for deterministic gate evidence freshness, completeness and traceability.",
      "path_classes": [
        "missing_or_stale_required_evidence",
        "unstructured_gate_command_evidence",
        "green_claim_without_current_material_binding"
      ],
      "catalog_relationship": "derived from audit_persistence and persistence_consistency for this PR readiness utility run"
    },
    "architecture_process": {
      "definition": "Run-local PR readiness surface for methodology boundary, self-application separation and workflow/source ownership clarity.",
      "path_classes": [
        "methodology_boundary_or_self_application_confusion",
        "source_artifact_boundary_confusion"
      ],
      "catalog_relationship": "derived from authority_boundary and workflow_composition for this PR readiness utility run"
    },
    "adversarial_authority": {
      "definition": "Run-local PR readiness surface for false readiness, missing human approval and mock-vs-live evidence claims.",
      "path_classes": [
        "false_merge_ready_claim_without_human_decision",
        "mock_or_placeholder_review_claimed_live",
        "publication_claim_without_live_evidence"
      ],
      "catalog_relationship": "derived from human_approval, authority_boundary and external_io for this PR readiness utility run"
    },
    "workflow_composition_integrity": {
      "definition": "Project-local surface for duplicated or conflicting workflow policy blocks that could change gate semantics.",
      "path_classes": [
        "modularity_drift_or_policy_contradiction",
        "repeated_policy_block_conflict"
      ],
      "catalog_relationship": "project-local extension declared by the AgentsFlow binding"
    }
  },
  "finding_calibration_guidance": [
    "Do not report missing final_human_merge_decision as a P1 during provider_mirrored_review unless the run claims accepted_merge_ready before that decision exists; the final human decision is an expected later phase.",
    "Do not report gh_pr_view HTTP 401 as a local merge-readiness blocker; it is a blocker only for executing optional_github_publication after final local acceptance.",
    "Internal-agent reviewer reports are recorded as report-present artifacts with reviewer.model=codex; external live evidence requirements apply to claude-code assignments.",
    "The current run does not rely on its own uncommitted artifacts as source evidence. Committed focused-review evidence from the prior material change is provenance for b6662a8, while this run rechecks b6662a8 with fresh provider-mirrored review."
  ],
  "red_green_evidence": {
    "publication_gate_p1": "Prior focused review found P1-GITHUB-PUBLICATION-RESULT-URL-NOT-BOUND; tests/test_pr_merge_readiness.py::test_published_github_publication_requires_result_artifact_url red-captured the gap and now passes.",
    "current_green": "Full pytest reports 235 passed and repo validation passed for b6662a8."
  },
  "agentsflow_version": "0.2",
  "workflow": "pr-merge-readiness",
  "run_id": "2026-06-23-v0.2-pr-merge-readiness-b6662a8",
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
    "path": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-b6662a8/review-prompt-contract.yaml",
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
    "escalation_reason": "PR acceptance rerun after new commit b6662a8; provider-mirrored topic-pair review remains required.",
    "surface_definitions": {
      "verification_evidence": {
        "definition": "Run-local PR readiness surface for deterministic gate evidence freshness, completeness and traceability.",
        "path_classes": [
          "missing_or_stale_required_evidence",
          "unstructured_gate_command_evidence",
          "green_claim_without_current_material_binding"
        ],
        "catalog_relationship": "derived from audit_persistence and persistence_consistency for this PR readiness utility run"
      },
      "architecture_process": {
        "definition": "Run-local PR readiness surface for methodology boundary, self-application separation and workflow/source ownership clarity.",
        "path_classes": [
          "methodology_boundary_or_self_application_confusion",
          "source_artifact_boundary_confusion"
        ],
        "catalog_relationship": "derived from authority_boundary and workflow_composition for this PR readiness utility run"
      },
      "adversarial_authority": {
        "definition": "Run-local PR readiness surface for false readiness, missing human approval and mock-vs-live evidence claims.",
        "path_classes": [
          "false_merge_ready_claim_without_human_decision",
          "mock_or_placeholder_review_claimed_live",
          "publication_claim_without_live_evidence"
        ],
        "catalog_relationship": "derived from human_approval, authority_boundary and external_io for this PR readiness utility run"
      },
      "workflow_composition_integrity": {
        "definition": "Project-local surface for duplicated or conflicting workflow policy blocks that could change gate semantics.",
        "path_classes": [
          "modularity_drift_or_policy_contradiction",
          "repeated_policy_block_conflict"
        ],
        "catalog_relationship": "project-local extension declared by the AgentsFlow binding"
      }
    },
    "calibration_guidance": [
      "Do not report missing final_human_merge_decision as a P1 during provider_mirrored_review unless the run claims accepted_merge_ready before that decision exists; the final human decision is an expected later phase.",
      "Do not report gh_pr_view HTTP 401 as a local merge-readiness blocker; it is a blocker only for executing optional_github_publication after final local acceptance.",
      "Internal-agent reviewer reports are recorded as report-present artifacts with reviewer.model=codex; external live evidence requirements apply to claude-code assignments.",
      "The current run does not rely on its own uncommitted artifacts as source evidence. Committed focused-review evidence from the prior material change is provenance for b6662a8, while this run rechecks b6662a8 with fresh provider-mirrored review."
    ]
  },
  "failure_path_matrix": {
    "path": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-b6662a8/readiness-intake.md",
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
    "path": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-b6662a8/verification-gate-report.md"
  },
  "evidence_freshness": {
    "latest_green_gate": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-b6662a8/verification-gate-report.md",
    "material_change_id": "b6662a8",
    "review_packet_generated_after_latest_green_gate": true,
    "stale_evidence_marked_or_excluded": true
  },
  "reviewer_instance_id": "architecture-claude",
  "reviewer_role": "architecture",
  "role_contract": "profiles/reviewer_roles/architecture.yaml",
  "role_contract_hash": "sha256:a866516c5cbcb62caf987046bf82432d5bcfbfba2bcc132a0ab99db9ad7bace0",
  "provider": "claude-code",
  "focus_zone": {
    "topic": "architecture-process",
    "provider_pair": "architecture",
    "primary_focus": [
      "workflow boundary",
      "methodology consistency",
      "self-application artifact separation",
      "workflow composition integrity"
    ]
  },
  "review_packet_path": "run-artifacts/agentsflow/runs/2026-06-23-v0.2-pr-merge-readiness-b6662a8/review-packets/architecture-claude.json"
}