from __future__ import annotations

from pathlib import Path


def validate_workflow_default_strictness(path: Path, data: dict) -> list[str]:
    default = data.get("default_strictness")
    supported = {
        str(item)
        for item in ((data.get("supported_profiles") or {}).get("strictness") or [])
    }
    if default is None:
        return [f"{path}: workflow must declare default_strictness"]
    if supported and str(default) not in supported:
        return [
            f"{path}: default_strictness {default} must be listed in supported_profiles.strictness"
        ]
    return []


def validate_test_framed_implementation(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    phases = data.get("phases", []) or []
    if not isinstance(phases, list):
        return errors
    for idx, phase in enumerate(phases):
        if not isinstance(phase, dict) or phase.get("kind") != "implementation":
            continue
        phase_id = phase.get("id", phase.get("name", f"#{idx}"))
        previous = phases[idx - 1] if idx > 0 and isinstance(phases[idx - 1], dict) else {}
        following = phases[idx + 1] if idx + 1 < len(phases) and isinstance(phases[idx + 1], dict) else {}
        valid_previous = previous.get("test_framing") == "red_capture" or (
            previous.get("test_framing") == "baseline_capture"
            and phase.get("change_type") == "refactor"
        )
        if not valid_previous:
            errors.append(
                f"{path}: implementation phase {phase_id} must be immediately preceded by a red-capture phase "
                "with test_framing: red_capture, or by baseline_capture for change_type: refactor"
            )
        elif previous.get("kind") not in {"verification", "gate"} or not previous.get("gate"):
            errors.append(
                f"{path}: implementation phase {phase_id} framing phase must be verification/gate with gate"
            )
        if following.get("test_framing") != "green_verify":
            errors.append(
                f"{path}: implementation phase {phase_id} must be immediately followed by a green-verify phase "
                "with test_framing: green_verify"
            )
        elif following.get("kind") not in {"verification", "gate"} or not following.get("gate"):
            errors.append(
                f"{path}: implementation phase {phase_id} green phase must be verification/gate with gate"
            )
        elif previous.get("gate") and following.get("gate") and previous.get("gate") != following.get("gate"):
            errors.append(
                f"{path}: implementation phase {phase_id} framing phases should use the same gate"
            )
    return errors


def validate_big_feature_plan_gate_policy(path: Path, data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("name") != "big-feature-contract-first":
        return errors
    phases = [
        phase
        for phase in data.get("phases", []) or []
        if isinstance(phase, dict)
    ]
    phase_by_id = {str(phase.get("id")): phase for phase in phases if phase.get("id")}
    technical_plan = phase_by_id.get("technical_plan")
    plan_gate = phase_by_id.get("plan_gate")
    contract_acceptance = phase_by_id.get("contract_acceptance")
    red_capture = phase_by_id.get("red_capture")
    allowed_pause_phases = {
        str(item)
        for item in ((data.get("human_interaction") or {}).get("allowed_pause_phases") or [])
    }
    required_plan_artifacts = {
        "repository-grounding-report.md",
        "plan.md",
        "task-breakdown.md",
        "decision-contract.md",
    }
    if not isinstance(technical_plan, dict):
        errors.append(f"{path}: big-feature-contract-first must include technical_plan phase before plan_gate")
    else:
        outputs = set(str(item) for item in technical_plan.get("outputs", []) or [])
        missing_outputs = sorted(required_plan_artifacts - outputs)
        if missing_outputs:
            errors.append(f"{path}: technical_plan phase missing outputs: {', '.join(missing_outputs)}")
        applies = set(str(item) for item in technical_plan.get("applies_to_strictness", []) or [])
        if applies != {"L3", "L4"}:
            errors.append(f"{path}: technical_plan phase must apply exactly to effective strictness values L3 and L4")
    if not isinstance(plan_gate, dict):
        errors.append(f"{path}: big-feature-contract-first must include plan_gate phase")
    else:
        if plan_gate.get("kind") not in {"gate", "verification"}:
            errors.append(f"{path}: plan_gate phase must be kind gate or verification")
        if plan_gate.get("gate") != "plan_gate":
            errors.append(f"{path}: plan_gate phase must bind gate plan_gate")
        applies = set(str(item) for item in plan_gate.get("applies_to_strictness", []) or [])
        if applies != {"L3", "L4"}:
            errors.append(f"{path}: plan_gate phase must apply exactly to effective strictness values L3 and L4")
        runs_after = set(str(item) for item in plan_gate.get("runs_after", []) or [])
        if "technical_plan" not in runs_after:
            errors.append(f"{path}: plan_gate phase must run after technical_plan")
    if not isinstance(contract_acceptance, dict):
        errors.append(
            f"{path}: big-feature-contract-first must include contract_acceptance phase"
        )
    else:
        if contract_acceptance.get("kind") != "decision":
            errors.append(f"{path}: contract_acceptance phase must be kind decision")
        human_interaction = contract_acceptance.get("human_interaction", {}) or {}
        if human_interaction.get("required") is not True:
            errors.append(
                f"{path}: contract_acceptance human_interaction.required must be true"
            )
        runs_after = set(str(item) for item in contract_acceptance.get("runs_after", []) or [])
        if "plan_gate" not in runs_after:
            errors.append(f"{path}: contract_acceptance phase must run after plan_gate")
        if "contract_acceptance" not in allowed_pause_phases:
            errors.append(
                f"{path}: human_interaction.allowed_pause_phases must include contract_acceptance"
            )
        decision_review = contract_acceptance.get("decision_review_contract")
        if not isinstance(decision_review, dict):
            errors.append(
                f"{path}: contract_acceptance must declare decision_review_contract"
            )
        else:
            if decision_review.get("artifact") != "decision-contract.md":
                errors.append(
                    f"{path}: contract_acceptance decision_review_contract.artifact must be decision-contract.md"
                )
            if decision_review.get("required_before_prompt") is not True:
                errors.append(
                    f"{path}: contract_acceptance decision_review_contract.required_before_prompt must be true"
                )
            required_sections = {
                "open_decision_inventory",
                "per_decision_options",
                "tradeoffs",
                "recommended_path",
                "rationale",
                "human_acceptance_question",
            }
            declared_sections = {
                str(item) for item in decision_review.get("required_sections", []) or []
            }
            missing_sections = sorted(required_sections - declared_sections)
            if missing_sections:
                errors.append(
                    f"{path}: contract_acceptance decision_review_contract missing required_sections: "
                    + ", ".join(missing_sections)
                )
    if isinstance(red_capture, dict):
        runs_after = set(str(item) for item in red_capture.get("runs_after", []) or [])
        if "plan_gate" not in runs_after:
            errors.append(f"{path}: red_capture phase must run after plan_gate")
        if "contract_acceptance" not in runs_after:
            errors.append(
                f"{path}: red_capture phase must run after contract_acceptance"
            )
        if red_capture.get("runs_after_policy") != "after_applicable_strictness_gate":
            errors.append(f"{path}: red_capture phase must use after_applicable_strictness_gate runs_after_policy")
    review_gates = set(str(item) for item in ((data.get("review", {}) or {}).get("gates", []) or []))
    if "plan_gate" not in review_gates:
        errors.append(f"{path}: review.gates must include plan_gate")
    concrete_gates = set(str(item) for item in data.get("concrete_gates", []) or [])
    if "plan_gate" not in concrete_gates:
        errors.append(f"{path}: concrete_gates must include plan_gate")
    return errors


def validate_phase_scripts_declared(path: Path, data: dict) -> list[str]:
    uses_scripts = set((data.get("uses") or {}).get("scripts", []) or [])
    missing: set[str] = set()
    for phase in data.get("phases", []) or []:
        if not isinstance(phase, dict):
            continue
        for script in phase.get("scripts", []) or []:
            if script not in uses_scripts:
                missing.add(str(script))
    if missing:
        return [f"{path}: phase scripts missing from uses.scripts: {', '.join(sorted(missing))}"]
    return []
