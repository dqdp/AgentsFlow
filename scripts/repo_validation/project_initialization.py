from __future__ import annotations

from pathlib import Path

from .common import parse_json, parse_yaml, safe_resolve, validate_against_schema


TARGET_WORKFLOW_OPEN_DECISION_SCOPES = {
    "run_scoped",
    "persistent_policy_candidate",
}
TARGET_WORKFLOW_OPEN_DECISION_REQUIRED_FIELDS = {
    "decision_id",
    "owning_requirement_ref",
    "decision_scope",
    "classification",
    "status",
    "affected_artifacts",
    "rationale",
}
TARGET_WORKFLOW_OPEN_DECISION_DEFERRAL_FIELDS = {
    "deferral_constraints",
    "residual_risk",
}

PROJECT_ASSESSMENT_ROLE_ARTIFACTS = {
    "architecture": "project-assessment.architecture.json",
    "verification": "project-assessment.verification.json",
    "adversarial": "project-assessment.adversarial.json",
    "prompt_engineering": "project-assessment.prompt-engineering.json",
}
PROJECT_ASSESSMENT_REQUIRED_ROLES = {"architecture", "verification", "adversarial"}


def target_workflow_has_implementation_phase(root: Path, target_workflow: object) -> bool:
    if not isinstance(target_workflow, str) or not target_workflow:
        return False
    workflow_path = root / "workflows" / target_workflow / "workflow.yaml"
    if not workflow_path.exists():
        return False
    workflow = parse_yaml(workflow_path) or {}
    phases = workflow.get("phases", []) if isinstance(workflow, dict) else []
    return any(
        isinstance(phase, dict) and phase.get("kind") == "implementation"
        for phase in phases
    )


def validate_project_assessment_synthesis_artifact(root: Path, path: Path) -> list[str]:
    errors: list[str] = []
    schema = parse_json(root / "schemas" / "project-assessment.schema.json")
    data = parse_json(path)
    if not isinstance(data, dict):
        return [f"{path}: project assessment synthesis must be a mapping"]

    errors.extend(validate_against_schema(path, data, schema))
    if data.get("role") != "synthesis":
        errors.append(f"{path}: project assessment synthesis role must be synthesis")

    role_reports = data.get("role_reports", []) or []
    if not isinstance(role_reports, list):
        return errors

    seen_roles: set[str] = set()
    for idx, report in enumerate(role_reports):
        if not isinstance(report, dict):
            continue
        role = str(report.get("role", ""))
        artifact = report.get("artifact")
        if role:
            seen_roles.add(role)
        if not isinstance(artifact, str):
            continue
        label = f"{path}: role_reports[{idx}].artifact"
        if not artifact.endswith(".json"):
            errors.append(f"{label} must reference a .json role report artifact")
            continue
        expected_artifact = PROJECT_ASSESSMENT_ROLE_ARTIFACTS.get(role)
        if expected_artifact and artifact != expected_artifact:
            errors.append(f"{path}: role_reports[{idx}] artifact for {role} must be {expected_artifact}")
        artifact_path = safe_resolve(path.parent, artifact, label, errors)
        if artifact_path is None:
            continue
        if not artifact_path.exists():
            errors.append(f"{path}: missing referenced role report artifact: {artifact}")
            continue
        try:
            role_data = parse_json(artifact_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not isinstance(role_data, dict):
            errors.append(f"{artifact_path}: role report must be a mapping")
            continue
        errors.extend(validate_against_schema(artifact_path, role_data, schema))
        if role_data.get("role") != role:
            errors.append(f"{artifact_path}: role report role must match synthesis role_reports entry {role}")
        if role_data.get("role") == "synthesis":
            errors.append(f"{artifact_path}: role report must not be a synthesis artifact")

    missing_roles = sorted(PROJECT_ASSESSMENT_REQUIRED_ROLES - seen_roles)
    if missing_roles:
        errors.append(f"{path}: role_reports missing required roles: {', '.join(missing_roles)}")

    return errors


def validate_project_onboarding_assessment_skill_contract(root: Path) -> list[str]:
    errors: list[str] = []
    skill_dir = root / "skills" / "project-onboarding-assessment"
    skill_md = skill_dir / "SKILL.md"
    skill_yaml = skill_dir / "skill.yaml"

    manifest = parse_yaml(skill_yaml) or {}
    if not isinstance(manifest, dict):
        return [f"{skill_yaml}: skill manifest must be a mapping"]

    outputs = set(str(item) for item in manifest.get("outputs", []) or [])
    required_outputs = {
        "project-assessment.architecture.json",
        "project-assessment.verification.json",
        "project-assessment.adversarial.json",
        "project-assessment.prompt-engineering.json when prompt-sensitive",
        "project-assessment.json",
    }
    missing_outputs = sorted(required_outputs - outputs)
    if missing_outputs:
        errors.append(f"{skill_yaml}: outputs missing: {', '.join(missing_outputs)}")

    text = skill_md.read_text(encoding="utf-8")
    lower_text = text.lower()
    required_phrases = {
        "schemas/project-assessment.schema.json": "schema reference",
        "templates/project-assessment.role.json": "role report template reference",
        "strict json": "strict JSON requirement",
        "before synthesis": "validation-before-synthesis rule",
        "reject": "invalid-output rejection rule",
        "markdown or prose-only": "Markdown/prose-only invalid-output rule",
        "prompt_engineering": "conditional prompt-engineering role",
    }
    for phrase, label in required_phrases.items():
        if phrase not in lower_text:
            errors.append(f"{skill_md}: missing {label}: {phrase}")

    return errors


def validate_project_documentation_disposition_artifact(root: Path, path: Path) -> list[str]:
    schema = parse_json(root / "schemas" / "project-documentation-disposition.schema.json")
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"{path}: project documentation disposition must be a mapping"]
    errors = validate_against_schema(path, data, schema)
    try:
        repo_relative_path = path.absolute().relative_to(root.absolute())
    except ValueError:
        repo_relative_path = None
    is_canonical_template = repo_relative_path == Path(
        "templates/project-documentation-disposition.yaml"
    )
    is_template_artifact = data.get("artifact_role") == "template"
    if is_template_artifact and not is_canonical_template:
        errors.append(
            f"{path}: artifact_role template is reserved for templates/project-documentation-disposition.yaml"
        )
    if not (is_template_artifact and is_canonical_template):
        errors.extend(validate_documentation_adoption_decision_record(root, path, data))
    return errors


def validate_documentation_adoption_decision_record(root: Path, path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    adoption = data.get("documentation_legacy_adoption", {}) or {}
    if not isinstance(adoption, dict):
        return errors
    decision_record = adoption.get("decision_record")
    if not isinstance(decision_record, str) or "#" not in decision_record:
        return errors
    decision_file, decision_id = decision_record.split("#", 1)
    if decision_file != "human-decisions.yaml":
        return errors
    decisions_path = path.parent / decision_file
    if not decisions_path.exists():
        errors.append(f"{path}: documentation_legacy_adoption decision_record missing file: {decision_file}")
        return errors
    try:
        decisions_data = parse_yaml(decisions_path) or {}
    except ValueError as exc:
        errors.append(str(exc))
        return errors
    decisions_schema = parse_json(root / "schemas" / "human-decisions.schema.json")
    errors.extend(validate_against_schema(decisions_path, decisions_data, decisions_schema))
    decisions = decisions_data.get("decisions", []) if isinstance(decisions_data, dict) else []
    if not isinstance(decisions, list):
        errors.append(f"{decisions_path}: decisions must be a list")
        return errors
    matching = [
        decision
        for decision in decisions
        if isinstance(decision, dict) and decision.get("decision_id") == decision_id
    ]
    if not matching:
        errors.append(f"{path}: documentation_legacy_adoption decision_record not found: {decision_record}")
        return errors
    decision = matching[0]
    questions_path = path.parent / "human-questions.yaml"
    if not questions_path.exists():
        errors.append(f"{path}: documentation_legacy_adoption missing human-questions.yaml")
    else:
        try:
            questions_data = parse_yaml(questions_path) or {}
        except ValueError as exc:
            errors.append(str(exc))
            questions_data = {}
        questions = questions_data.get("questions", []) if isinstance(questions_data, dict) else []
        if not isinstance(questions, list):
            errors.append(f"{questions_path}: questions must be a list")
        else:
            question_matching = [
                question
                for question in questions
                if isinstance(question, dict)
                and question.get("decision_id") in {decision_id, decision.get("question_ref")}
            ]
            if not question_matching:
                errors.append(f"{path}: documentation_legacy_adoption matching human question not found")
            else:
                question = question_matching[0]
                if question.get("phase_id") != "documentation_disposition_decision":
                    errors.append(
                        f"{path}: documentation_legacy_adoption question must belong to documentation_disposition_decision"
                    )
                if question.get("status") != "answered":
                    errors.append(
                        f"{path}: documentation_legacy_adoption question must be answered"
                    )
                if question.get("classification") != "blocking-material":
                    errors.append(
                        f"{path}: documentation_legacy_adoption question must be blocking-material"
                    )
                if question.get("answer_required") is not True:
                    errors.append(
                        f"{path}: documentation_legacy_adoption question must require an answer"
                    )
                question_default = question.get("default", {}) or {}
                if question_default.get("allowed") is not False:
                    errors.append(
                        f"{path}: documentation_legacy_adoption question must not allow a default"
                    )
                if question_default.get("id") is not None:
                    errors.append(
                        f"{path}: documentation_legacy_adoption question must not declare a default id"
                    )
                if decision.get("question_ref") != question.get("decision_id"):
                    errors.append(
                        f"{path}: documentation_legacy_adoption decision question_ref must match question decision_id"
                    )
                option_ids = {
                    str(option.get("id"))
                    for option in question.get("options", []) or []
                    if isinstance(option, dict)
                }
                required_mode_options = {
                    "preserve-as-is",
                    "knowledge-extraction",
                    "rewrite-migration",
                    "archive-delete",
                }
                missing_options = sorted(required_mode_options - option_ids)
                extra_options = sorted(option_ids - required_mode_options)
                if missing_options:
                    errors.append(
                        f"{path}: documentation_legacy_adoption question options missing modes: {', '.join(missing_options)}"
                    )
                if extra_options:
                    errors.append(
                        f"{path}: documentation_legacy_adoption question options must not include non-mode ids: {', '.join(extra_options)}"
                    )
                depth_option_ids = {
                    str(option.get("id"))
                    for option in question.get("extraction_depth_options", []) or []
                    if isinstance(option, dict)
                }
                required_depth_options = {"light", "standard", "deep"}
                missing_depth_options = sorted(required_depth_options - depth_option_ids)
                extra_depth_options = sorted(depth_option_ids - required_depth_options)
                if missing_depth_options:
                    errors.append(
                        f"{path}: documentation_legacy_adoption question extraction_depth_options missing: {', '.join(missing_depth_options)}"
                    )
                if extra_depth_options:
                    errors.append(
                        f"{path}: documentation_legacy_adoption question extraction_depth_options must not include unsupported ids: {', '.join(extra_depth_options)}"
                    )
                scope_option_ids = {
                    str(option.get("id"))
                    for option in question.get("persistence_scope_options", []) or []
                    if isinstance(option, dict)
                }
                required_scope_options = {"run-level", "project-level"}
                missing_scope_options = sorted(required_scope_options - scope_option_ids)
                extra_scope_options = sorted(scope_option_ids - required_scope_options)
                if missing_scope_options:
                    errors.append(
                        f"{path}: documentation_legacy_adoption question persistence_scope_options missing: {', '.join(missing_scope_options)}"
                    )
                if extra_scope_options:
                    errors.append(
                        f"{path}: documentation_legacy_adoption question persistence_scope_options must not include unsupported ids: {', '.join(extra_scope_options)}"
                    )
    if decision.get("phase_id") != "documentation_disposition_decision":
        errors.append(
            f"{path}: documentation_legacy_adoption decision_record must point to documentation_disposition_decision"
        )
    if decision.get("status") != "confirmed":
        errors.append(
            f"{path}: documentation_legacy_adoption decision_record must be confirmed"
        )
    if str(decision.get("answered_by", "")) not in {"human", "project-owner"}:
        errors.append(
            f"{path}: documentation_legacy_adoption decision_record must be human-owned"
        )
    if decision.get("classification") != "blocking-material":
        errors.append(
            f"{path}: documentation_legacy_adoption decision_record must be blocking-material"
        )
    answer = decision.get("answer", {}) or {}
    if not isinstance(answer, dict):
        errors.append(f"{path}: documentation_legacy_adoption decision_record answer must be a mapping")
        return errors
    for key in ["mode", "extraction_depth", "persistence_scope"]:
        adoption_value = adoption.get(key)
        if adoption_value is None:
            continue
        if answer.get(key) != adoption_value:
            errors.append(
                f"{path}: documentation_legacy_adoption decision_record answer.{key} must match disposition"
            )
    if adoption.get("mode") == "knowledge-extraction":
        extraction_artifact = adoption.get("extraction_artifact")
        if not isinstance(extraction_artifact, str) or not extraction_artifact:
            errors.append(f"{path}: documentation_legacy_adoption extraction_artifact must be set")
        elif Path(extraction_artifact).name != "project-knowledge-extraction.md":
            errors.append(
                f"{path}: documentation_legacy_adoption extraction_artifact must be project-knowledge-extraction.md"
            )
        else:
            artifact_path = safe_resolve(
                path.parent,
                extraction_artifact,
                f"{path}: documentation_legacy_adoption extraction_artifact",
                errors,
            )
            if artifact_path is None:
                pass
            elif not artifact_path.exists():
                errors.append(
                    f"{path}: documentation_legacy_adoption extraction_artifact missing: {extraction_artifact}"
                )
            elif not artifact_path.read_text(encoding="utf-8").strip():
                errors.append(
                    f"{path}: documentation_legacy_adoption extraction_artifact must not be empty: {extraction_artifact}"
                )

    risk_acceptance = adoption.get("implementation_risk_acceptance")
    scope = data.get("scope", {}) or {}
    if not isinstance(scope, dict):
        scope = {}
    is_light_implementation_prepare = (
        scope.get("intent_mode") == "prepare-workflow"
        and adoption.get("extraction_depth") == "light"
        and target_workflow_has_implementation_phase(root, scope.get("target_workflow"))
    )
    if is_light_implementation_prepare and not isinstance(risk_acceptance, dict):
        errors.append(
            f"{path}: light extraction cannot unlock implementation readiness without human risk acceptance or depth upgrade evidence"
        )
    if isinstance(risk_acceptance, dict):
        risk_decision_record = risk_acceptance.get("decision_record")
        if isinstance(risk_decision_record, str) and risk_decision_record.startswith("human-decisions.yaml#"):
            _, risk_decision_id = risk_decision_record.split("#", 1)
            risk_matching = [
                decision
                for decision in decisions
                if isinstance(decision, dict) and decision.get("decision_id") == risk_decision_id
            ]
            if not risk_matching:
                errors.append(
                    f"{path}: implementation_risk_acceptance decision_record not found: {risk_decision_record}"
                )
            else:
                risk_decision = risk_matching[0]
                if risk_decision.get("status") != "confirmed":
                    errors.append(f"{path}: implementation_risk_acceptance decision_record must be confirmed")
                if str(risk_decision.get("answered_by", "")) not in {"human", "project-owner"}:
                    errors.append(f"{path}: implementation_risk_acceptance decision_record must be human-owned")
                if risk_decision.get("classification") != "blocking-material":
                    errors.append(f"{path}: implementation_risk_acceptance decision_record must be blocking-material")
                if risk_decision.get("phase_id") not in {
                    "documentation_disposition_decision",
                    "target_workflow_context_decision_packet",
                }:
                    errors.append(
                        f"{path}: implementation_risk_acceptance decision_record must belong to documentation disposition or target workflow context"
                    )
                risk_answer = risk_decision.get("answer", {}) or {}
                if not isinstance(risk_answer, dict):
                    errors.append(f"{path}: implementation_risk_acceptance decision_record answer must be a mapping")
                elif (
                    risk_answer.get("accepts_light_extraction_implementation_risk") is not True
                    and risk_answer.get("extraction_depth") != "standard"
                    and risk_answer.get("extraction_depth") != "deep"
                ):
                    errors.append(
                        f"{path}: implementation_risk_acceptance decision_record must accept light extraction implementation risk or upgrade depth"
                    )
        else:
            errors.append(f"{path}: implementation_risk_acceptance decision_record must reference human-decisions.yaml")
    return errors


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
        open_packet = target_decisions.get("open_decision_packet", {}) or {}
        if open_packet.get("packet_kind") != "target_workflow_open_decisions":
            errors.append(
                f"{path}: target_workflow_context_decision_packet open_decision_packet.packet_kind must be target_workflow_open_decisions"
            )
        if open_packet.get("discovered_by") != "target_workflow_readiness_preflight":
            errors.append(
                f"{path}: target_workflow_context_decision_packet open_decision_packet.discovered_by must be target_workflow_readiness_preflight"
            )
        if open_packet.get("owning_requirement_ref_required") is not True:
            errors.append(
                f"{path}: target_workflow_context_decision_packet must require owning_requirement_ref"
            )
        decision_scopes = set(str(item) for item in open_packet.get("allowed_decision_scopes", []) or [])
        missing_scopes = sorted(TARGET_WORKFLOW_OPEN_DECISION_SCOPES - decision_scopes)
        if missing_scopes:
            errors.append(
                f"{path}: target_workflow_context_decision_packet allowed_decision_scopes missing: {', '.join(missing_scopes)}"
            )
        required_fields = set(str(item) for item in open_packet.get("required_fields", []) or [])
        missing_fields = sorted(TARGET_WORKFLOW_OPEN_DECISION_REQUIRED_FIELDS - required_fields)
        if missing_fields:
            errors.append(
                f"{path}: target_workflow_context_decision_packet required_fields missing: {', '.join(missing_fields)}"
            )
        deferral_fields = set(str(item) for item in open_packet.get("deferral_requires", []) or [])
        missing_deferral = sorted(TARGET_WORKFLOW_OPEN_DECISION_DEFERRAL_FIELDS - deferral_fields)
        if missing_deferral:
            errors.append(
                f"{path}: target_workflow_context_decision_packet deferral_requires missing: {', '.join(missing_deferral)}"
            )
        if open_packet.get("persistent_policy_activation_allowed") is not False:
            errors.append(
                f"{path}: target_workflow_context_decision_packet must not activate persistent policy"
            )
        outputs = set(str(item) for item in target_decisions.get("outputs", []) or [])
        if "target workflow human decision packet" not in outputs:
            errors.append(f"{path}: target_workflow_context_decision_packet must output target workflow human decision packet")
        human = target_decisions.get("human_interaction", {}) or {}
        if human.get("response_artifact") == "project-operating-decisions.yaml":
            errors.append(f"{path}: target_workflow_context_decision_packet must not write project-operating-decisions.yaml")
        resume_states = set(str(item) for item in human.get("allowed_resume_states", []) or [])
        if "unresolved" in resume_states:
            errors.append(
                f"{path}: target_workflow_context_decision_packet must not allow bare unresolved resume state"
            )
        if "answered" not in resume_states:
            errors.append(
                f"{path}: target_workflow_context_decision_packet must allow answered resume state"
            )
        if "explicitly_deferred_with_constraints" not in resume_states:
            errors.append(
                f"{path}: target_workflow_context_decision_packet must allow explicitly_deferred_with_constraints resume state"
            )
        resume_policy = human.get("resume_policy", {}) or {}
        if resume_policy.get("unresolved_blocking_material_decisions") != "block_target_workflow_readiness":
            errors.append(
                f"{path}: target_workflow_context_decision_packet must block readiness on unresolved blocking-material decisions"
            )
        inputs = set(str(item) for item in target_decisions.get("inputs", []) or [])
        if "project-documentation-disposition.yaml" not in inputs:
            errors.append(f"{path}: target_workflow_context_decision_packet must consume project-documentation-disposition.yaml")
        if "project-knowledge-extraction.md when documentation_legacy_adoption.mode is knowledge-extraction" not in inputs:
            errors.append(
                f"{path}: target_workflow_context_decision_packet must consume conditional project-knowledge-extraction.md"
            )
    overlay = phase_by_id.get("overlay_draft")
    if overlay:
        overlay_applies = set(str(item) for item in overlay.get("applies_to_intent_modes", []) or [])
        if overlay_applies != {"adoption-onboarding"}:
            errors.append(f"{path}: overlay_draft must apply only to adoption-onboarding")
        inputs = set(overlay.get("inputs", []) or [])
        has_operating_decisions = any(str(item).startswith("project-operating-decisions.yaml") for item in inputs)
        if not has_operating_decisions:
            errors.append(f"{path}: overlay_draft must consume project-operating-decisions.yaml for onboarding")
        if "project-documentation-disposition.yaml" not in inputs:
            errors.append(f"{path}: overlay_draft must consume project-documentation-disposition.yaml")
    target_binding = phase_by_id.get("target_workflow_binding_draft")
    if not isinstance(target_binding, dict):
        errors.append(f"{path}: project-initialization must include target_workflow_binding_draft phase")
    else:
        applies = set(str(item) for item in target_binding.get("applies_to_intent_modes", []) or [])
        if applies != {"prepare-workflow"}:
            errors.append(f"{path}: target_workflow_binding_draft must apply only to prepare-workflow")
        runs_after = set(str(item) for item in target_binding.get("runs_after", []) or [])
        if "target_workflow_readiness_gate" not in runs_after:
            errors.append(f"{path}: target_workflow_binding_draft must run after target_workflow_readiness_gate")
        inputs = set(str(item) for item in target_binding.get("inputs", []) or [])
        for required_input in [
            "project-documentation-disposition.yaml",
            "target-workflow-readiness-gate-report.md",
        ]:
            if required_input not in inputs:
                errors.append(f"{path}: target_workflow_binding_draft must consume {required_input}")
        if not any("target workflow human decision packet" in item for item in inputs):
            errors.append(f"{path}: target_workflow_binding_draft must allow target workflow human decision packet")
        if not any("existing project policy/workflow binding" in item for item in inputs):
            errors.append(f"{path}: target_workflow_binding_draft must allow existing project policy/workflow binding")
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
    allowed_resume_states = set(str(item) for item in human.get("allowed_resume_states", []) or [])
    if "explicitly_deferred_with_constraints" not in allowed_resume_states:
        errors.append(
            f"{path}: human_interaction.allowed_resume_states must include explicitly_deferred_with_constraints"
        )
    if "defaulted" in allowed_resume_states:
        errors.append(
            f"{path}: human_interaction.allowed_resume_states must not include defaulted as a global resume state"
        )
    if "unresolved" in allowed_resume_states:
        errors.append(
            f"{path}: human_interaction.allowed_resume_states must not include unresolved as a global resume state"
        )

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


def validate_project_initialization_expert_assessment_contract(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("name") != "project-initialization":
        return errors

    contract = data.get("expert_assessment_output_contract")
    if not isinstance(contract, dict):
        return [f"{path}: expert_assessment_output_contract is required"]

    if contract.get("response_format") != "strict_json":
        errors.append(f"{path}: expert_assessment_output_contract.response_format must be strict_json")
    if contract.get("schema") != "schemas/project-assessment.schema.json":
        errors.append(
            f"{path}: expert_assessment_output_contract.schema must be schemas/project-assessment.schema.json"
        )
    if contract.get("role_report_template") != "templates/project-assessment.role.json":
        errors.append(
            f"{path}: expert_assessment_output_contract.role_report_template must be templates/project-assessment.role.json"
        )
    if contract.get("synthesis_template") != "templates/project-assessment.json":
        errors.append(
            f"{path}: expert_assessment_output_contract.synthesis_template must be templates/project-assessment.json"
        )
    if contract.get("validation_required_before_synthesis") is not True:
        errors.append(
            f"{path}: expert_assessment_output_contract.validation_required_before_synthesis must be true"
        )
    if contract.get("invalid_output_policy") != "reject_and_rerun_or_pause":
        errors.append(
            f"{path}: expert_assessment_output_contract.invalid_output_policy must be reject_and_rerun_or_pause"
        )
    if contract.get("raw_prose_must_not_be_normalized_as_authoritative") is not True:
        errors.append(
            f"{path}: expert_assessment_output_contract.raw_prose_must_not_be_normalized_as_authoritative must be true"
        )

    prompt_requirements = set(str(item) for item in contract.get("launch_prompt_requirements", []) or [])
    required_prompt_requirements = {
        "return_only_valid_json",
        "no_markdown_or_prose_outside_json",
        "must_conform_to_schema",
        "no_human_questions_directly",
        "read_only_no_tests_no_edits",
    }
    missing_prompt_requirements = sorted(required_prompt_requirements - prompt_requirements)
    if missing_prompt_requirements:
        errors.append(
            f"{path}: expert_assessment_output_contract.launch_prompt_requirements missing: "
            + ", ".join(missing_prompt_requirements)
        )

    synthesis_requirements = set(str(item) for item in contract.get("synthesis_requirements", []) or [])
    required_synthesis_requirements = {
        "all_role_reports_schema_valid",
        "role_report_validation_recorded",
        "invalid_role_output_blocks_synthesis",
        "candidate_findings_not_authoritative",
    }
    missing_synthesis_requirements = sorted(required_synthesis_requirements - synthesis_requirements)
    if missing_synthesis_requirements:
        errors.append(
            f"{path}: expert_assessment_output_contract.synthesis_requirements missing: "
            + ", ".join(missing_synthesis_requirements)
        )

    expert = data.get("expert_assessment", {}) or {}
    if expert.get("fresh_context_no_fork") is not True:
        errors.append(f"{path}: expert_assessment.fresh_context_no_fork must be true")
    if expert.get("reviewers_read_only") is not True:
        errors.append(f"{path}: expert_assessment.reviewers_read_only must be true")
    role_reports = set(str(item) for item in expert.get("role_reports", []) or [])
    required_roles = {"architecture", "verification", "adversarial"}
    missing_roles = sorted(required_roles - role_reports)
    if missing_roles:
        errors.append(f"{path}: expert_assessment.role_reports missing: {', '.join(missing_roles)}")

    conditional_roles = expert.get("conditional_role_reports", []) or []
    prompt_role_present = any(
        isinstance(item, dict) and item.get("role") == "prompt_engineering"
        for item in conditional_roles
    )
    if not prompt_role_present:
        errors.append(f"{path}: expert_assessment.conditional_role_reports must include prompt_engineering")

    phase_by_id = {
        phase.get("id"): phase
        for phase in data.get("phases", []) or []
        if isinstance(phase, dict) and phase.get("id")
    }
    expert_phase = phase_by_id.get("expert_assessment", {}) or {}
    if expert_phase.get("output_contract") != "expert_assessment_output_contract":
        errors.append(f"{path}: expert_assessment phase must bind expert_assessment_output_contract")
    phase_outputs = set(str(item) for item in expert_phase.get("outputs", []) or [])
    for required_output in [
        "project-assessment.architecture.json",
        "project-assessment.verification.json",
        "project-assessment.adversarial.json",
        "project-assessment.json",
    ]:
        if required_output not in phase_outputs:
            errors.append(f"{path}: expert_assessment phase outputs missing {required_output}")
    if not any("project-assessment.prompt-engineering.json" in item for item in phase_outputs):
        errors.append(
            f"{path}: expert_assessment phase outputs must allow project-assessment.prompt-engineering.json"
        )

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
        "target_workflow_binding_draft",
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
        "target_workflow_binding_draft",
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
    if (
        prepare_policy.get("target_workflow_context_decision_packet")
        != "conditional_when_bounded_target_workflow_open_decisions_are_discovered"
    ):
        errors.append(
            f"{path}: prepare-workflow phase policy must use target_workflow_context_decision_packet for bounded target-workflow open decisions"
        )
    if "operating_decisions_interview" in prepare_policy:
        errors.append(f"{path}: prepare-workflow phase policy must not use operating_decisions_interview")
    prepare_requires = set(str(item) for item in prepare_policy.get("requires", []) or [])
    prepare_conditional_requires = set(str(item) for item in prepare_policy.get("conditional_requires", []) or [])
    if "target_workflow_binding_draft" not in prepare_requires:
        errors.append(f"{path}: prepare-workflow requires must include target_workflow_binding_draft")
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
        "target_workflow_binding_draft",
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
        "target_workflow_binding_draft": {"prepare-workflow"},
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
    target_gate_runs_after = set(str(item) for item in target_gate.get("runs_after", []) or [])
    if "target_workflow_context_decision_packet" not in target_gate_runs_after:
        errors.append(f"{path}: target_workflow_readiness_gate must run after target_workflow_context_decision_packet when required")
    if (
        target_gate.get("runs_after_policy")
        != "after_conditional_target_workflow_context_decision_packet_when_required"
    ):
        errors.append(
            f"{path}: target_workflow_readiness_gate must use after_conditional_target_workflow_context_decision_packet_when_required runs_after_policy"
        )
    target_binding = phase_by_id.get("target_workflow_binding_draft", {}) or {}
    if target_binding.get("kind") != "specification":
        errors.append(f"{path}: target_workflow_binding_draft phase must be kind specification")
    target_binding_runs_after = set(str(item) for item in target_binding.get("runs_after", []) or [])
    if "target_workflow_readiness_gate" not in target_binding_runs_after:
        errors.append(f"{path}: target_workflow_binding_draft must run after target_workflow_readiness_gate")
    target_binding_inputs = set(str(item) for item in target_binding.get("inputs", []) or [])
    if "project-knowledge-extraction.md when documentation_legacy_adoption.mode is knowledge-extraction" not in target_binding_inputs:
        errors.append(
            f"{path}: target_workflow_binding_draft must consume conditional project-knowledge-extraction.md"
        )

    initialization_review = phase_by_id.get("initialization_review", {}) or {}
    if initialization_review.get("kind") != "review":
        errors.append(f"{path}: initialization_review phase must be kind review")
    review_runs_after = set(str(item) for item in initialization_review.get("runs_after", []) or [])
    for required_gate_phase in ["project_initialization_gate", "target_workflow_readiness_gate"]:
        if required_gate_phase not in review_runs_after:
            errors.append(f"{path}: initialization_review must run after {required_gate_phase}")
    if "target_workflow_binding_draft" not in review_runs_after:
        errors.append(f"{path}: initialization_review must run after target_workflow_binding_draft")
    if (
        initialization_review.get("runs_after_policy")
        != "after_applicable_intent_mode_gate_and_prepare_workflow_binding_draft"
    ):
        errors.append(
            f"{path}: initialization_review must use after_applicable_intent_mode_gate_and_prepare_workflow_binding_draft runs_after_policy"
        )

    documentation_disposition = phase_by_id.get("documentation_disposition_decision", {}) or {}
    if documentation_disposition.get("kind") != "decision":
        errors.append(f"{path}: documentation_disposition_decision phase must be kind decision")
    doc_outputs = set(str(item) for item in documentation_disposition.get("outputs", []) or [])
    if "project-documentation-disposition.yaml" not in doc_outputs:
        errors.append(
            f"{path}: documentation_disposition_decision must output project-documentation-disposition.yaml"
        )
    extraction_output = (
        "project-knowledge-extraction.md when documentation_legacy_adoption.mode is knowledge-extraction"
    )
    if extraction_output not in doc_outputs:
        errors.append(
            f"{path}: documentation_disposition_decision must output conditional project-knowledge-extraction.md for extraction modes"
        )
    if documentation_disposition.get("legacy_adoption_question_required") is not True:
        errors.append(
            f"{path}: documentation_disposition_decision must require explicit documentation legacy adoption question"
        )
    if documentation_disposition.get("agent_may_select_legacy_adoption_without_human") is not False:
        errors.append(
            f"{path}: documentation_disposition_decision must forbid agent-selected documentation legacy adoption mode"
        )
    disposition_resume_states = (
        documentation_disposition.get("human_interaction", {}).get("allowed_resume_states", [])
    )
    if "defaulted" in disposition_resume_states:
        errors.append(
            f"{path}: documentation_disposition_decision must not allow agent-defaulted documentation legacy adoption"
        )
    if "unresolved" in disposition_resume_states:
        errors.append(
            f"{path}: documentation_disposition_decision must not allow unresolved resume for required documentation legacy adoption"
        )
    supported_documentation_modes = set(
        str(item)
        for item in documentation_disposition.get(
            "supported_documentation_legacy_adoption_modes", []
        )
        or []
    )
    required_documentation_modes = {
        "preserve-as-is",
        "knowledge-extraction",
        "rewrite-migration",
        "archive-delete",
    }
    if supported_documentation_modes != required_documentation_modes:
        errors.append(
            f"{path}: documentation_disposition_decision supported_documentation_legacy_adoption_modes must be: {', '.join(sorted(required_documentation_modes))}"
        )
    supported_extraction_depths = set(
        str(item)
        for item in documentation_disposition.get(
            "supported_documentation_extraction_depths", []
        )
        or []
    )
    required_extraction_depths = {"light", "standard", "deep"}
    if supported_extraction_depths != required_extraction_depths:
        errors.append(
            f"{path}: documentation_disposition_decision supported_documentation_extraction_depths must be: {', '.join(sorted(required_extraction_depths))}"
        )
    extraction_depth_defaults = (
        documentation_disposition.get(
            "default_documentation_extraction_depth_by_intent_mode", {}
        )
        or {}
    )
    if extraction_depth_defaults.get("prepare-workflow") != "standard":
        errors.append(
            f"{path}: documentation_disposition_decision must default prepare-workflow extraction depth to standard"
        )
    implementation_rule = str(
        documentation_disposition.get("implementation_readiness_rule", "")
    )
    if "light" not in implementation_rule or "implementation phase" not in implementation_rule:
        errors.append(
            f"{path}: documentation_disposition_decision must state light extraction implementation readiness rule"
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
    if (
        "target_workflow_context_decision_packet" in phase_order
        and "target_workflow_readiness_gate" in phase_order
        and phase_order["target_workflow_context_decision_packet"] >= phase_order["target_workflow_readiness_gate"]
    ):
        errors.append(
            f"{path}: target_workflow_context_decision_packet must appear before target_workflow_readiness_gate"
        )
    if (
        "target_workflow_readiness_gate" in phase_order
        and "target_workflow_binding_draft" in phase_order
        and phase_order["target_workflow_readiness_gate"] >= phase_order["target_workflow_binding_draft"]
    ):
        errors.append(f"{path}: target_workflow_readiness_gate must appear before target_workflow_binding_draft")
    if (
        "target_workflow_binding_draft" in phase_order
        and "initialization_review" in phase_order
        and phase_order["target_workflow_binding_draft"] >= phase_order["initialization_review"]
    ):
        errors.append(f"{path}: target_workflow_binding_draft must appear before initialization_review")
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
    prepare_workflow_pre_binding_forbidden_outputs = [
        "target workflow binding draft",
        "target workflow gate readiness report",
        "target workflow readiness report",
        "target workflow readiness handoff",
    ]
    prepare_workflow_pre_gate_forbidden_outputs = [
        "target-workflow-readiness-gate-report",
    ]
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
        if "prepare-workflow" in applies and phase.get("id") != "target_workflow_binding_draft":
            pre_binding_present = [
                item
                for item in [*phase_outputs, response_artifact]
                if any(pattern in item for pattern in prepare_workflow_pre_binding_forbidden_outputs)
            ]
            if pre_binding_present:
                errors.append(
                    f"{path}: phase {phase.get('id')} must not produce target workflow binding/readiness handoff before target_workflow_binding_draft: "
                    + ", ".join(sorted(set(pre_binding_present)))
                )
        if "prepare-workflow" in applies and phase.get("id") != "target_workflow_readiness_gate":
            pre_gate_present = [
                item
                for item in [*phase_outputs, response_artifact]
                if any(pattern in item for pattern in prepare_workflow_pre_gate_forbidden_outputs)
            ]
            if pre_gate_present:
                errors.append(
                    f"{path}: phase {phase.get('id')} must not produce target workflow readiness gate report before target_workflow_readiness_gate: "
                    + ", ".join(sorted(set(pre_gate_present)))
                )

    review = data.get("review", {}) or {}
    if isinstance(review, dict) and review.get("topology") not in {None, "none"}:
        gates = set(str(item) for item in review.get("gates", []) or [])
        for gate_id in ["project_initialization_gate", "target_workflow_readiness_gate"]:
            if gate_id not in gates:
                errors.append(f"{path}: project-initialization review.gates must include {gate_id}")
    return errors
