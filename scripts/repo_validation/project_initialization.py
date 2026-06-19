from __future__ import annotations

from pathlib import Path

from .common import parse_json, parse_yaml, validate_against_schema


def validate_project_documentation_disposition_artifact(root: Path, path: Path) -> list[str]:
    schema = parse_json(root / "schemas" / "project-documentation-disposition.schema.json")
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"{path}: project documentation disposition must be a mapping"]
    return validate_against_schema(path, data, schema)


def validate_project_initialization_operating_decisions(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("name") != "project-initialization":
        return errors
    outputs = set(data.get("outputs", []) or [])
    uses = data.get("uses", {}) or {}
    skills = set(uses.get("skills", []) or [])
    templates = set(uses.get("templates", []) or [])
    phases = data.get("phases", []) or []
    phase_by_id = {
        phase.get("id"): phase
        for phase in phases
        if isinstance(phase, dict) and phase.get("id")
    }
    mode_outputs = data.get("mode_gated_outputs", {}) or {}
    onboarding_outputs = set(mode_outputs.get("adoption-onboarding", []) or [])
    if "project-operating-decisions.yaml" not in onboarding_outputs:
        errors.append(f"{path}: adoption-onboarding outputs must include project-operating-decisions.yaml")
    if "project-operating-decisions-interview" not in skills:
        errors.append(f"{path}: project-initialization must use project-operating-decisions-interview skill")
    if "project-operating-decisions.yaml" not in templates:
        errors.append(f"{path}: project-initialization must use project-operating-decisions.yaml template")
    if "project-documentation-disposition.yaml" not in templates:
        errors.append(f"{path}: project-initialization must use project-documentation-disposition.yaml template")
    interview = phase_by_id.get("operating_decisions_interview")
    if not interview:
        errors.append(f"{path}: project-initialization must include operating_decisions_interview phase")
    else:
        interview_applies = set(str(item) for item in interview.get("applies_to_intent_modes", []) or [])
        if interview_applies != {"adoption-onboarding"}:
            errors.append(f"{path}: operating_decisions_interview must apply only to adoption-onboarding")
        if "project-operating-decisions.yaml" not in set(interview.get("outputs", []) or []):
            errors.append(f"{path}: operating_decisions_interview must output project-operating-decisions.yaml")
    target_decisions = phase_by_id.get("target_workflow_context_decision_packet")
    if not isinstance(target_decisions, dict):
        errors.append(f"{path}: project-initialization must include target_workflow_context_decision_packet phase")
    else:
        applies = set(str(item) for item in target_decisions.get("applies_to_intent_modes", []) or [])
        if applies != {"prepare-workflow"}:
            errors.append(f"{path}: target_workflow_context_decision_packet must apply only to prepare-workflow")
        outputs = set(str(item) for item in target_decisions.get("outputs", []) or [])
        if "target workflow human decision packet" not in outputs:
            errors.append(f"{path}: target_workflow_context_decision_packet must output target workflow human decision packet")
        human = target_decisions.get("human_interaction", {}) or {}
        if human.get("response_artifact") == "project-operating-decisions.yaml":
            errors.append(f"{path}: target_workflow_context_decision_packet must not write project-operating-decisions.yaml")
        inputs = set(str(item) for item in target_decisions.get("inputs", []) or [])
        if "project-documentation-disposition.yaml" not in inputs:
            errors.append(f"{path}: target_workflow_context_decision_packet must consume project-documentation-disposition.yaml")
    overlay = phase_by_id.get("overlay_draft")
    if overlay:
        inputs = set(overlay.get("inputs", []) or [])
        has_operating_decisions = any(str(item).startswith("project-operating-decisions.yaml") for item in inputs)
        has_existing_policy = any("existing project policy/workflow binding" in str(item) for item in inputs)
        if not has_operating_decisions:
            errors.append(f"{path}: overlay_draft must consume project-operating-decisions.yaml for onboarding")
        if not has_existing_policy:
            errors.append(f"{path}: overlay_draft must allow existing project policy/workflow binding for prepare-workflow")
        if "project-documentation-disposition.yaml" not in inputs:
            errors.append(f"{path}: overlay_draft must consume project-documentation-disposition.yaml")
    return errors


def validate_project_initialization_human_interaction(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("name") != "project-initialization":
        return errors

    human = data.get("human_interaction", {}) or {}
    if human.get("mode") != "main-agent-mediated":
        errors.append(f"{path}: project-initialization human_interaction.mode must be main-agent-mediated")
    if human.get("reviewers_may_ask_human") is not False:
        errors.append(f"{path}: project-initialization must set reviewers_may_ask_human: false")
    if human.get("pause_state") != "paused_waiting_for_human":
        errors.append(f"{path}: project-initialization pause_state must be paused_waiting_for_human")
    if human.get("question_artifact") != "human-questions.yaml":
        errors.append(f"{path}: project-initialization question_artifact must be human-questions.yaml")
    if human.get("decision_artifact") != "human-decisions.yaml":
        errors.append(f"{path}: project-initialization decision_artifact must be human-decisions.yaml")

    required_pause_phases = {
        "documentation_disposition_decision",
        "read_project_intake",
        "legacy_adoption_mode_decision",
        "operating_decisions_interview",
        "target_workflow_context_decision_packet",
        "human_approval",
    }
    declared = set(human.get("allowed_pause_phases", []) or [])
    missing_declared = sorted(required_pause_phases - declared)
    if missing_declared:
        errors.append(f"{path}: human_interaction.allowed_pause_phases missing: {', '.join(missing_declared)}")

    phase_by_id = {
        phase.get("id"): phase
        for phase in data.get("phases", []) or []
        if isinstance(phase, dict) and phase.get("id")
    }
    for phase_id in sorted(required_pause_phases):
        phase = phase_by_id.get(phase_id)
        if not phase:
            errors.append(f"{path}: missing human-interaction phase: {phase_id}")
            continue
        phase_human = phase.get("human_interaction", {}) or {}
        if phase_human.get("can_pause") is not True:
            errors.append(f"{path}: phase {phase_id} must set human_interaction.can_pause: true")
        if phase_human.get("question_artifact") != "human-questions.yaml":
            errors.append(f"{path}: phase {phase_id} must use human-questions.yaml")
        if phase_human.get("decision_artifact") != "human-decisions.yaml":
            errors.append(f"{path}: phase {phase_id} must use human-decisions.yaml")
    return errors


def validate_project_initialization_intent_mode_policy(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("name") != "project-initialization":
        return errors

    intent_modes = data.get("intent_modes", {}) or {}
    supported = set(str(item) for item in intent_modes.get("supported", []) or [])
    required_modes = {
        "unknown-discovery",
        "adoption-onboarding",
        "prepare-workflow",
        "legacy-cleanup",
        "risk-domain-assessment",
    }
    missing = sorted(required_modes - supported)
    if intent_modes.get("required") is not True:
        errors.append(f"{path}: project-initialization intent_modes.required must be true")
    if intent_modes.get("prepare_workflow_requires_target_workflow") is not True:
        errors.append(f"{path}: prepare-workflow must require target_workflow")
    if missing:
        errors.append(f"{path}: intent_modes.supported missing: {', '.join(missing)}")
    outputs = set(str(item) for item in data.get("outputs", []) or [])
    mode_outputs = {
        str(mode): [str(item) for item in outputs_for_mode or []]
        for mode, outputs_for_mode in (data.get("mode_gated_outputs", {}) or {}).items()
    }

    def mode_has(mode: str, text: str) -> bool:
        return any(text in item for item in mode_outputs.get(mode, []))

    def mode_missing(mode: str, required_texts: list[str]) -> list[str]:
        return [text for text in required_texts if not mode_has(mode, text)]

    onboarding_only_output_patterns = [
        ".agentsflow/agentsflow.lock.yaml",
        ".agentsflow/project.yaml",
        "project-operating-decisions.yaml",
        "project-documentation-disposition.yaml",
        "workflow bindings",
        "workflow bindings draft",
        "project-bound gate drafts",
        "initialization-report.md",
        "legacy-agent-system-inventory.json",
        "legacy-adoption-decision.yaml",
        "active-instruction-map.yaml",
    ]
    leaked_outputs = sorted(
        item
        for item in outputs
        if any(pattern in item for pattern in onboarding_only_output_patterns)
    )
    if leaked_outputs:
        errors.append(
            f"{path}: top-level outputs must be mode-neutral; move mode-specific outputs to mode_gated_outputs: "
            + ", ".join(leaked_outputs)
        )
    required_mode_outputs = {
        "unknown-discovery": [
            "project-raw-scan.json",
            "project-inventory.json",
            "project-assessment.architecture.json",
            "project-assessment.verification.json",
            "project-assessment.adversarial.json",
            "project-assessment.json",
            "human-questions.yaml",
        ],
        "adoption-onboarding": [
            "project-documentation-disposition.yaml",
            "project-operating-decisions.yaml",
            ".agentsflow/project.yaml draft",
            "workflow bindings draft",
            "project-bound gate drafts",
            "active-instruction-map.yaml draft",
            "legacy-agent-system-inventory.json when legacy artifacts are in scope",
            "legacy-adoption-decision.yaml when legacy artifacts are in scope",
            "agent-instruction-migration-plan.md when legacy artifacts are in scope",
            "legacy-backup-manifest.yaml when legacy artifacts are in scope",
            "initialization-report.md",
        ],
        "prepare-workflow": [
            "project-documentation-disposition.yaml",
            "target workflow binding draft",
            "target workflow gate readiness report",
            "target workflow human decision packet",
            "finding-validation-report.md",
            "review-cycle-report.md",
        ],
        "legacy-cleanup": [
            "project-documentation-disposition.yaml",
            "legacy-agent-system-inventory.json",
            "legacy-adoption-decision.yaml",
            "agent-instruction-migration-plan.md",
            "active-instruction-map.yaml draft",
        ],
        "risk-domain-assessment": [
            "domain-identification section",
            "project-assessment.architecture.json",
            "project-assessment.verification.json",
            "project-assessment.adversarial.json",
            "project-assessment.json",
            "human domain-expertise questions",
        ],
    }
    for mode, required_texts in required_mode_outputs.items():
        missing_mode_outputs = mode_missing(mode, required_texts)
        if missing_mode_outputs:
            errors.append(
                f"{path}: mode_gated_outputs.{mode} missing: {', '.join(missing_mode_outputs)}"
            )
    forbidden_mode_outputs = {
        "unknown-discovery": [
            ".agentsflow/project.yaml",
            "workflow bindings",
            "project-bound gate",
            "project-operating-decisions.yaml",
            "initialization-report.md",
            "active-instruction-map.yaml",
        ],
        "prepare-workflow": [
            ".agentsflow/project.yaml",
            "project-operating-decisions.yaml",
            "workflow bindings draft",
            "project-bound gate drafts",
            "initialization-report.md",
            "active-instruction-map.yaml",
        ],
        "risk-domain-assessment": [
            ".agentsflow/project.yaml",
            "workflow bindings",
            "project-bound gate",
            "project-operating-decisions.yaml",
            "initialization-report.md",
            "active-instruction-map.yaml",
        ],
    }
    for mode, forbidden_texts in forbidden_mode_outputs.items():
        forbidden_present = [
            item
            for item in mode_outputs.get(mode, [])
            if any(forbidden_text in item for forbidden_text in forbidden_texts)
        ]
        if forbidden_present:
            errors.append(
                f"{path}: mode_gated_outputs.{mode} must not include activation outputs: "
                + ", ".join(forbidden_present)
            )

    phase_policy = data.get("intent_mode_phase_policy", {}) or {}
    unknown_policy = phase_policy.get("unknown-discovery", {}) or {}
    risk_policy = phase_policy.get("risk-domain-assessment", {}) or {}
    prepare_policy = phase_policy.get("prepare-workflow", {}) or {}
    must_not_require = set(str(item) for item in unknown_policy.get("must_not_require", []) or [])
    risk_must_not_require = set(str(item) for item in risk_policy.get("must_not_require", []) or [])
    mode_specific_activation_phases = [
        "operating_decisions_interview",
        "overlay_draft",
        "project_initialization_gate",
        "documentation_disposition_decision",
        "target_workflow_context_decision_packet",
        "target_workflow_readiness_gate",
        "initialization_review",
        "finding_validation",
        "human_approval",
    ]
    for phase_id in mode_specific_activation_phases:
        if phase_id not in must_not_require:
            errors.append(f"{path}: unknown-discovery must not require {phase_id}")
    for phase_id in [
        "overlay_draft",
        "project_initialization_gate",
        "documentation_disposition_decision",
        "target_workflow_context_decision_packet",
        "target_workflow_readiness_gate",
        "initialization_review",
        "finding_validation",
        "human_approval",
    ]:
        if phase_id not in risk_must_not_require:
            errors.append(f"{path}: risk-domain-assessment must not require {phase_id}")
    if prepare_policy.get("requires_target_workflow") is not True:
        errors.append(f"{path}: prepare-workflow phase policy must require target_workflow")
    if prepare_policy.get("requires_sufficient_operating_context") is not True:
        errors.append(f"{path}: prepare-workflow phase policy must require sufficient operating context")
    if prepare_policy.get("target_workflow_context_decision_packet") != "conditional_when_target_workflow_policy_is_missing":
        errors.append(f"{path}: prepare-workflow phase policy must use target_workflow_context_decision_packet for missing context")
    if "operating_decisions_interview" in prepare_policy:
        errors.append(f"{path}: prepare-workflow phase policy must not use operating_decisions_interview")
    prepare_requires = set(str(item) for item in prepare_policy.get("requires", []) or [])
    prepare_conditional_requires = set(str(item) for item in prepare_policy.get("conditional_requires", []) or [])
    if "target_workflow_context_decision_packet" in prepare_requires:
        errors.append(f"{path}: prepare-workflow must not require target_workflow_context_decision_packet unconditionally")
    if "target_workflow_context_decision_packet" not in prepare_conditional_requires:
        errors.append(f"{path}: prepare-workflow conditional_requires must include target_workflow_context_decision_packet")

    phase_by_id = {
        phase.get("id"): phase
        for phase in data.get("phases", []) or []
        if isinstance(phase, dict) and phase.get("id")
    }
    for phase_id in [
        "documentation_disposition_decision",
        "operating_decisions_interview",
        "overlay_draft",
        "project_initialization_gate",
        "target_workflow_context_decision_packet",
        "target_workflow_readiness_gate",
        "initialization_review",
        "finding_validation",
        "human_approval",
    ]:
        phase = phase_by_id.get(phase_id)
        if not isinstance(phase, dict):
            continue
        applies = set(str(item) for item in phase.get("applies_to_intent_modes", []) or [])
        if not applies:
            errors.append(f"{path}: phase {phase_id} must declare applies_to_intent_modes")
        if "unknown-discovery" in applies:
            errors.append(f"{path}: phase {phase_id} must not apply to unknown-discovery by default")
        if "risk-domain-assessment" in applies:
            errors.append(f"{path}: phase {phase_id} must not apply to risk-domain-assessment by default")
    attach = phase_by_id.get("attach_or_verify_upstream")
    if isinstance(attach, dict):
        attach_applies = set(str(item) for item in attach.get("applies_to_intent_modes", []) or [])
        if not attach_applies:
            errors.append(f"{path}: attach_or_verify_upstream must declare applies_to_intent_modes")
        for mode in ["unknown-discovery", "risk-domain-assessment"]:
            if mode in attach_applies:
                errors.append(f"{path}: attach_or_verify_upstream must not apply to {mode} by default")
    for phase_id in ["operating_decisions_interview", "human_approval"]:
        phase = phase_by_id.get(phase_id, {}) or {}
        human = phase.get("human_interaction", {}) or {}
        if human.get("required") is True:
            errors.append(f"{path}: phase {phase_id} human_interaction.required must be conditional")

    expected_mode_phases = {
        "documentation_disposition_decision": {
            "adoption-onboarding",
            "legacy-cleanup",
            "prepare-workflow",
        },
        "legacy_agent_system_discovery": {"adoption-onboarding", "legacy-cleanup"},
        "project_initialization_gate": {"adoption-onboarding"},
        "target_workflow_context_decision_packet": {"prepare-workflow"},
        "target_workflow_readiness_gate": {"prepare-workflow"},
        "initialization_review": {"adoption-onboarding", "prepare-workflow"},
        "finding_validation": {"adoption-onboarding", "prepare-workflow"},
    }
    for phase_id, expected_modes in expected_mode_phases.items():
        phase = phase_by_id.get(phase_id)
        if not isinstance(phase, dict):
            errors.append(f"{path}: project-initialization must include {phase_id} phase")
            continue
        applies = set(str(item) for item in phase.get("applies_to_intent_modes", []) or [])
        if applies != expected_modes:
            errors.append(
                f"{path}: phase {phase_id} must apply exactly to: {', '.join(sorted(expected_modes))}"
            )

    project_gate = phase_by_id.get("project_initialization_gate", {}) or {}
    if project_gate.get("gate") != "project_initialization_gate":
        errors.append(f"{path}: project_initialization_gate phase must bind project_initialization_gate")
    target_gate = phase_by_id.get("target_workflow_readiness_gate", {}) or {}
    if target_gate.get("kind") != "gate":
        errors.append(f"{path}: target_workflow_readiness_gate phase must be kind gate")
    if target_gate.get("gate") != "target_workflow_readiness_gate":
        errors.append(f"{path}: target_workflow_readiness_gate phase must bind target_workflow_readiness_gate")

    initialization_review = phase_by_id.get("initialization_review", {}) or {}
    if initialization_review.get("kind") != "review":
        errors.append(f"{path}: initialization_review phase must be kind review")
    review_runs_after = set(str(item) for item in initialization_review.get("runs_after", []) or [])
    for required_gate_phase in ["project_initialization_gate", "target_workflow_readiness_gate"]:
        if required_gate_phase not in review_runs_after:
            errors.append(f"{path}: initialization_review must run after {required_gate_phase}")
    if initialization_review.get("runs_after_policy") != "after_applicable_intent_mode_gate":
        errors.append(f"{path}: initialization_review must use after_applicable_intent_mode_gate runs_after_policy")

    documentation_disposition = phase_by_id.get("documentation_disposition_decision", {}) or {}
    if documentation_disposition.get("kind") != "decision":
        errors.append(f"{path}: documentation_disposition_decision phase must be kind decision")
    doc_outputs = set(str(item) for item in documentation_disposition.get("outputs", []) or [])
    if "project-documentation-disposition.yaml" not in doc_outputs:
        errors.append(
            f"{path}: documentation_disposition_decision must output project-documentation-disposition.yaml"
        )
    doc_inputs = set(str(item) for item in documentation_disposition.get("inputs", []) or [])
    for required_input in [
        "documentation-history-index.md",
        "project-inventory.json",
        "project-assessment.json",
    ]:
        if required_input not in doc_inputs:
            errors.append(f"{path}: documentation_disposition_decision must consume {required_input}")
    doc_runs_after = set(str(item) for item in documentation_disposition.get("runs_after", []) or [])
    for required_phase in ["documentation_and_history_discovery", "expert_assessment"]:
        if required_phase not in doc_runs_after:
            errors.append(f"{path}: documentation_disposition_decision must run after {required_phase}")

    legacy_decision = phase_by_id.get("legacy_adoption_mode_decision", {}) or {}
    legacy_inputs = set(str(item) for item in legacy_decision.get("inputs", []) or [])
    if "project-documentation-disposition.yaml" not in legacy_inputs:
        errors.append(f"{path}: legacy_adoption_mode_decision must consume project-documentation-disposition.yaml")

    finding_validation = phase_by_id.get("finding_validation", {}) or {}
    if finding_validation.get("kind") != "finding_validation":
        errors.append(f"{path}: finding_validation phase must be kind finding_validation")
    validation_runs_after = set(str(item) for item in finding_validation.get("runs_after", []) or [])
    if "initialization_review" not in validation_runs_after:
        errors.append(f"{path}: finding_validation phase must run after initialization_review")

    human_approval = phase_by_id.get("human_approval", {}) or {}
    human_runs_after = set(str(item) for item in human_approval.get("runs_after", []) or [])
    for required_phase in ["finding_validation", "legacy_migration_or_quarantine_plan"]:
        if required_phase not in human_runs_after:
            errors.append(f"{path}: human_approval must run after {required_phase} when applicable")
    if human_approval.get("runs_after_policy") != "after_applicable_intent_mode_preapproval_phase":
        errors.append(f"{path}: human_approval must use after_applicable_intent_mode_preapproval_phase runs_after_policy")

    phase_order = {
        str(phase.get("id")): index
        for index, phase in enumerate(data.get("phases", []) or [])
        if isinstance(phase, dict) and phase.get("id")
    }
    ordered_backbone = [
        "raw_project_scan",
        "structured_project_inventory",
        "domain_identification",
        "expert_assessment",
    ]
    for before, after in zip(ordered_backbone, ordered_backbone[1:]):
        if before in phase_order and after in phase_order and phase_order[before] >= phase_order[after]:
            errors.append(f"{path}: {before} must appear before {after}")
    for legacy_phase in ["legacy_adoption_mode_decision", "legacy_migration_or_quarantine_plan"]:
        if (
            legacy_phase in phase_order
            and "expert_assessment" in phase_order
            and phase_order[legacy_phase] <= phase_order["expert_assessment"]
        ):
            errors.append(f"{path}: {legacy_phase} must run after expert_assessment")

    forbidden_phase_outputs_by_mode = {
        "prepare-workflow": ["project-operating-decisions.yaml"],
        "unknown-discovery": [
            "project-operating-decisions.yaml",
            "project.yaml draft",
            "workflow bindings draft",
            "project-bound gate drafts",
            "active-instruction-map.yaml",
        ],
        "risk-domain-assessment": [
            "project-operating-decisions.yaml",
            "project.yaml draft",
            "workflow bindings draft",
            "project-bound gate drafts",
            "active-instruction-map.yaml",
        ],
    }
    for phase in data.get("phases", []) or []:
        if not isinstance(phase, dict):
            continue
        applies = set(str(item) for item in phase.get("applies_to_intent_modes", []) or [])
        if not applies and phase_policy.get("phases_without_applies_to_intent_modes_apply_to_all") is True:
            applies = supported
        phase_outputs = [str(item) for item in phase.get("outputs", []) or []]
        phase_human = phase.get("human_interaction", {}) or {}
        response_artifact = str(phase_human.get("response_artifact", ""))
        for mode, forbidden_patterns in forbidden_phase_outputs_by_mode.items():
            if mode not in applies:
                continue
            forbidden_present = [
                item
                for item in [*phase_outputs, response_artifact]
                if any(pattern in item for pattern in forbidden_patterns)
            ]
            if forbidden_present:
                errors.append(
                    f"{path}: phase {phase.get('id')} must not produce {mode} forbidden artifact(s): "
                    + ", ".join(sorted(set(forbidden_present)))
                )

    review = data.get("review", {}) or {}
    if isinstance(review, dict) and review.get("topology") not in {None, "none"}:
        gates = set(str(item) for item in review.get("gates", []) or [])
        for gate_id in ["project_initialization_gate", "target_workflow_readiness_gate"]:
            if gate_id not in gates:
                errors.append(f"{path}: project-initialization review.gates must include {gate_id}")
    return errors

