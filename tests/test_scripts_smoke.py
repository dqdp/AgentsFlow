from __future__ import annotations

import os
import subprocess
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_CLAUDE_ENV = [
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
]


def clean_env() -> dict[str, str]:
    env = os.environ.copy()
    for name in FORBIDDEN_CLAUDE_ENV:
        env.pop(name, None)
    return env


def run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=env,
    )


def reviewer_report_context(
    reviewer: str,
    packet_ref: object,
    material_change_id: str | None = None,
    run_id: str = "2026-06-17-add-calculator",
) -> dict[str, str]:
    context = {
        "run_id": run_id,
        "review_packet_path": str(packet_ref),
        "reviewer_instance_id": reviewer,
    }
    if material_change_id:
        context["material_change_id"] = material_change_id
    return context


def test_example_contract_lint_passes() -> None:
    result = run("scripts/contract_lint.py", "--contract", "examples/memory-policy/Docs/contracts/memory-policy.contract.md")
    assert result.returncode == 0, result.stdout + result.stderr


def test_example_gherkin_lint_passes() -> None:
    result = run("scripts/gherkin_lint.py", "--contract", "examples/memory-policy/Docs/contracts/memory-policy.contract.md")
    assert result.returncode == 0, result.stdout + result.stderr


def test_example_boundary_check_passes() -> None:
    result = run(
        "scripts/boundary_check.py",
        "--contract", "examples/memory-policy/Docs/contracts/memory-policy.contract.md",
        "--changed-files", "examples/memory-policy/changed-files.txt",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_gate_runner_manifest_dry_run(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "gate-report.json"
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "gates" / "run_gate.py"), "--gate", str(root / "gates" / "contract_gate.yaml"), "--output", str(out), "--dry-run"],
        cwd=root,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert out.exists()

def test_behavior_binding_check_passes() -> None:
    result = run("scripts/bdd_binding_check.py", "--bindings", "examples/memory-policy/Docs/contracts/memory-policy.bindings.yaml")
    assert result.returncode == 0, result.stdout + result.stderr


def test_agentsflow_v02_behavior_contract_passes() -> None:
    contract = "docs/contracts/agentsflow-v0.2-mvp.contract.md"
    bindings = "docs/contracts/agentsflow-v0.2-mvp.bindings.yaml"

    contract_result = run("scripts/contract_lint.py", "--contract", contract)
    assert contract_result.returncode == 0, contract_result.stdout + contract_result.stderr

    gherkin_result = run("scripts/gherkin_lint.py", "--contract", contract)
    assert gherkin_result.returncode == 0, gherkin_result.stdout + gherkin_result.stderr

    binding_result = run("scripts/bdd_binding_check.py", "--bindings", bindings)
    assert binding_result.returncode == 0, binding_result.stdout + binding_result.stderr


def test_behavior_binding_check_rejects_unknown_contract_scenario(tmp_path) -> None:
    import yaml

    contract_src = ROOT / "docs/contracts/agentsflow-v0.2-mvp.contract.md"
    bindings_src = ROOT / "docs/contracts/agentsflow-v0.2-mvp.bindings.yaml"
    contract_dst = tmp_path / contract_src.name
    bindings_dst = tmp_path / bindings_src.name
    contract_dst.write_text(contract_src.read_text(encoding="utf-8"), encoding="utf-8")
    bindings = yaml.safe_load(bindings_src.read_text(encoding="utf-8"))
    target_binding = next(binding for binding in bindings["bindings"] if binding["id"] == "AF-V02-BHV-008")
    target_binding["scenario"] = "Prepare-workflow missing context or design forks use a run-level decision packet"
    bindings_dst.write_text(yaml.safe_dump(bindings, sort_keys=False), encoding="utf-8")

    result = run("scripts/bdd_binding_check.py", "--bindings", str(bindings_dst))
    assert result.returncode != 0
    assert "scenario is not declared in contract" in (result.stdout + result.stderr)


def test_behavior_binding_check_rejects_missing_required_contract_source(tmp_path) -> None:
    import yaml

    contract_src = ROOT / "docs/contracts/agentsflow-v0.2-mvp.contract.md"
    bindings_src = ROOT / "docs/contracts/agentsflow-v0.2-mvp.bindings.yaml"
    contract_dst = tmp_path / contract_src.name
    bindings_dst = tmp_path / bindings_src.name
    contract_dst.write_text(contract_src.read_text(encoding="utf-8"), encoding="utf-8")
    bindings = yaml.safe_load(bindings_src.read_text(encoding="utf-8"))
    target_binding = next(binding for binding in bindings["bindings"] if binding["id"] == "AF-V02-BHV-008")
    target_binding["source"]["path"] = "missing.contract.md"
    bindings_dst.write_text(yaml.safe_dump(bindings, sort_keys=False), encoding="utf-8")

    result = run("scripts/bdd_binding_check.py", "--bindings", str(bindings_dst))
    assert result.returncode != 0
    assert "source contract file does not exist" in (result.stdout + result.stderr)


def test_behavior_binding_check_rejects_missing_task_contract_for_run_binding(tmp_path) -> None:
    import yaml

    bindings_src = (
        ROOT
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/behavior.bindings.yaml"
    )
    bindings = yaml.safe_load(bindings_src.read_text(encoding="utf-8"))
    bindings_dst = tmp_path / "behavior.bindings.yaml"
    bindings_dst.write_text(yaml.safe_dump(bindings, sort_keys=False), encoding="utf-8")

    result = run("scripts/bdd_binding_check.py", "--bindings", str(bindings_dst))
    assert result.returncode != 0
    assert "contract file does not exist: task.contract.md" in (result.stdout + result.stderr)


def test_behavior_binding_schema_allows_spec_only_bindings(tmp_path) -> None:
    import json

    import jsonschema
    import yaml

    schema = json.loads(
        (ROOT / "schemas/behavior-binding.schema.json").read_text(encoding="utf-8")
    )
    example = yaml.safe_load(
        (ROOT / "examples/memory-policy/Docs/contracts/memory-policy.bindings.yaml").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.Draft202012Validator(schema).validate(example)

    invalid = {
        "version": 1,
        "contract": "task.contract.md",
        "bindings": [
            {
                "id": "REQ-MISSING-CHECK",
                "scenario": "Required scenario has executable evidence",
                "required": True,
                "checks": [],
                "gates": [],
            }
        ],
    }
    validator = jsonschema.Draft202012Validator(schema)
    assert list(validator.iter_errors(invalid))

    invalid_path = tmp_path / "invalid.bindings.yaml"
    invalid_path.write_text(yaml.safe_dump(invalid), encoding="utf-8")
    result = run("scripts/bdd_binding_check.py", "--bindings", str(invalid_path))
    assert result.returncode != 0
    assert "has no checks" in (result.stdout + result.stderr)


def test_behavior_binding_schema_allows_risk_path_metadata(tmp_path) -> None:
    import json

    import jsonschema
    import yaml

    schema = json.loads(
        (ROOT / "schemas/behavior-binding.schema.json").read_text(encoding="utf-8")
    )
    binding = yaml.safe_load((ROOT / "templates/behavior-bindings.yaml").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(binding)

    invalid = yaml.safe_load((ROOT / "templates/behavior-bindings.yaml").read_text(encoding="utf-8"))
    invalid["bindings"][0]["evidence_class"] = "spreadsheet"
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(invalid))

    binding_path = tmp_path / "risk.bindings.yaml"
    binding_path.write_text(yaml.safe_dump(binding), encoding="utf-8")
    result = run("scripts/bdd_binding_check.py", "--bindings", "templates/behavior-bindings.yaml")
    assert result.returncode == 0, result.stdout + result.stderr


def test_project_binding_validation_passes() -> None:
    result = run("scripts/validate_project_binding.py", "--project", "examples/project-overlay", "--agentsflow-root", ".")
    assert result.returncode == 0, result.stdout + result.stderr


def test_primary_e2e_project_binding_validation_passes() -> None:
    result = run("scripts/validate_project_binding.py", "--project", "examples/e2e/minimal-python-project", "--agentsflow-root", ".")
    assert result.returncode == 0, result.stdout + result.stderr


def test_project_binding_requires_strictness_applicable_gates(tmp_path) -> None:
    import shutil
    import yaml

    project = tmp_path / "project"
    shutil.copytree(ROOT / "examples/project-overlay/.agentsflow", project / ".agentsflow")
    binding_path = project / ".agentsflow/workflows/big-feature-contract-first.binding.yaml"
    binding = yaml.safe_load(binding_path.read_text(encoding="utf-8"))
    binding["gates"].pop("plan_gate")
    binding_path.write_text(yaml.safe_dump(binding, sort_keys=False), encoding="utf-8")

    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode != 0
    assert "missing project gate binding(s): plan_gate" in (result.stdout + result.stderr)


def test_project_binding_does_not_require_higher_strictness_gate_for_l2(tmp_path) -> None:
    import shutil
    import yaml

    project = tmp_path / "project"
    shutil.copytree(ROOT / "examples/project-overlay/.agentsflow", project / ".agentsflow")
    binding_path = project / ".agentsflow/workflows/big-feature-contract-first.binding.yaml"
    binding = yaml.safe_load(binding_path.read_text(encoding="utf-8"))
    binding["strictness"] = "L2"
    binding["strictness_source"] = "project_override"
    binding["strictness_override_reason"] = "Test fixture intentionally exercises the lighter contract profile."
    binding["gates"].pop("plan_gate")
    binding_path.write_text(yaml.safe_dump(binding, sort_keys=False), encoding="utf-8")

    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode == 0, result.stdout + result.stderr


def test_project_binding_strictness_override_requires_reason(tmp_path) -> None:
    import shutil
    import yaml

    project = tmp_path / "project"
    shutil.copytree(ROOT / "examples/e2e/minimal-python-project/.agentsflow", project / ".agentsflow")
    binding_path = project / ".agentsflow/workflows/big-feature-contract-first.binding.yaml"
    binding = yaml.safe_load(binding_path.read_text(encoding="utf-8"))
    binding["strictness_source"] = "project_override"
    binding.pop("strictness_override_reason", None)
    binding_path.write_text(yaml.safe_dump(binding, sort_keys=False), encoding="utf-8")

    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode != 0
    assert "strictness_override_reason" in (result.stdout + result.stderr)


def test_project_binding_rejects_raw_strictness_without_override_source(tmp_path) -> None:
    import shutil
    import yaml

    project = tmp_path / "project"
    shutil.copytree(ROOT / "examples/project-overlay/.agentsflow", project / ".agentsflow")
    binding_path = project / ".agentsflow/workflows/big-feature-contract-first.binding.yaml"
    binding = yaml.safe_load(binding_path.read_text(encoding="utf-8"))
    binding["strictness"] = "L2"
    binding.pop("strictness_source", None)
    binding.pop("strictness_override_reason", None)
    binding["gates"].pop("plan_gate")
    binding_path.write_text(yaml.safe_dump(binding, sort_keys=False), encoding="utf-8")

    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "strictness_source" in output
    assert "strictness_override_reason" in output
    assert "missing project gate binding(s): plan_gate" in output


def test_project_binding_rejects_unsupported_strictness_override(tmp_path) -> None:
    import shutil
    import yaml

    project = tmp_path / "project"
    shutil.copytree(ROOT / "examples/project-overlay/.agentsflow", project / ".agentsflow")
    binding_path = project / ".agentsflow/workflows/big-feature-contract-first.binding.yaml"
    binding = yaml.safe_load(binding_path.read_text(encoding="utf-8"))
    binding["strictness"] = "L0"
    binding["strictness_source"] = "project_override"
    binding["strictness_override_reason"] = "Exercise unsupported strictness validation."
    binding_path.write_text(yaml.safe_dump(binding, sort_keys=False), encoding="utf-8")

    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode != 0
    assert "strictness L0 is not supported by upstream workflow" in (result.stdout + result.stderr)


def test_project_binding_rejects_strictness_override_without_workflow_support_list(tmp_path) -> None:
    import shutil
    import yaml

    agentsflow_root = tmp_path / "agentsflow"
    for dirname in ["schemas", "profiles", "gates", "workflows"]:
        shutil.copytree(ROOT / dirname, agentsflow_root / dirname)
    workflow_path = agentsflow_root / "workflows/big-feature-contract-first/workflow.yaml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    workflow["supported_profiles"].pop("strictness", None)
    workflow_path.write_text(yaml.safe_dump(workflow, sort_keys=False), encoding="utf-8")

    project = tmp_path / "project"
    shutil.copytree(ROOT / "examples/e2e/minimal-python-project/.agentsflow", project / ".agentsflow")

    result = run(
        "scripts/validate_project_binding.py",
        "--project",
        str(project),
        "--agentsflow-root",
        str(agentsflow_root),
    )
    assert result.returncode != 0
    assert "local strictness override requires upstream workflow supported_profiles.strictness" in (
        result.stdout + result.stderr
    )


def test_project_binding_rejects_invalid_review_policy(tmp_path) -> None:
    import shutil
    import yaml

    project = tmp_path / "project"
    shutil.copytree(ROOT / "examples/project-overlay/.agentsflow", project / ".agentsflow")
    binding_path = project / ".agentsflow/workflows/big-feature-contract-first.binding.yaml"
    binding = yaml.safe_load(binding_path.read_text(encoding="utf-8"))
    binding["review"]["topology"] = "homogeneous-dual"
    binding["review"]["composition"] = "heterogeneous"
    binding_path.write_text(yaml.safe_dump(binding, sort_keys=False), encoding="utf-8")

    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode != 0
    assert "review.composition must be homogeneous" in (result.stdout + result.stderr)


def test_project_binding_rejects_invalid_gate_instrument_type(tmp_path) -> None:
    import shutil
    import yaml

    project = tmp_path / "project"
    shutil.copytree(ROOT / "examples/project-overlay/.agentsflow", project / ".agentsflow")
    gate_path = project / ".agentsflow/gates/verification_gate.yaml"
    gate = yaml.safe_load(gate_path.read_text(encoding="utf-8"))
    gate["instruments"][0]["type"] = "script"
    gate_path.write_text(yaml.safe_dump(gate, sort_keys=False), encoding="utf-8")

    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode != 0
    assert "unknown type script" in (result.stdout + result.stderr)


def test_project_binding_rejects_missing_workflows_directory(tmp_path) -> None:
    import shutil

    project = tmp_path / "project"
    shutil.copytree(ROOT / "examples/project-overlay/.agentsflow", project / ".agentsflow")
    shutil.rmtree(project / ".agentsflow/workflows")

    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode != 0
    assert "missing workflows directory" in (result.stdout + result.stderr)


def test_project_binding_rejects_missing_required_gate_binding(tmp_path) -> None:
    import shutil
    import yaml

    project = tmp_path / "project"
    shutil.copytree(ROOT / "examples/project-overlay/.agentsflow", project / ".agentsflow")
    binding_path = project / ".agentsflow/workflows/big-feature-contract-first.binding.yaml"
    binding = yaml.safe_load(binding_path.read_text(encoding="utf-8"))
    binding["gates"] = {}
    binding_path.write_text(yaml.safe_dump(binding, sort_keys=False), encoding="utf-8")

    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode != 0
    assert "missing project gate binding(s): plan_gate, verification_gate" in (result.stdout + result.stderr)


def test_project_binding_rejects_wrong_upstream_gate_id(tmp_path) -> None:
    import shutil
    import yaml

    project = tmp_path / "project"
    shutil.copytree(ROOT / "examples/project-overlay/.agentsflow", project / ".agentsflow")
    binding_path = project / ".agentsflow/workflows/big-feature-contract-first.binding.yaml"
    binding = yaml.safe_load(binding_path.read_text(encoding="utf-8"))
    binding["gates"]["verification_gate"]["extends"] = "gates/contract_gate.yaml"
    binding_path.write_text(yaml.safe_dump(binding, sort_keys=False), encoding="utf-8")
    gate_path = project / ".agentsflow/gates/verification_gate.yaml"
    gate = yaml.safe_load(gate_path.read_text(encoding="utf-8"))
    gate["extends"] = "gates/contract_gate.yaml"
    gate_path.write_text(yaml.safe_dump(gate, sort_keys=False), encoding="utf-8")

    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode != 0
    assert "extends upstream gate id contract_gate" in (result.stdout + result.stderr)


def test_big_feature_requires_contract_acceptance() -> None:
    import copy
    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    from repo_validation.workflows import validate_big_feature_plan_gate_policy

    workflow_path = ROOT / "workflows/big-feature-contract-first/workflow.yaml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    assert validate_big_feature_plan_gate_policy(workflow_path, workflow) == []

    without_acceptance = copy.deepcopy(workflow)
    without_acceptance["phases"] = [
        phase
        for phase in without_acceptance["phases"]
        if phase.get("id") != "contract_acceptance"
    ]
    errors = validate_big_feature_plan_gate_policy(workflow_path, without_acceptance)
    assert any("contract_acceptance" in error for error in errors)

    without_red_dependency = copy.deepcopy(workflow)
    for phase in without_red_dependency["phases"]:
        if phase.get("id") == "red_capture":
            phase["runs_after"] = ["plan_gate"]
    errors = validate_big_feature_plan_gate_policy(workflow_path, without_red_dependency)
    assert any("red_capture phase must run after contract_acceptance" in error for error in errors)

    without_design_review = copy.deepcopy(workflow)
    for phase in without_design_review["phases"]:
        if phase.get("id") == "contract_acceptance":
            phase.pop("decision_review_contract", None)
    errors = validate_big_feature_plan_gate_policy(workflow_path, without_design_review)
    assert any("contract_acceptance must declare decision_review_contract" in error for error in errors)

    without_pause_phase = copy.deepcopy(workflow)
    allowed_pause_phases = without_pause_phase["human_interaction"]["allowed_pause_phases"]
    allowed_pause_phases.remove("contract_acceptance")
    errors = validate_big_feature_plan_gate_policy(workflow_path, without_pause_phase)
    assert any("human_interaction.allowed_pause_phases must include contract_acceptance" in error for error in errors)


def test_review_fusion_reusable_pipeline_is_documented() -> None:
    review_model = (ROOT / "docs/review-fusion-model.md").read_text(encoding="utf-8")
    fusion_skill = (ROOT / "skills/fusion-synthesis/SKILL.md").read_text(encoding="utf-8")
    fusion_template = (ROOT / "templates/fusion-report.md").read_text(encoding="utf-8")
    validation_template = (ROOT / "templates/finding-validation-report.md").read_text(encoding="utf-8")
    combined = "\n".join(
        [review_model, fusion_skill, fusion_template, validation_template]
    ).lower()

    required_terms = [
        "mechanical intake",
        "canonical finding",
        "duplicate",
        "related",
        "conflict",
        "topic-pair comparison",
        "authority boundary",
        "human-mediated",
    ]
    for term in required_terms:
        assert term in combined


def test_finding_validation_calibrates_blocker_severity() -> None:
    documents = [
        ROOT / "AGENTS.md",
        ROOT / "docs/review-control-model.md",
        ROOT / "docs/review-agent-interaction-protocol.md",
        ROOT / "docs/review-fusion-model.md",
        ROOT / "docs/review-profile-model.md",
        ROOT / "docs/pr-merge-readiness.md",
        ROOT / "profiles/review_profiles/collision-control.yaml",
        ROOT / "profiles/review_topologies/single-reviewer.yaml",
        ROOT / "workflows/pr-merge-readiness/workflow.yaml",
        ROOT / "templates/project-operating-decisions.yaml",
        ROOT / "skills/fusion-synthesis/SKILL.md",
        ROOT / "skills/project-operating-decisions-interview/SKILL.md",
        ROOT / "templates/finding-validation-report.md",
        ROOT / "templates/fusion-report.md",
        ROOT / "templates/review-cycle-report.md",
        ROOT / "templates/review-prompts/base.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in documents).lower()

    required_terms = [
        "blocker path",
        "candidate severity",
        "validated severity",
        "acceptance consequence",
        "risk-surface or failure path matrix membership alone",
    ]
    for term in required_terms:
        assert term in combined

    control_model = (ROOT / "docs/review-control-model.md").read_text(encoding="utf-8").lower()
    interaction_protocol = (ROOT / "docs/review-agent-interaction-protocol.md").read_text(
        encoding="utf-8"
    ).lower()
    fusion_model = (ROOT / "docs/review-fusion-model.md").read_text(encoding="utf-8").lower()
    validation_template = (ROOT / "templates/finding-validation-report.md").read_text(
        encoding="utf-8"
    ).lower()
    review_cycle_template = (ROOT / "templates/review-cycle-report.md").read_text(
        encoding="utf-8"
    ).lower()
    collision_profile = (ROOT / "profiles/review_profiles/collision-control.yaml").read_text(
        encoding="utf-8"
    ).lower()
    pr_readiness_workflow = (ROOT / "workflows/pr-merge-readiness/workflow.yaml").read_text(
        encoding="utf-8"
    ).lower()
    pr_readiness_docs = (ROOT / "docs/pr-merge-readiness.md").read_text(encoding="utf-8").lower()

    assert "its validated severity is p0/p1 with a grounded blocker path" in control_model
    assert "plausible blocker-path candidate findings" in interaction_protocol
    assert "plausible blocker-path candidate findings" in fusion_model
    assert "plausible blocker-path candidate findings" in collision_profile
    assert "fail closed" in pr_readiness_workflow
    assert "source review/fusion" in pr_readiness_workflow
    assert "not by this readiness evaluator" in pr_readiness_workflow
    assert "plausible blocker-path candidate findings" in pr_readiness_docs
    assert "yes if mandatory evidence or grounded p0/p1 blocker path" in validation_template
    assert "rejected or downgraded plausible blocker-path findings" in review_cycle_template

    legacy_blocker_phrases = [
        "its severity is p0/p1, or when mandatory verification evidence is missing",
        "blocker-level candidate findings were rejected or downgraded",
        "rejects or downgrades p0/p1 candidate findings",
        "rejected or downgraded p0/p1 candidate findings",
        "rejected or downgraded p0/p1 findings",
        "yes if mandatory evidence or p0/p1",
    ]
    for phrase in legacy_blocker_phrases:
        assert phrase not in combined


def test_finding_validation_boundary_trace_is_trigger_based() -> None:
    protocol = (ROOT / "docs/review-agent-interaction-protocol.md").read_text(
        encoding="utf-8"
    ).lower()
    fusion_model = (ROOT / "docs/review-fusion-model.md").read_text(encoding="utf-8").lower()
    fusion_skill = (ROOT / "skills/fusion-synthesis/SKILL.md").read_text(encoding="utf-8").lower()
    validation_template = (ROOT / "templates/finding-validation-report.md").read_text(
        encoding="utf-8"
    ).lower()
    fusion_template = (ROOT / "templates/fusion-report.md").read_text(encoding="utf-8").lower()
    reviewer_prompt = (ROOT / "templates/review-prompts/base.md").read_text(encoding="utf-8").lower()

    combined = "\n".join(
        [
            protocol,
            fusion_model,
            fusion_skill,
            validation_template,
            fusion_template,
            reviewer_prompt,
        ]
    )

    required_terms = [
        "boundary trace",
        "trigger conditions",
        "accepted p0/p1",
        "mandatory evidence gap",
        "boundary impact is not severity",
        "main/orchestrating agent owns boundary trace validation",
        "reviewers may suggest affected boundaries",
        "suspected boundary impact",
    ]
    for term in required_terms:
        assert term in combined

    for label in [
        "docs-rule",
        "reviewer-output",
        "schema",
        "prompt-rendering",
        "external-normalization",
        "artifact-storage",
        "evaluator",
        "contract-evidence",
        "generated-artifacts",
        "human-decision",
    ]:
        assert label in validation_template

    assert "required only when triggered" in validation_template
    assert "provider" in validation_template
    assert "reviewer-reported plausible boundary-loss path" in validation_template
    assert "schema, prompt rendering, reviewer output" in protocol
    assert "provider, artifact storage, contract evidence" in protocol
    assert "not a new workflow" in protocol
    assert "not a new artifact type" in protocol
    assert "do not require boundary trace for every p2/p3" in protocol


def test_project_binding_rejects_path_escape(tmp_path) -> None:
    import shutil
    import yaml

    project = tmp_path / "project"
    shutil.copytree(ROOT / "examples/project-overlay/.agentsflow", project / ".agentsflow")
    binding_path = project / ".agentsflow/workflows/big-feature-contract-first.binding.yaml"
    binding = yaml.safe_load(binding_path.read_text(encoding="utf-8"))
    binding["gates"]["verification_gate"]["runner"] = "../outside.sh"
    binding_path.write_text(yaml.safe_dump(binding, sort_keys=False), encoding="utf-8")

    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode != 0
    assert "relative non-escaping path" in (result.stdout + result.stderr)



def test_project_intake_validation_passes() -> None:
    result = run("scripts/validate_project_intake.py", "--intake", "examples/project-initialization/project-intake.yaml")
    assert result.returncode == 0, result.stdout + result.stderr


def test_project_intake_prepare_workflow_requires_target_workflow(tmp_path) -> None:
    import yaml

    intake = yaml.safe_load((ROOT / "examples/project-initialization/project-intake.yaml").read_text(encoding="utf-8"))
    intake["intent_mode"] = "prepare-workflow"
    intake["target_workflow"] = None
    path = tmp_path / "project-intake.yaml"
    path.write_text(yaml.safe_dump(intake, sort_keys=False), encoding="utf-8")

    result = run("scripts/validate_project_intake.py", "--intake", str(path))
    assert result.returncode != 0
    assert "target_workflow must be a non-empty string" in (result.stdout + result.stderr)

    intake["target_workflow"] = 123
    path.write_text(yaml.safe_dump(intake, sort_keys=False), encoding="utf-8")
    result = run("scripts/validate_project_intake.py", "--intake", str(path))
    assert result.returncode != 0
    assert "target_workflow must be a non-empty string" in (result.stdout + result.stderr)

    intake["target_workflow"] = "not-a-real-workflow"
    path.write_text(yaml.safe_dump(intake, sort_keys=False), encoding="utf-8")
    result = run("scripts/validate_project_intake.py", "--intake", str(path))
    assert result.returncode != 0
    assert "target_workflow must match a v0.2 supported target workflow id" in (result.stdout + result.stderr)

    intake["target_workflow"] = "safe-refactor"
    path.write_text(yaml.safe_dump(intake, sort_keys=False), encoding="utf-8")
    result = run("scripts/validate_project_intake.py", "--intake", str(path))
    assert result.returncode != 0
    assert "target_workflow must match a v0.2 supported target workflow id" in (result.stdout + result.stderr)

    intake["target_workflow"] = "project-initialization"
    path.write_text(yaml.safe_dump(intake, sort_keys=False), encoding="utf-8")
    result = run("scripts/validate_project_intake.py", "--intake", str(path))
    assert result.returncode != 0
    assert "target_workflow must match a v0.2 supported target workflow id" in (result.stdout + result.stderr)

    for target_workflow in ["bugfix-regression-capture", "new-project-spec-first", "review-only-fusion"]:
        intake["target_workflow"] = target_workflow
        path.write_text(yaml.safe_dump(intake, sort_keys=False), encoding="utf-8")
        result = run("scripts/validate_project_intake.py", "--intake", str(path))
        assert result.returncode != 0
        assert "target_workflow must match a v0.2 supported target workflow id" in (
            result.stdout + result.stderr
        )

    intake["target_workflow"] = "big-feature-contract-first"
    path.write_text(yaml.safe_dump(intake, sort_keys=False), encoding="utf-8")
    result = run("scripts/validate_project_intake.py", "--intake", str(path))
    assert result.returncode == 0, result.stdout + result.stderr


def test_project_intake_schema_restricts_prepare_workflow_target() -> None:
    import copy
    import json

    import jsonschema
    import yaml

    schema = json.loads((ROOT / "schemas/project-intake.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    intake = yaml.safe_load((ROOT / "examples/project-initialization/project-intake.yaml").read_text(encoding="utf-8"))
    intake["intent_mode"] = "prepare-workflow"

    valid = copy.deepcopy(intake)
    valid["target_workflow"] = "big-feature-contract-first"
    validator.validate(valid)

    for target_workflow in [
        "bugfix-regression-capture",
        "new-project-spec-first",
        "review-only-fusion",
        "safe-refactor",
        "project-initialization",
        "not-a-real-workflow",
    ]:
        invalid = copy.deepcopy(intake)
        invalid["target_workflow"] = target_workflow
        assert list(validator.iter_errors(invalid))


def test_project_inventory_validation_passes() -> None:
    result = run("scripts/validate_project_inventory.py", "--inventory", "examples/project-initialization/project-inventory.json")
    assert result.returncode == 0, result.stdout + result.stderr


def test_project_assessment_schema_requires_triad_synthesis() -> None:
    import copy
    import json

    import jsonschema

    schema = json.loads((ROOT / "schemas/project-assessment.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    for rel in [
        "templates/project-assessment.json",
        "templates/project-assessment.role.json",
        "examples/project-initialization/project-assessment.json",
        "examples/project-initialization/project-assessment.architecture.json",
        "examples/project-initialization/project-assessment.verification.json",
        "examples/project-initialization/project-assessment.adversarial.json",
    ]:
        data = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        validator.validate(data)

    synthesis = json.loads((ROOT / "templates/project-assessment.json").read_text(encoding="utf-8"))
    missing_reports = copy.deepcopy(synthesis)
    missing_reports.pop("role_reports")
    assert list(validator.iter_errors(missing_reports))

    missing_adversarial = copy.deepcopy(synthesis)
    missing_adversarial["role_reports"] = [
        report for report in missing_adversarial["role_reports"] if report["role"] != "adversarial"
    ]
    assert list(validator.iter_errors(missing_adversarial))

    markdown_artifact = copy.deepcopy(synthesis)
    markdown_artifact["role_reports"][0]["artifact"] = "project-assessment.architecture.md"
    assert list(validator.iter_errors(markdown_artifact))

    invalid_role = json.loads((ROOT / "templates/project-assessment.role.json").read_text(encoding="utf-8"))
    invalid_role["role"] = "generalist"
    assert list(validator.iter_errors(invalid_role))

    missing_readiness = json.loads((ROOT / "templates/project-assessment.role.json").read_text(encoding="utf-8"))
    missing_readiness.pop("readiness")
    assert list(validator.iter_errors(missing_readiness))

    invalid_readiness = json.loads((ROOT / "templates/project-assessment.role.json").read_text(encoding="utf-8"))
    invalid_readiness["readiness"] = "looks-good"
    assert list(validator.iter_errors(invalid_readiness))

    missing_validation = copy.deepcopy(synthesis)
    missing_validation.pop("role_report_validation")
    assert list(validator.iter_errors(missing_validation))

    invalid_validation = copy.deepcopy(synthesis)
    invalid_validation["role_report_validation"]["all_role_reports_schema_valid"] = False
    assert list(validator.iter_errors(invalid_validation))

    authoritative_finding = copy.deepcopy(synthesis)
    authoritative_finding["candidate_findings"] = [
        {
            "id": "AF-INIT-BAD",
            "severity": "P1",
            "finding": "This incorrectly claims main-agent validation.",
            "status": "accepted-relevant",
        }
    ]
    assert list(validator.iter_errors(authoritative_finding))

    prompt_role = json.loads((ROOT / "templates/project-assessment.role.json").read_text(encoding="utf-8"))
    prompt_role["role"] = "prompt_engineering"
    validator.validate(prompt_role)


def test_project_assessment_synthesis_validates_referenced_role_reports(tmp_path) -> None:
    import json
    import shutil
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    run_dir = tmp_path / "project-initialization"
    shutil.copytree(ROOT / "examples" / "project-initialization", run_dir)
    synthesis_path = run_dir / "project-assessment.json"

    assert validate_repo.validate_project_assessment_synthesis_artifact(ROOT, synthesis_path) == []

    missing_role_dir = tmp_path / "missing-role"
    shutil.copytree(run_dir, missing_role_dir)
    (missing_role_dir / "project-assessment.architecture.json").unlink()
    errors = validate_repo.validate_project_assessment_synthesis_artifact(
        ROOT,
        missing_role_dir / "project-assessment.json",
    )
    assert "missing referenced role report artifact" in "\n".join(errors)

    markdown_ref_dir = tmp_path / "markdown-ref"
    shutil.copytree(run_dir, markdown_ref_dir)
    synthesis = json.loads((markdown_ref_dir / "project-assessment.json").read_text(encoding="utf-8"))
    synthesis["role_reports"][0]["artifact"] = "project-assessment.architecture.md"
    (markdown_ref_dir / "project-assessment.json").write_text(
        json.dumps(synthesis, indent=2) + "\n",
        encoding="utf-8",
    )
    errors = validate_repo.validate_project_assessment_synthesis_artifact(
        ROOT,
        markdown_ref_dir / "project-assessment.json",
    )
    assert "must reference a .json role report artifact" in "\n".join(errors)

    invalid_role_dir = tmp_path / "invalid-role"
    shutil.copytree(run_dir, invalid_role_dir)
    role_report = json.loads((invalid_role_dir / "project-assessment.architecture.json").read_text(encoding="utf-8"))
    role_report.pop("readiness")
    (invalid_role_dir / "project-assessment.architecture.json").write_text(
        json.dumps(role_report, indent=2) + "\n",
        encoding="utf-8",
    )
    errors = validate_repo.validate_project_assessment_synthesis_artifact(
        ROOT,
        invalid_role_dir / "project-assessment.json",
    )
    assert "schema error" in "\n".join(errors)


def test_project_onboarding_assessment_skill_carries_schema_bound_contract() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    errors = validate_repo.validate_project_onboarding_assessment_skill_contract(ROOT)
    assert errors == []


def test_project_initialization_expert_assessment_requires_schema_bound_json_contract() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/project-initialization/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))

    errors = validate_repo.validate_project_initialization_expert_assessment_contract(path, workflow)
    assert not errors

    missing_contract = copy.deepcopy(workflow)
    missing_contract.pop("expert_assessment_output_contract", None)
    errors = validate_repo.validate_project_initialization_expert_assessment_contract(path, missing_contract)
    assert "expert_assessment_output_contract is required" in "\n".join(errors)

    weak_contract = copy.deepcopy(workflow)
    weak_contract["expert_assessment_output_contract"]["response_format"] = "markdown"
    errors = validate_repo.validate_project_initialization_expert_assessment_contract(path, weak_contract)
    assert "response_format must be strict_json" in "\n".join(errors)

    no_validation = copy.deepcopy(workflow)
    no_validation["expert_assessment_output_contract"]["validation_required_before_synthesis"] = False
    errors = validate_repo.validate_project_initialization_expert_assessment_contract(path, no_validation)
    assert "validation_required_before_synthesis must be true" in "\n".join(errors)

    no_prompt = copy.deepcopy(workflow)
    no_prompt["expert_assessment_output_contract"].pop("launch_prompt_requirements")
    errors = validate_repo.validate_project_initialization_expert_assessment_contract(path, no_prompt)
    assert "launch_prompt_requirements missing" in "\n".join(errors)


def test_project_operating_decisions_schema_passes() -> None:
    import json

    import jsonschema
    import yaml

    schema = json.loads(
        (ROOT / "schemas/project-operating-decisions.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validator = jsonschema.Draft202012Validator(schema)
    for rel in [
        "templates/project-operating-decisions.yaml",
        "examples/project-initialization/project-operating-decisions.yaml",
    ]:
        data = yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))
        validator.validate(data)
        material_triggers = set(
            data["review_cycle_policy"]["materiality_classification"]["material_if_changes"]
        )
        assert {
            "task_contract_or_scope",
            "selected_risk_surfaces_or_failure_path_matrix",
            "behavior_bindings",
            "affected_implementation_behavior",
            "review_packet_content",
        }.issubset(material_triggers)

    invalid_cycles = yaml.safe_load((ROOT / "templates/project-operating-decisions.yaml").read_text(encoding="utf-8"))
    invalid_cycles["review_cycle_policy"]["max_review_cycles"] = 1
    assert list(validator.iter_errors(invalid_cycles))

    invalid_control_count = yaml.safe_load((ROOT / "templates/project-operating-decisions.yaml").read_text(encoding="utf-8"))
    invalid_control_count["review_cycle_policy"]["control_reviewer_count"] = 1
    assert list(validator.iter_errors(invalid_control_count))

    invalid_context = yaml.safe_load((ROOT / "templates/project-operating-decisions.yaml").read_text(encoding="utf-8"))
    invalid_context["review_cycle_policy"]["control_review_context_policy"]["allowed_context_sources"].append("full_repo")
    assert list(validator.iter_errors(invalid_context))

    missing_context_sources = yaml.safe_load((ROOT / "templates/project-operating-decisions.yaml").read_text(encoding="utf-8"))
    missing_context_sources["review_cycle_policy"]["control_review_context_policy"].pop("allowed_context_sources")
    assert list(validator.iter_errors(missing_context_sources))

    missing_materiality = yaml.safe_load((ROOT / "templates/project-operating-decisions.yaml").read_text(encoding="utf-8"))
    missing_materiality["review_cycle_policy"].pop("materiality_classification")
    assert list(validator.iter_errors(missing_materiality))

    missing_material_trigger = yaml.safe_load((ROOT / "templates/project-operating-decisions.yaml").read_text(encoding="utf-8"))
    missing_material_trigger["review_cycle_policy"]["materiality_classification"]["material_if_changes"].remove(
        "selected_risk_surfaces_or_failure_path_matrix"
    )
    assert list(validator.iter_errors(missing_material_trigger))

    missing_risk_surface_policy = yaml.safe_load((ROOT / "templates/project-operating-decisions.yaml").read_text(encoding="utf-8"))
    missing_risk_surface_policy.pop("risk_surface_policy")
    assert list(validator.iter_errors(missing_risk_surface_policy))

    missing_evidence_freshness = yaml.safe_load((ROOT / "templates/project-operating-decisions.yaml").read_text(encoding="utf-8"))
    missing_evidence_freshness["artifact_policy"].pop("evidence_freshness")
    assert list(validator.iter_errors(missing_evidence_freshness))

    read_write_review = yaml.safe_load((ROOT / "templates/project-operating-decisions.yaml").read_text(encoding="utf-8"))
    read_write_review["review_policy"]["read_only_by_default"] = False
    assert list(validator.iter_errors(read_write_review))

    missing_main_validation = yaml.safe_load((ROOT / "templates/project-operating-decisions.yaml").read_text(encoding="utf-8"))
    missing_main_validation["review_policy"].pop("candidate_findings_require_main_validation")
    assert list(validator.iter_errors(missing_main_validation))

    weak_main_validation = yaml.safe_load((ROOT / "templates/project-operating-decisions.yaml").read_text(encoding="utf-8"))
    weak_main_validation["review_policy"]["candidate_findings_require_main_validation"] = False
    assert list(validator.iter_errors(weak_main_validation))


def test_project_documentation_disposition_schema_passes() -> None:
    import json

    import jsonschema
    import yaml

    schema = json.loads(
        (ROOT / "schemas/project-documentation-disposition.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validator = jsonschema.Draft202012Validator(schema)
    for rel in [
        "templates/project-documentation-disposition.yaml",
        "examples/project-initialization/project-documentation-disposition.yaml",
    ]:
        data = yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))
        validator.validate(data)

    invalid_delete_without_approval = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_delete_without_approval["documents"][0]["disposition"] = (
        "rewrite-or-delete-after-approval"
    )
    invalid_delete_without_approval["documents"][0]["human_approval_required"] = False
    assert list(validator.iter_errors(invalid_delete_without_approval))

    invalid_authority_without_confidence = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_authority_without_confidence["documents"][0]["disposition"] = (
        "keep-authoritative"
    )
    invalid_authority_without_confidence["documents"][0].pop("confidence")
    assert list(validator.iter_errors(invalid_authority_without_confidence))

    invalid_prepare_not_run_level = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_prepare_not_run_level["scope"]["intent_mode"] = "prepare-workflow"
    invalid_prepare_not_run_level["scope"]["run_level_only"] = False
    assert list(validator.iter_errors(invalid_prepare_not_run_level))

    invalid_prepare_missing_target = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_prepare_missing_target["scope"]["intent_mode"] = "prepare-workflow"
    invalid_prepare_missing_target["scope"].pop("target_workflow")
    assert list(validator.iter_errors(invalid_prepare_missing_target))

    invalid_prepare_reference_target = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_prepare_reference_target["scope"]["intent_mode"] = "prepare-workflow"
    invalid_prepare_reference_target["scope"]["target_workflow"] = "review-only-fusion"
    assert list(validator.iter_errors(invalid_prepare_reference_target))

    invalid_authority_null_scope = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_authority_null_scope["documents"][0]["disposition"] = "keep-authoritative"
    invalid_authority_null_scope["documents"][0]["authority_scope"] = None
    assert list(validator.iter_errors(invalid_authority_null_scope))

    invalid_authority_blank_scope = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_authority_blank_scope["documents"][0]["disposition"] = "keep-authoritative"
    invalid_authority_blank_scope["documents"][0]["authority_scope"] = ""
    assert list(validator.iter_errors(invalid_authority_blank_scope))

    invalid_stale_without_approval = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_stale_without_approval["documents"][0]["disposition"] = (
        "mark-stale-or-superseded"
    )
    invalid_stale_without_approval["documents"][0]["human_approval_required"] = False
    assert list(validator.iter_errors(invalid_stale_without_approval))

    invalid_prepare_persistent_targets = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_prepare_persistent_targets["scope"]["intent_mode"] = "prepare-workflow"
    invalid_prepare_persistent_targets["scope"]["run_level_only"] = True
    invalid_prepare_persistent_targets["documents"][0]["normalized_targets"] = [
        "project-operating-decisions.yaml",
        "active-instruction-map.yaml",
    ]
    assert list(validator.iter_errors(invalid_prepare_persistent_targets))

    invalid_prepare_canonical_persistent_targets = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_prepare_canonical_persistent_targets["scope"]["intent_mode"] = "prepare-workflow"
    invalid_prepare_canonical_persistent_targets["scope"]["run_level_only"] = True
    invalid_prepare_canonical_persistent_targets["documents"][0]["normalized_targets"] = [
        ".agentsflow/project-operating-decisions.yaml",
        ".agentsflow/active-instruction-map.yaml",
    ]
    assert list(validator.iter_errors(invalid_prepare_canonical_persistent_targets))

    empty_documents = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    empty_documents["documents"] = []
    empty_documents["no_material_documents_rationale"] = (
        "No material project documentation or Markdown implementation history was observed."
    )
    validator.validate(empty_documents)

    empty_documents_without_rationale = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    empty_documents_without_rationale["documents"] = []
    empty_documents_without_rationale.pop("no_material_documents_rationale", None)
    assert list(validator.iter_errors(empty_documents_without_rationale))

    missing_documentation_adoption = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    missing_documentation_adoption.pop("documentation_legacy_adoption")
    assert list(validator.iter_errors(missing_documentation_adoption))

    invalid_agent_selected_documentation_adoption = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_agent_selected_documentation_adoption["documentation_legacy_adoption"][
        "agent_may_select_without_human"
    ] = True
    assert list(validator.iter_errors(invalid_agent_selected_documentation_adoption))

    invalid_unconfirmed_documentation_adoption = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_unconfirmed_documentation_adoption["artifact_role"] = "run_artifact"
    invalid_unconfirmed_documentation_adoption["documentation_legacy_adoption"][
        "human_confirmation"
    ]["status"] = "pending"
    assert list(validator.iter_errors(invalid_unconfirmed_documentation_adoption))

    invalid_agent_default_confirmation_source = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_agent_default_confirmation_source["documentation_legacy_adoption"][
        "human_confirmation"
    ]["source"] = "agent-default"
    assert list(validator.iter_errors(invalid_agent_default_confirmation_source))

    missing_decision_record = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    missing_decision_record["documentation_legacy_adoption"].pop("decision_record")
    assert list(validator.iter_errors(missing_decision_record))

    invalid_decision_record = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_decision_record["documentation_legacy_adoption"][
        "decision_record"
    ] = "agent-default"
    assert list(validator.iter_errors(invalid_decision_record))

    invalid_light_as_mode = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_light_as_mode["documentation_legacy_adoption"]["mode"] = "light-extraction"
    assert list(validator.iter_errors(invalid_light_as_mode))

    missing_extraction_depth = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    missing_extraction_depth["documentation_legacy_adoption"].pop("extraction_depth")
    assert list(validator.iter_errors(missing_extraction_depth))

    invalid_prepare_project_level_extraction = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_prepare_project_level_extraction["scope"]["intent_mode"] = "prepare-workflow"
    invalid_prepare_project_level_extraction["documentation_legacy_adoption"][
        "persistence_scope"
    ] = "project-level"
    assert list(validator.iter_errors(invalid_prepare_project_level_extraction))

    invalid_prepare_extraction_artifact = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    invalid_prepare_extraction_artifact["scope"]["intent_mode"] = "prepare-workflow"
    invalid_prepare_extraction_artifact["documentation_legacy_adoption"][
        "extraction_artifact"
    ] = "custom-extraction.md"
    assert list(validator.iter_errors(invalid_prepare_extraction_artifact))

    light_prepare_without_risk_acceptance = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    light_prepare_without_risk_acceptance["scope"]["intent_mode"] = "prepare-workflow"
    light_prepare_without_risk_acceptance["documentation_legacy_adoption"][
        "extraction_depth"
    ] = "light"
    validator.validate(light_prepare_without_risk_acceptance)

    light_prepare_with_risk_acceptance = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    light_prepare_with_risk_acceptance["scope"]["intent_mode"] = "prepare-workflow"
    light_prepare_with_risk_acceptance["documentation_legacy_adoption"][
        "extraction_depth"
    ] = "light"
    light_prepare_with_risk_acceptance["documentation_legacy_adoption"][
        "implementation_risk_acceptance"
    ] = {
        "required": True,
        "status": "accepted",
        "source": "human-dialogue",
        "decision_record": "human-decisions.yaml#documentation-extraction-light-risk",
    }
    validator.validate(light_prepare_with_risk_acceptance)

    knowledge_extraction = yaml.safe_load(
        (ROOT / "templates/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    knowledge_extraction["documentation_legacy_adoption"]["mode"] = "knowledge-extraction"
    knowledge_extraction["documentation_legacy_adoption"]["extraction_depth"] = "standard"
    validator.validate(knowledge_extraction)


def test_project_documentation_disposition_resolves_human_decision_record(tmp_path: Path) -> None:
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    disposition = yaml.safe_load(
        (ROOT / "examples/project-initialization/project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    decisions = yaml.safe_load(
        (ROOT / "examples/project-initialization/human-decisions.yaml").read_text(
            encoding="utf-8"
        )
    )
    questions = yaml.safe_load(
        (ROOT / "examples/project-initialization/human-questions.yaml").read_text(
            encoding="utf-8"
        )
    )
    extraction_text = (
        ROOT / "examples/project-initialization/project-knowledge-extraction.md"
    ).read_text(encoding="utf-8")
    disposition_path = tmp_path / "project-documentation-disposition.yaml"
    decisions_path = tmp_path / "human-decisions.yaml"
    questions_path = tmp_path / "human-questions.yaml"
    extraction_path = tmp_path / "project-knowledge-extraction.md"

    def write_artifacts(
        decisions_data: dict | None = None,
        questions_data: dict | None = None,
        disposition_data: dict | None = None,
    ) -> None:
        disposition_path.write_text(
            yaml.safe_dump(disposition_data or disposition), encoding="utf-8"
        )
        decisions_path.write_text(
            yaml.safe_dump(decisions_data or decisions), encoding="utf-8"
        )
        questions_path.write_text(
            yaml.safe_dump(questions_data or questions), encoding="utf-8"
        )
        extraction_path.write_text(extraction_text, encoding="utf-8")

    write_artifacts()
    assert not validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )

    copied_template_disposition = yaml.safe_load(yaml.safe_dump(disposition))
    copied_template_disposition["artifact_role"] = "template"
    write_artifacts(disposition_data=copied_template_disposition)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "artifact_role template is reserved" in "\n".join(errors)

    questions_path.unlink()
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "missing human-questions.yaml" in "\n".join(errors)

    missing_question = yaml.safe_load(yaml.safe_dump(questions))
    missing_question["questions"] = [
        question
        for question in missing_question["questions"]
        if question["decision_id"] != "documentation-legacy-adoption"
    ]
    write_artifacts(questions_data=missing_question)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "matching human question not found" in "\n".join(errors)

    defaulted_question = yaml.safe_load(yaml.safe_dump(questions))
    defaulted_question["questions"][0]["default"]["allowed"] = True
    write_artifacts(questions_data=defaulted_question)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "question must not allow a default" in "\n".join(errors)

    default_id_question = yaml.safe_load(yaml.safe_dump(questions))
    default_id_question["questions"][0]["default"]["id"] = "knowledge-extraction"
    write_artifacts(questions_data=default_id_question)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "question must not declare a default id" in "\n".join(errors)

    open_question = yaml.safe_load(yaml.safe_dump(questions))
    open_question["questions"][0]["status"] = "open"
    write_artifacts(questions_data=open_question)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "question must be answered" in "\n".join(errors)

    incomplete_mode_options = yaml.safe_load(yaml.safe_dump(questions))
    incomplete_mode_options["questions"][0]["options"] = [
        option
        for option in incomplete_mode_options["questions"][0]["options"]
        if option["id"] != "archive-delete"
    ]
    write_artifacts(questions_data=incomplete_mode_options)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "question options missing modes: archive-delete" in "\n".join(errors)

    extra_mode_option = yaml.safe_load(yaml.safe_dump(questions))
    extra_mode_option["questions"][0]["options"].append(
        {
            "id": "unresolved",
            "label": "Leave unresolved",
            "impact": "Blocks the run.",
        }
    )
    write_artifacts(questions_data=extra_mode_option)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "question options must not include non-mode ids: unresolved" in "\n".join(errors)

    missing_depth_option = yaml.safe_load(yaml.safe_dump(questions))
    missing_depth_option["questions"][0]["extraction_depth_options"] = [
        option
        for option in missing_depth_option["questions"][0]["extraction_depth_options"]
        if option["id"] != "deep"
    ]
    write_artifacts(questions_data=missing_depth_option)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "question extraction_depth_options missing: deep" in "\n".join(errors)

    extra_depth_option = yaml.safe_load(yaml.safe_dump(questions))
    extra_depth_option["questions"][0]["extraction_depth_options"].append(
        {
            "id": "full",
            "label": "Full",
            "impact": "Unsupported extraction depth.",
        }
    )
    write_artifacts(questions_data=extra_depth_option)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "question extraction_depth_options must not include unsupported ids: full" in "\n".join(errors)

    missing_scope_option = yaml.safe_load(yaml.safe_dump(questions))
    missing_scope_option["questions"][0]["persistence_scope_options"] = [
        option
        for option in missing_scope_option["questions"][0]["persistence_scope_options"]
        if option["id"] != "project-level"
    ]
    write_artifacts(questions_data=missing_scope_option)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "question persistence_scope_options missing: project-level" in "\n".join(errors)

    extra_scope_option = yaml.safe_load(yaml.safe_dump(questions))
    extra_scope_option["questions"][0]["persistence_scope_options"].append(
        {
            "id": "global",
            "label": "Global",
            "impact": "Unsupported persistence scope.",
        }
    )
    write_artifacts(questions_data=extra_scope_option)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "question persistence_scope_options must not include unsupported ids: global" in "\n".join(errors)

    mismatched_question_ref = yaml.safe_load(yaml.safe_dump(decisions))
    mismatched_question_ref["decisions"][0]["question_ref"] = "documentation.legacy_adoption"
    write_artifacts(decisions_data=mismatched_question_ref)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "decision question_ref must match question decision_id" in "\n".join(errors)

    write_artifacts()
    assert not validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )

    missing_decision = yaml.safe_load(yaml.safe_dump(decisions))
    missing_decision["decisions"] = [
        decision
        for decision in missing_decision["decisions"]
        if decision["decision_id"] != "documentation-legacy-adoption"
    ]
    write_artifacts(decisions_data=missing_decision)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "decision_record not found" in "\n".join(errors)

    defaulted_decision = yaml.safe_load(yaml.safe_dump(decisions))
    defaulted_decision["decisions"][0]["status"] = "defaulted"
    write_artifacts(decisions_data=defaulted_decision)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "decision_record must be confirmed" in "\n".join(errors)

    agent_owned_decision = yaml.safe_load(yaml.safe_dump(decisions))
    agent_owned_decision["decisions"][0]["answered_by"] = "agent"
    write_artifacts(decisions_data=agent_owned_decision)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "decision_record must be human-owned" in "\n".join(errors)

    nonblocking_decision = yaml.safe_load(yaml.safe_dump(decisions))
    nonblocking_decision["decisions"][0]["classification"] = "nonblocking-follow-up"
    write_artifacts(decisions_data=nonblocking_decision)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "decision_record must be blocking-material" in "\n".join(errors)

    mismatched_decision = yaml.safe_load(yaml.safe_dump(decisions))
    mismatched_decision["decisions"][0]["answer"]["extraction_depth"] = "deep"
    write_artifacts(decisions_data=mismatched_decision)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "answer.extraction_depth must match disposition" in "\n".join(errors)

    write_artifacts()
    extraction_path.unlink()
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "extraction_artifact missing" in "\n".join(errors)

    write_artifacts()
    extraction_path.write_text("", encoding="utf-8")
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "extraction_artifact must not be empty" in "\n".join(errors)

    wrong_extraction_artifact = yaml.safe_load(yaml.safe_dump(disposition))
    wrong_extraction_artifact["documentation_legacy_adoption"]["extraction_artifact"] = "README.md"
    (tmp_path / "README.md").write_text("Not an extraction artifact.", encoding="utf-8")
    write_artifacts(disposition_data=wrong_extraction_artifact)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "extraction_artifact must be project-knowledge-extraction.md" in "\n".join(errors)

    light_implementation_disposition = yaml.safe_load(yaml.safe_dump(disposition))
    light_implementation_disposition["scope"]["intent_mode"] = "prepare-workflow"
    light_implementation_disposition["scope"]["target_workflow"] = "big-feature-contract-first"
    light_implementation_disposition["scope"]["run_level_only"] = True
    light_implementation_disposition["documentation_legacy_adoption"][
        "extraction_depth"
    ] = "light"
    light_implementation_decisions = yaml.safe_load(yaml.safe_dump(decisions))
    light_implementation_decisions["decisions"][0]["answer"]["extraction_depth"] = "light"
    write_artifacts(
        decisions_data=light_implementation_decisions,
        disposition_data=light_implementation_disposition,
    )
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "light extraction cannot unlock implementation readiness" in "\n".join(errors)

    risk_disposition = yaml.safe_load(yaml.safe_dump(disposition))
    risk_disposition["scope"]["intent_mode"] = "prepare-workflow"
    risk_disposition["scope"]["target_workflow"] = "big-feature-contract-first"
    risk_disposition["scope"]["run_level_only"] = True
    risk_disposition["documentation_legacy_adoption"]["extraction_depth"] = "light"
    risk_disposition["documentation_legacy_adoption"][
        "implementation_risk_acceptance"
    ] = {
        "required": True,
        "status": "accepted",
        "source": "human-decisions.yaml",
        "decision_record": "human-decisions.yaml#unrelated-confirmed-decision",
    }
    unrelated_risk_decisions = yaml.safe_load(yaml.safe_dump(decisions))
    unrelated_risk_decisions["decisions"][0]["answer"]["extraction_depth"] = "light"
    unrelated_risk_decisions["decisions"].append(
        {
            "decision_id": "unrelated-confirmed-decision",
            "phase_id": "target_workflow_context_decision_packet",
            "question_ref": "unrelated-confirmed-decision",
            "owning_requirement_ref": "project-initialization.documentation_disposition",
            "decision_scope": "run_scoped",
            "answer": {
                "unrelated": True,
            },
            "status": "confirmed",
            "answered_by": "project-owner",
            "classification": "blocking-material",
            "rationale": "Fixture risk decision is intentionally unrelated.",
            "affected_artifacts": [
                "human-decisions.yaml",
            ],
        }
    )
    write_artifacts(decisions_data=unrelated_risk_decisions, disposition_data=risk_disposition)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "must accept light extraction implementation risk or upgrade depth" in "\n".join(errors)

    nonblocking_risk_decisions = yaml.safe_load(yaml.safe_dump(unrelated_risk_decisions))
    nonblocking_risk_decision = next(
        decision
        for decision in nonblocking_risk_decisions["decisions"]
        if decision["decision_id"] == "unrelated-confirmed-decision"
    )
    nonblocking_risk_decision["answer"] = {
        "accepts_light_extraction_implementation_risk": True,
    }
    nonblocking_risk_decision["classification"] = "nonblocking-follow-up"
    write_artifacts(decisions_data=nonblocking_risk_decisions, disposition_data=risk_disposition)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "implementation_risk_acceptance decision_record must be blocking-material" in "\n".join(errors)

    risk_decisions = yaml.safe_load(yaml.safe_dump(decisions))
    risk_decisions["decisions"][0]["answer"]["extraction_depth"] = "light"
    risk_decisions["decisions"].append(
        {
            "decision_id": "documentation-extraction-light-risk",
            "phase_id": "target_workflow_context_decision_packet",
            "question_ref": "documentation-extraction-light-risk",
            "owning_requirement_ref": "project-initialization.documentation_disposition",
            "decision_scope": "run_scoped",
            "answer": {
                "accepts_light_extraction_implementation_risk": True,
            },
            "status": "confirmed",
            "answered_by": "project-owner",
            "classification": "blocking-material",
            "rationale": "Fixture accepts light extraction risk for implementation readiness.",
            "affected_artifacts": [
                "project-documentation-disposition.yaml",
                "target-workflow-readiness-gate-report.md",
            ],
        }
    )
    risk_disposition["documentation_legacy_adoption"][
        "implementation_risk_acceptance"
    ]["decision_record"] = "human-decisions.yaml#documentation-extraction-light-risk"
    write_artifacts(decisions_data=risk_decisions, disposition_data=risk_disposition)
    assert not validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )

    invalid_schema_decisions = yaml.safe_load(yaml.safe_dump(risk_decisions))
    invalid_schema_decision = next(
        decision
        for decision in invalid_schema_decisions["decisions"]
        if decision["decision_id"] == "documentation-extraction-light-risk"
    )
    invalid_schema_decision.pop("owning_requirement_ref")
    write_artifacts(decisions_data=invalid_schema_decisions, disposition_data=risk_disposition)
    errors = validate_repo.validate_project_documentation_disposition_artifact(
        ROOT, disposition_path
    )
    assert "schema error" in "\n".join(errors)


def test_project_initialization_example_claimed_files_exist() -> None:
    import json
    import yaml

    example_root = ROOT / "examples/project-initialization"
    raw_scan = json.loads((example_root / "project-raw-scan.json").read_text(encoding="utf-8"))
    for rel in raw_scan["observed_files"]:
        assert (example_root / rel).exists(), rel

    disposition = yaml.safe_load(
        (example_root / "project-documentation-disposition.yaml").read_text(
            encoding="utf-8"
        )
    )
    for document in disposition["documents"]:
        assert (example_root / document["path"]).exists(), document["path"]
        for evidence in document["evidence"]:
            assert (example_root / evidence).exists(), evidence

    decision_record = disposition["documentation_legacy_adoption"]["decision_record"]
    decision_file, decision_id = decision_record.split("#", 1)
    human_decisions = yaml.safe_load(
        (example_root / decision_file).read_text(encoding="utf-8")
    )
    human_questions = yaml.safe_load(
        (example_root / "human-questions.yaml").read_text(encoding="utf-8")
    )
    questions_by_id = {
        question["decision_id"]: question
        for question in human_questions["questions"]
    }
    decisions_by_id = {
        decision["decision_id"]: decision
        for decision in human_decisions["decisions"]
    }
    documentation_question = questions_by_id[decision_id]
    assert documentation_question["phase_id"] == "documentation_disposition_decision"
    assert documentation_question["classification"] == "blocking-material"
    assert documentation_question["default"]["allowed"] is False
    assert "id" not in documentation_question["default"]
    documentation_decision = decisions_by_id[decision_id]
    assert documentation_decision["phase_id"] == "documentation_disposition_decision"
    assert documentation_decision["status"] == "confirmed"
    assert documentation_decision["answered_by"] in {"human", "project-owner"}
    assert documentation_decision["answer"]["mode"] == disposition[
        "documentation_legacy_adoption"
    ]["mode"]
    assert documentation_decision["answer"]["extraction_depth"] == disposition[
        "documentation_legacy_adoption"
    ]["extraction_depth"]


def test_human_interaction_artifact_schemas_pass() -> None:
    import json

    import jsonschema
    import yaml

    cases = [
        (
            "schemas/human-questions.schema.json",
            [
                "templates/human-questions.yaml",
                "examples/project-initialization/human-questions.yaml",
            ],
        ),
        (
            "schemas/human-decisions.schema.json",
            [
                "templates/human-decisions.yaml",
                "examples/project-initialization/human-decisions.yaml",
            ],
        ),
    ]
    for schema_rel, artifact_rels in cases:
        schema = json.loads((ROOT / schema_rel).read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        for rel in artifact_rels:
            data = yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))
            validator.validate(data)


def test_human_questions_require_classification_and_blocking_questions_cannot_auto_default() -> None:
    import copy
    import json

    import jsonschema
    import yaml

    schema = json.loads((ROOT / "schemas/human-questions.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    data = yaml.safe_load((ROOT / "templates/human-questions.yaml").read_text(encoding="utf-8"))

    missing_classification = copy.deepcopy(data)
    missing_classification["questions"][0].pop("classification")
    assert list(validator.iter_errors(missing_classification))

    defaulted_blocking = copy.deepcopy(data)
    defaulted_blocking["questions"][0]["default"]["allowed"] = True
    errors = list(validator.iter_errors(defaulted_blocking))
    assert errors

    default_status_blocking = copy.deepcopy(data)
    default_status_blocking["questions"][0]["status"] = "defaulted"
    assert list(validator.iter_errors(default_status_blocking))

    missing_allowed = copy.deepcopy(data)
    missing_allowed["questions"][0]["default"].pop("allowed")
    assert list(validator.iter_errors(missing_allowed))

    missing_default = copy.deepcopy(data)
    missing_default["questions"][0].pop("default")
    assert list(validator.iter_errors(missing_default))


def test_human_decisions_reject_defaulted_blocking_material() -> None:
    import copy
    import json

    import jsonschema
    import yaml

    schema = json.loads((ROOT / "schemas/human-decisions.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    data = yaml.safe_load((ROOT / "templates/human-decisions.yaml").read_text(encoding="utf-8"))

    defaulted_blocking = copy.deepcopy(data)
    defaulted_blocking["decisions"][0]["status"] = "defaulted"
    assert list(validator.iter_errors(defaulted_blocking))

    deferred_blocking = copy.deepcopy(data)
    deferred_blocking["decisions"][0]["status"] = "explicitly_deferred_with_constraints"
    deferred_blocking["decisions"][0]["deferral_constraints"] = {
        "constraints": ["The deferred decision is out of scope for this run."],
    }
    assert not list(validator.iter_errors(deferred_blocking))

    missing_constraints = copy.deepcopy(deferred_blocking)
    missing_constraints["decisions"][0].pop("deferral_constraints")
    assert list(validator.iter_errors(missing_constraints))

    empty_constraints = copy.deepcopy(deferred_blocking)
    empty_constraints["decisions"][0]["deferral_constraints"]["constraints"] = []
    assert list(validator.iter_errors(empty_constraints))

    blank_constraints = copy.deepcopy(deferred_blocking)
    blank_constraints["decisions"][0]["deferral_constraints"]["constraints"] = ["   "]
    assert list(validator.iter_errors(blank_constraints))


def test_target_workflow_human_decisions_require_open_decision_fields() -> None:
    import copy
    import json

    import jsonschema
    import yaml

    schema = json.loads((ROOT / "schemas/human-decisions.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    data = yaml.safe_load((ROOT / "templates/human-decisions.yaml").read_text(encoding="utf-8"))
    target_decision = data["decisions"][1]
    assert target_decision["phase_id"] == "target_workflow_context_decision_packet"
    assert not list(validator.iter_errors(data))

    for field in ["owning_requirement_ref", "decision_scope", "rationale"]:
        missing = copy.deepcopy(data)
        missing["decisions"][1].pop(field)
        assert list(validator.iter_errors(missing))

    for field in ["owning_requirement_ref", "rationale", "residual_risk"]:
        blank = copy.deepcopy(data)
        blank["decisions"][1][field] = "   "
        assert list(validator.iter_errors(blank))

    agent_owned = copy.deepcopy(data)
    agent_owned["decisions"][1]["answered_by"] = "agent"
    assert list(validator.iter_errors(agent_owned))

    invalid_scope = copy.deepcopy(data)
    invalid_scope["decisions"][1]["decision_scope"] = "global_policy"
    assert list(validator.iter_errors(invalid_scope))

    missing_residual_risk = copy.deepcopy(data)
    missing_residual_risk["decisions"][1].pop("residual_risk")
    assert list(validator.iter_errors(missing_residual_risk))


def test_review_packet_schema_allows_plus_focused_baseline_without_focus_zone() -> None:
    import copy
    import json

    import jsonschema

    schema = json.loads((ROOT / "schemas/review-packet.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    packet = json.loads(
        (
            ROOT
            / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-packets/generalist-a.json"
        ).read_text(encoding="utf-8")
    )
    packet["review_profile"] = "homogeneous-plus-focused"
    packet["composition"] = "homogeneous-plus-focused"
    packet["risk_surface_profile"]["selected_risk_surfaces"] = ["authority_boundary"]
    packet["risk_surface_profile"]["review_topology_source"] = "risk_surface_profile"
    packet["risk_surface_profile"]["escalation_reason"] = "authority boundary selected"
    packet["failure_path_matrix"]["rows"] = [
        {
            "id": "FPM-001",
            "risk_surface": "authority_boundary",
            "path_class": "direct_bypass_attempt",
            "evidence_binding": "AF-BHV-001",
            "status": "covered",
        }
    ]
    validator.validate(packet)

    missing_escalation_surface = copy.deepcopy(packet)
    missing_escalation_surface["risk_surface_profile"]["selected_risk_surfaces"] = []
    assert list(validator.iter_errors(missing_escalation_surface))

    blank_escalation_surface = copy.deepcopy(packet)
    blank_escalation_surface["risk_surface_profile"]["selected_risk_surfaces"] = [""]
    assert list(validator.iter_errors(blank_escalation_surface))

    whitespace_escalation_surface = copy.deepcopy(packet)
    whitespace_escalation_surface["risk_surface_profile"]["selected_risk_surfaces"] = ["   "]
    assert list(validator.iter_errors(whitespace_escalation_surface))

    empty_escalation_fpm = copy.deepcopy(packet)
    empty_escalation_fpm["failure_path_matrix"]["rows"] = []
    assert list(validator.iter_errors(empty_escalation_fpm))

    focused = copy.deepcopy(packet)
    focused["reviewer_instance_id"] = "adversarial"
    focused["reviewer_role"] = "adversarial"
    assert list(validator.iter_errors(focused))

    focused["focus_zone"] = {"primary_focus": ["false completion", "bypasses"]}
    validator.validate(focused)

    empty_focus = copy.deepcopy(focused)
    empty_focus["focus_zone"]["primary_focus"] = []
    assert list(validator.iter_errors(empty_focus))


def test_review_packet_schema_accepts_risk_surface_context() -> None:
    import copy
    import json

    import jsonschema

    schema = json.loads((ROOT / "schemas/review-packet.schema.json").read_text(encoding="utf-8"))
    packet = json.loads((ROOT / "templates/review-packet.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(packet)

    risk_packet = copy.deepcopy(packet)
    risk_packet["review_profile"] = "homogeneous-plus-focused"
    risk_packet["composition"] = "homogeneous-plus-focused"
    risk_packet["risk_surface_profile"]["selected_risk_surfaces"] = ["authority_boundary"]
    risk_packet["risk_surface_profile"]["review_topology_source"] = "risk_surface_profile"
    risk_packet["risk_surface_profile"]["escalation_reason"] = "authority boundary selected"
    risk_packet["failure_path_matrix"]["rows"] = [
        {
            "id": "FPM-001",
            "risk_surface": "authority_boundary",
            "path_class": "direct_bypass_attempt",
            "evidence_binding": "AF-BHV-001",
            "status": "covered",
        }
    ]
    validator.validate(risk_packet)

    invalid = copy.deepcopy(risk_packet)
    invalid["failure_path_matrix"]["rows"][0].pop("evidence_binding")
    assert list(validator.iter_errors(invalid))

    empty_fpm_path = copy.deepcopy(risk_packet)
    empty_fpm_path["failure_path_matrix"]["path"] = ""
    assert list(validator.iter_errors(empty_fpm_path))

    empty_evidence_binding = copy.deepcopy(risk_packet)
    empty_evidence_binding["failure_path_matrix"]["rows"][0]["evidence_binding"] = ""
    assert list(validator.iter_errors(empty_evidence_binding))

    whitespace_evidence_binding = copy.deepcopy(risk_packet)
    whitespace_evidence_binding["failure_path_matrix"]["rows"][0]["evidence_binding"] = "   "
    assert list(validator.iter_errors(whitespace_evidence_binding))

    whitespace_fpm_path = copy.deepcopy(risk_packet)
    whitespace_fpm_path["failure_path_matrix"]["path"] = "   "
    assert list(validator.iter_errors(whitespace_fpm_path))

    whitespace_fpm_surface = copy.deepcopy(risk_packet)
    whitespace_fpm_surface["failure_path_matrix"]["rows"][0]["risk_surface"] = "   "
    assert list(validator.iter_errors(whitespace_fpm_surface))

    empty_selected_surface = copy.deepcopy(risk_packet)
    empty_selected_surface["risk_surface_profile"]["selected_risk_surfaces"] = [""]
    assert list(validator.iter_errors(empty_selected_surface))

    whitespace_selected_surface = copy.deepcopy(risk_packet)
    whitespace_selected_surface["risk_surface_profile"]["selected_risk_surfaces"] = ["   "]
    assert list(validator.iter_errors(whitespace_selected_surface))

    selected_surface_without_fpm_rows = copy.deepcopy(risk_packet)
    selected_surface_without_fpm_rows["failure_path_matrix"]["rows"] = []
    assert list(validator.iter_errors(selected_surface_without_fpm_rows))

    missing_verification_gate_report = copy.deepcopy(risk_packet)
    missing_verification_gate_report.pop("verification_gate_report")
    assert list(validator.iter_errors(missing_verification_gate_report))

    missing_changed_files = copy.deepcopy(risk_packet)
    missing_changed_files.pop("changed_files")
    assert list(validator.iter_errors(missing_changed_files))

    blank_changed_files = copy.deepcopy(risk_packet)
    blank_changed_files["changed_files"] = ["   "]
    assert list(validator.iter_errors(blank_changed_files))

    empty_material_change = copy.deepcopy(risk_packet)
    empty_material_change["evidence_freshness"]["material_change_id"] = ""
    assert list(validator.iter_errors(empty_material_change))

    empty_latest_green_gate = copy.deepcopy(risk_packet)
    empty_latest_green_gate["evidence_freshness"]["latest_green_gate"] = ""
    assert list(validator.iter_errors(empty_latest_green_gate))

    whitespace_latest_green_gate = copy.deepcopy(risk_packet)
    whitespace_latest_green_gate["evidence_freshness"]["latest_green_gate"] = "   "
    assert list(validator.iter_errors(whitespace_latest_green_gate))

    stale = copy.deepcopy(packet)
    stale["evidence_freshness"]["review_packet_generated_after_latest_green_gate"] = False
    assert list(validator.iter_errors(stale))

    deferred = copy.deepcopy(risk_packet)
    deferred["failure_path_matrix"]["rows"][0]["status"] = "deferred"
    deferred["failure_path_matrix"]["rows"][0]["deferral"] = {
        "residual_risk": "covered by follow-up gate",
        "approved_by": "project_owner",
        "approval_artifact": "human-decisions.yaml#HD-001",
        "constraints": ["must not affect authority boundary behavior"],
    }
    validator.validate(deferred)

    missing_deferral = copy.deepcopy(deferred)
    missing_deferral["failure_path_matrix"]["rows"][0].pop("deferral")
    assert list(validator.iter_errors(missing_deferral))

    whitespace_deferral = copy.deepcopy(deferred)
    whitespace_deferral["failure_path_matrix"]["rows"][0]["deferral"]["approval_artifact"] = "   "
    assert list(validator.iter_errors(whitespace_deferral))


def test_collision_control_review_packet_requires_non_null_batch() -> None:
    import copy
    import json

    import jsonschema

    schema = json.loads((ROOT / "schemas/review-packet.schema.json").read_text(encoding="utf-8"))
    packet = json.loads((ROOT / "templates/review-packet.json").read_text(encoding="utf-8"))
    packet["review_profile"] = "collision-control"
    packet["composition"] = "control"
    packet["collision_control"] = None

    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(packet))
    assert errors
    assert "not of type 'object'" in "\n".join(error.message for error in errors)

    valid = copy.deepcopy(packet)
    valid["collision_control"] = {
        "trigger": "rejected_or_downgraded_blocker_collision",
        "collision_batch_id": "collision-001",
        "control_reviewer_count": 2,
        "disputed_findings": [
            {
                "finding_id": "F-001",
                "original_severity": "P1",
                "source_reviewer_report": "reviewer-report.generalist-a.md",
                "orchestrator_action": "rejected",
            }
        ],
        "orchestrator_collision_reason": "Contradicted by contract evidence.",
        "evidence_references_checked": ["task.contract.md"],
    }
    jsonschema.Draft202012Validator(schema).validate(valid)

    invalid_count = copy.deepcopy(valid)
    invalid_count["collision_control"]["control_reviewer_count"] = 1
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(invalid_count))

    empty_batch = copy.deepcopy(valid)
    empty_batch["collision_control"]["collision_batch_id"] = ""
    empty_batch["collision_control"]["disputed_findings"][0]["finding_id"] = ""
    empty_batch["collision_control"]["disputed_findings"][0]["source_reviewer_report"] = ""
    empty_batch["collision_control"]["orchestrator_collision_reason"] = ""
    empty_batch["collision_control"]["evidence_references_checked"] = [""]
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(empty_batch))


def test_primary_e2e_markdown_reviewer_summaries_are_sidecars_not_gate_reports() -> None:
    import yaml

    run_path = ROOT / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/run.yaml"
    run_data = yaml.safe_load(run_path.read_text(encoding="utf-8"))
    review_evidence = run_data["phase_evidence"]["review"]

    assert all(path.endswith(".json") for path in review_evidence["reviewer_reports"])
    assert all(path.endswith(".md") for path in review_evidence["reviewer_report_summaries"])


def test_reviewer_prompts_require_schema_json_without_losing_substance() -> None:
    import json
    import sys

    import yaml

    base_prompt = (ROOT / "templates/review-prompts/base.md").read_text(encoding="utf-8")
    assert "Return exactly one schema-valid reviewer-report JSON object" in base_prompt
    assert '"reviewer_instance_id": "<reviewer_instance_id>"' in base_prompt
    assert "self_declared_limitations" in base_prompt

    sys.path.insert(0, str(ROOT / "scripts" / "reviewers"))
    from prompt_rendering import render_review_prompt  # noqa: PLC0415

    packet = json.loads(
        (
            ROOT
            / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-packets/generalist-a.json"
        ).read_text(encoding="utf-8")
    )
    role_contract = yaml.safe_load((ROOT / "profiles/reviewer_roles/generalist.yaml").read_text(encoding="utf-8"))
    rendered = render_review_prompt(packet, role_contract)

    assert "Return exactly one schema-valid reviewer-report JSON object" in rendered
    assert "If there are no findings, return an empty findings array" in rendered
    assert '"reviewer":{"id":"<reviewer_instance_id>"' in rendered


def test_evidence_probe_report_schema_rejects_decision_fields_and_unbound_sources() -> None:
    import copy
    import json
    import sys

    import jsonschema

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    schema = json.loads((ROOT / "schemas/evidence-probe-report.schema.json").read_text(encoding="utf-8"))
    report = json.loads((ROOT / "templates/evidence-probe-report.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(report)

    root_decision = copy.deepcopy(report)
    root_decision["finding_decision"] = "accepted"
    assert list(validator.iter_errors(root_decision))

    nested_decision = copy.deepcopy(report)
    nested_decision["evidence_collected"][0]["finding_decision"] = "accepted"
    assert list(validator.iter_errors(nested_decision))

    missing_context_sources = copy.deepcopy(report)
    missing_context_sources["context_policy"].pop("allowed_context_sources")
    assert list(validator.iter_errors(missing_context_sources))

    human_source = copy.deepcopy(report)
    human_source["allowed_instruments"][0]["source"] = "human_decision"
    assert list(validator.iter_errors(human_source))

    empty_allowed_id = copy.deepcopy(report)
    empty_allowed_id["allowed_instruments"][0]["id"] = ""
    assert list(validator.iter_errors(empty_allowed_id))

    empty_command_id = copy.deepcopy(report)
    empty_command_id["commands_run"][0]["instrument_id"] = ""
    assert list(validator.iter_errors(empty_command_id))

    undeclared_command = copy.deepcopy(report)
    undeclared_command["commands_run"][0]["instrument_id"] = "not-declared"
    temp_report = ROOT / ".pytest_cache/evidence-probe-report.invalid.json"
    temp_report.parent.mkdir(parents=True, exist_ok=True)
    temp_report.write_text(json.dumps(undeclared_command), encoding="utf-8")
    try:
        errors = validate_repo.validate_evidence_probe_report_artifact(ROOT, temp_report)
    finally:
        temp_report.unlink(missing_ok=True)
    assert errors
    assert "not declared in allowed_instruments" in "\n".join(errors)

def test_review_packet_rejects_stale_latest_green_gate_reference(tmp_path) -> None:
    import json
    import shutil
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "agentsflow-stale-green"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"),
    )
    packet_path = (
        root
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-packets/generalist-a.json"
    )
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["evidence_freshness"]["latest_green_gate"] = "missing-green-report.md"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    errors = validate_repo.validate_review_packet_artifact(
        root,
        packet_path,
        True,
        require_green_verification_gate=True,
    )
    joined = "\n".join(errors)
    assert "evidence_freshness.latest_green_gate must match verification_gate_report.path" in joined
    assert "evidence_freshness.latest_green_gate must reference a verification gate report artifact" in joined


def _copy_example_review_packet(tmp_path, name: str):
    import shutil

    root = tmp_path / name
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"),
    )
    packet_path = (
        root
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-packets/generalist-a.json"
    )
    return root, packet_path


def _validate_required_green_review_packet(root: Path, packet_path: Path) -> list[str]:
    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    return validate_repo.validate_review_packet_artifact(
        root,
        packet_path,
        True,
        require_green_verification_gate=True,
    )


def _assert_required_green_review_packet_rejected(
    tmp_path,
    name: str,
    report_body: str | dict,
    report_name: str = "verification-gate-report.md",
    expected_error: str = "verification_gate_report.path must reference a verification gate report artifact",
) -> None:
    root, packet_path = _copy_example_review_packet(tmp_path, name)
    report_path = packet_path.parent.parent / report_name
    if isinstance(report_body, dict):
        report_path.write_text(json.dumps(report_body, indent=2) + "\n", encoding="utf-8")
    else:
        report_path.write_text(report_body, encoding="utf-8")
    if report_name != "verification-gate-report.md":
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["verification_gate_report"]["path"] = report_name
        packet["evidence_freshness"]["latest_green_gate"] = report_name
        packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    errors = _validate_required_green_review_packet(root, packet_path)

    assert expected_error in "\n".join(errors)


def test_review_packet_rejects_green_markdown_gate_without_command_evidence(tmp_path) -> None:
    import shutil
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "agentsflow-skeletal-green"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"),
    )
    packet_path = (
        root
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-packets/generalist-a.json"
    )
    report_path = packet_path.parent.parent / "verification-gate-report.md"
    report_path.write_text("# Verification Gate Report\n\nStatus: pass\n", encoding="utf-8")

    errors = validate_repo.validate_review_packet_artifact(
        root,
        packet_path,
        True,
        require_green_verification_gate=True,
    )
    joined = "\n".join(errors)
    assert "verification_gate_report.path must reference a verification gate report artifact" in joined
    assert "evidence_freshness.latest_green_gate must reference a verification gate report artifact" in joined


def test_review_packet_rejects_green_markdown_gate_with_placeholder_table(tmp_path) -> None:
    import shutil
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "agentsflow-placeholder-green"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"),
    )
    packet_path = (
        root
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-packets/generalist-a.json"
    )
    report_path = packet_path.parent.parent / "verification-gate-report.md"
    report_path.write_text(
        "\n".join(
            [
                "# Verification Gate Report",
                "",
                "Status: pass",
                "",
                "## Structured command evidence",
                "",
                "| Command id | Exit code | Result | Output summary | Artifact paths | Raw log path |",
                "|---|---:|---|---|---|---|",
                "|  |  | pass/fail/skip/blocked |  |  | optional |",
                "",
            ]
        ),
        encoding="utf-8",
    )

    errors = validate_repo.validate_review_packet_artifact(
        root,
        packet_path,
        True,
        require_green_verification_gate=True,
    )
    assert "verification_gate_report.path must reference a verification gate report artifact" in "\n".join(errors)


def test_review_packet_rejects_green_markdown_gate_with_mixed_failed_row(tmp_path) -> None:
    _assert_required_green_review_packet_rejected(
        tmp_path,
        "agentsflow-mixed-green",
        "\n".join(
            [
                "# Verification Gate Report",
                "",
                "Status: pass",
                "",
                "## Structured command evidence",
                "",
                "| Command id | Exit code | Result | Output summary | Artifact paths | Raw log path |",
                "|---|---:|---|---|---|---|",
                "| pytest | 1 | fail | tests failed | logs/pytest.log | logs/pytest.log |",
                "| ruff | 0 | pass | lint passed | logs/ruff.log | logs/ruff.log |",
                "",
            ]
        ),
    )


def test_review_packet_rejects_green_markdown_gate_with_named_row_without_evidence(tmp_path) -> None:
    _assert_required_green_review_packet_rejected(
        tmp_path,
        "agentsflow-empty-evidence-green",
        "\n".join(
            [
                "# Verification Gate Report",
                "",
                "Status: pass",
                "",
                "## Structured command evidence",
                "",
                "| Command id | Exit code | Result | Output summary | Artifact paths | Raw log path |",
                "|---|---:|---|---|---|---|",
                "| pytest | 0 | pass |  |  | optional |",
                "",
            ]
        ),
    )


def test_review_packet_rejects_green_markdown_gate_with_failed_checks_executed_row(tmp_path) -> None:
    _assert_required_green_review_packet_rejected(
        tmp_path,
        "agentsflow-markdown-failed-check-row",
        "\n".join(
            [
                "# Verification Gate Report",
                "",
                "Status: pass",
                "",
                "## Checks executed by gate",
                "",
                "| Check | Command / mechanism | Risk surface | Path class | Required | Result | Notes |",
                "|---|---|---|---|---:|---|---|",
                "| Unit tests | pytest |  |  | yes | fail | failed |",
                "",
                "## Structured command evidence",
                "",
                "| Command id | Exit code | Result | Output summary | Artifact paths | Raw log path |",
                "|---|---:|---|---|---|---|",
                "| ruff | 0 | pass | lint passed | evidence/ruff.log | evidence/ruff.log |",
                "",
            ]
        ),
    )


def test_review_packet_rejects_green_markdown_headerless_nonzero_exit_code(tmp_path) -> None:
    _assert_required_green_review_packet_rejected(
        tmp_path,
        "agentsflow-markdown-headerless-nonzero-exit",
        "\n".join(
            [
                "# Verification Gate Report",
                "",
                "Status: pass",
                "",
                "## Structured command evidence",
                "",
                "| pytest | 1 | pass | tests passed | evidence/pytest.log | evidence/pytest.log |",
                "",
            ]
        ),
    )


def test_review_packet_rejects_green_markdown_headerless_result_before_exit_code(tmp_path) -> None:
    _assert_required_green_review_packet_rejected(
        tmp_path,
        "agentsflow-markdown-headerless-result-before-exit",
        "\n".join(
            [
                "# Verification Gate Report",
                "",
                "Status: pass",
                "",
                "## Structured command evidence",
                "",
                "| pytest | pass | 1 | tests passed | evidence/pytest.log |",
                "",
            ]
        ),
    )


def test_review_packet_rejects_green_markdown_gate_with_missing_raw_log_path(tmp_path) -> None:
    _assert_required_green_review_packet_rejected(
        tmp_path,
        "agentsflow-markdown-missing-raw-log",
        "\n".join(
            [
                "# Verification Gate Report",
                "",
                "Status: pass",
                "",
                "Material change id: 2026-06-17-add-calculator-green",
                "",
                "## Structured command evidence",
                "",
                "| Command id | Exit code | Result | Output summary | Artifact paths | Raw log path |",
                "|---|---:|---|---|---|---|",
                "| pytest | 0 | pass | tests passed |  | evidence/missing.log |",
                "",
            ]
        ),
    )


def test_review_packet_rejects_green_json_gate_with_failed_check(tmp_path) -> None:
    import json
    import shutil
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "agentsflow-json-failed-check"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"),
    )
    packet_path = (
        root
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-packets/generalist-a.json"
    )
    report_path = packet_path.parent.parent / "verification-gate-report.json"
    report_path.write_text(
        json.dumps(
            {
                "kind": "verification_gate_report",
                "result_state": "pass",
                "checks": [{"id": "pytest", "result": "fail", "exit_code": 1}],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["verification_gate_report"]["path"] = "verification-gate-report.json"
    packet["evidence_freshness"]["latest_green_gate"] = "verification-gate-report.json"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    errors = validate_repo.validate_review_packet_artifact(
        root,
        packet_path,
        True,
        require_green_verification_gate=True,
    )
    assert "verification_gate_report.path must reference a verification gate report artifact" in "\n".join(errors)


def test_review_packet_rejects_green_json_gate_with_conflicting_check_state(tmp_path) -> None:
    _assert_required_green_review_packet_rejected(
        tmp_path,
        "agentsflow-json-conflicting-check",
        {
            "kind": "verification_gate_report",
            "result_state": "pass",
            "checks": [{"id": "repo-validation", "result": "pass", "status": "fail", "exit_code": 0}],
        },
        "verification-gate-report.json",
    )


def test_review_packet_rejects_green_json_gate_with_string_nonzero_exit_code(tmp_path) -> None:
    _assert_required_green_review_packet_rejected(
        tmp_path,
        "agentsflow-json-string-exit-code",
        {
            "kind": "verification_gate_report",
            "result_state": "pass",
            "checks": [{"id": "repo-validation", "status": "pass", "exit_code": "1"}],
        },
        "verification-gate-report.json",
    )


def test_review_packet_rejects_green_json_gate_without_material_evidence(tmp_path) -> None:
    _assert_required_green_review_packet_rejected(
        tmp_path,
        "agentsflow-json-skeletal-green",
        {
            "kind": "verification_gate_report",
            "result_state": "pass",
            "checks": [{"id": "repo-validation", "status": "pass", "exit_code": 0}],
        },
        "verification-gate-report.json",
    )


def test_review_packet_rejects_green_json_gate_without_exit_code(tmp_path) -> None:
    _assert_required_green_review_packet_rejected(
        tmp_path,
        "agentsflow-json-no-exit-code",
        {
            "kind": "verification_gate_report",
            "result_state": "pass",
            "material_change_id": "2026-06-17-add-calculator-green",
            "checks": [
                {
                    "id": "repo-validation",
                    "status": "pass",
                    "output_summary": "repo validation passed",
                }
            ],
        },
        "verification-gate-report.json",
    )


def test_review_packet_rejects_green_json_gate_with_missing_raw_log_path(tmp_path) -> None:
    _assert_required_green_review_packet_rejected(
        tmp_path,
        "agentsflow-json-missing-raw-log",
        {
            "kind": "verification_gate_report",
            "result_state": "pass",
            "checks": [
                {
                    "id": "repo-validation",
                    "status": "pass",
                    "exit_code": 0,
                    "raw_log_path": "evidence/missing.log",
                }
            ],
        },
        "verification-gate-report.json",
    )


def test_review_packet_rejects_green_json_gate_with_directory_raw_log_path(tmp_path) -> None:
    root, packet_path = _copy_example_review_packet(tmp_path, "agentsflow-json-directory-raw-log")
    report_path = packet_path.parent.parent / "verification-gate-report.json"
    (packet_path.parent.parent / "evidence").mkdir(exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "kind": "verification_gate_report",
                "result_state": "pass",
                "material_change_id": "2026-06-17-add-calculator-green",
                "checks": [
                    {
                        "id": "repo-validation",
                        "status": "pass",
                        "exit_code": 0,
                        "raw_log_path": "evidence",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["verification_gate_report"]["path"] = "verification-gate-report.json"
    packet["evidence_freshness"]["latest_green_gate"] = "verification-gate-report.json"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    errors = _validate_required_green_review_packet(root, packet_path)

    assert "verification_gate_report.path must reference a verification gate report artifact" in "\n".join(errors)


def test_review_packet_rejects_green_json_gate_with_boolean_evidence(tmp_path) -> None:
    _assert_required_green_review_packet_rejected(
        tmp_path,
        "agentsflow-json-boolean-evidence",
        {
            "kind": "verification_gate_report",
            "result_state": "pass",
            "checks": [{"id": "repo-validation", "status": "pass", "exit_code": 0, "evidence": False}],
        },
        "verification-gate-report.json",
    )


def test_review_packet_rejects_green_gate_material_change_mismatch(tmp_path) -> None:
    _assert_required_green_review_packet_rejected(
        tmp_path,
        "agentsflow-json-stale-material-change",
        {
            "kind": "verification_gate_report",
            "result_state": "pass",
            "material_change_id": "older-green",
            "checks": [
                {
                    "id": "repo-validation",
                    "status": "pass",
                    "exit_code": 0,
                    "output_summary": "repo validation passed",
                }
            ],
        },
        "verification-gate-report.json",
        "evidence_freshness.latest_green_gate material_change_id must match evidence_freshness.material_change_id",
    )


def test_review_packet_rejects_stale_canonical_green_gate_without_latest_green_mirror(tmp_path) -> None:
    root, packet_path = _copy_example_review_packet(tmp_path, "agentsflow-json-stale-canonical-gate")
    report_path = packet_path.parent.parent / "verification-gate-report.json"
    report_path.write_text(
        json.dumps(
            {
                "kind": "verification_gate_report",
                "result_state": "pass",
                "material_change_id": "older-green",
                "checks": [
                    {
                        "id": "repo-validation",
                        "status": "pass",
                        "exit_code": 0,
                        "output_summary": "repo validation passed",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["verification_gate_report"]["path"] = "verification-gate-report.json"
    packet["evidence_freshness"].pop("latest_green_gate", None)
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    errors = _validate_required_green_review_packet(root, packet_path)

    assert "verification_gate_report.path material_change_id must match evidence_freshness.material_change_id" in "\n".join(errors)


def test_review_packet_accepts_green_markdown_gate_with_instruments() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    packet_path = (
        ROOT
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-packets/generalist-a.json"
    )

    assert not validate_repo.validate_review_packet_artifact(
        ROOT,
        packet_path,
        True,
        require_green_verification_gate=True,
    )


def test_review_packet_rejects_selected_surface_without_fpm_row(tmp_path) -> None:
    import json
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    packet = json.loads((ROOT / "templates/review-packet.json").read_text(encoding="utf-8"))
    packet["risk_surface_profile"]["selected_risk_surfaces"] = ["authority_boundary"]
    packet["risk_surface_profile"]["review_topology_source"] = "risk_surface_profile"
    packet["risk_surface_profile"]["escalation_reason"] = "authority boundary selected"
    packet["failure_path_matrix"]["rows"] = [
        {
            "id": "FPM-001",
            "risk_surface": "audit_persistence",
            "path_class": "denied_attempt_persisted",
            "evidence_binding": "AF-BHV-001",
            "status": "covered",
        }
    ]
    packet_path = tmp_path / "review-packet.json"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    errors = validate_repo.validate_review_packet_artifact(ROOT, packet_path, False)
    assert "failure_path_matrix.rows must cover selected risk surface(s): authority_boundary" in "\n".join(errors)


def test_review_packet_rejects_whitespace_only_risk_surface_values(tmp_path) -> None:
    import json
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    packet = json.loads((ROOT / "templates/review-packet.json").read_text(encoding="utf-8"))
    packet["risk_surface_profile"]["selected_risk_surfaces"] = ["   "]
    packet["risk_surface_profile"]["review_topology_source"] = "risk_surface_profile"
    packet["risk_surface_profile"]["escalation_reason"] = "authority boundary selected"
    packet["failure_path_matrix"]["rows"] = [
        {
            "id": "FPM-001",
            "risk_surface": "   ",
            "path_class": "denied_attempt_persisted",
            "evidence_binding": "AF-BHV-001",
            "status": "covered",
        }
    ]
    packet_path = tmp_path / "review-packet.json"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    errors = validate_repo.validate_review_packet_artifact(ROOT, packet_path, False)
    joined = "\n".join(errors)
    assert "risk_surface_profile.selected_risk_surfaces must not contain blank entries" in joined
    assert "failure_path_matrix.rows risk_surface must not be blank" in joined


def test_v02_review_control_phase_requires_top_level_review_policy() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    workflow = yaml.safe_load((ROOT / "workflows/review-only-fusion/workflow.yaml").read_text(encoding="utf-8"))
    broken = copy.deepcopy(workflow)
    broken.pop("review", None)

    errors = validate_repo.validate_v02_review_control_phase_policy(
        ROOT / "workflows/review-only-fusion/workflow.yaml",
        broken,
    )
    assert errors
    assert "top-level review policy" in errors[0]


def test_upstream_review_cycle_rejects_hardcoded_max_cycles() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/big-feature-contract-first/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(workflow)
    broken["review_cycle"]["max_review_cycles"] = 2

    errors = validate_repo.validate_upstream_review_cycle_policy(path, broken)
    assert errors
    assert "must not hardcode max_review_cycles" in "\n".join(errors)

    broken_required = copy.deepcopy(workflow)
    broken_required["review_cycle"]["max_review_cycles_required"] = True

    errors = validate_repo.validate_upstream_review_cycle_policy(path, broken_required)
    assert errors
    assert "must not require max_review_cycles" in "\n".join(errors)

    broken_source = copy.deepcopy(workflow)
    broken_source["review_cycle"]["max_review_cycles_source"] = "project_policy"

    errors = validate_repo.validate_upstream_review_cycle_policy(path, broken_source)
    assert errors
    assert "max_review_cycles_source must be project_policy_or_workflow_binding" in "\n".join(errors)


def test_v02_review_control_fusion_requires_validation_after_fusion() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/big-feature-contract-first/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(workflow)
    for phase in broken["phases"]:
        if phase.get("id") == "fusion":
            phase["runs_after"] = ["finding_validation"]
        if phase.get("id") == "finding_validation":
            phase["runs_after"] = ["review"]

    errors = validate_repo.validate_review_fusion_validation_order(path, broken)
    assert errors
    assert "finding_validation phase must run after fusion" in "\n".join(errors)


def test_bfcf_l3_keeps_fusion_required() -> None:
    import yaml

    workflow = yaml.safe_load((ROOT / "workflows/big-feature-contract-first/workflow.yaml").read_text(encoding="utf-8"))
    strictness = yaml.safe_load((ROOT / "profiles/strictness/L3.yaml").read_text(encoding="utf-8"))
    review = workflow["review"]
    phase_by_id = {phase["id"]: phase for phase in workflow["phases"] if "id" in phase}

    assert workflow["default_strictness"] == "L3"
    assert "fusion_report" in strictness["requires"]
    assert review["fusion_required"] is True
    assert "fusion_gate" in review["gates"]
    assert "fusion_gate" in workflow["concrete_gates"]
    assert "fusion" in phase_by_id["finding_validation"]["runs_after"]


def test_review_only_fusion_requires_finding_validation_phase() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/review-only-fusion/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(workflow)
    broken["phases"] = [phase for phase in broken["phases"] if phase.get("id") != "finding_validation"]

    errors = validate_repo.validate_review_fusion_validation_order(path, broken)
    assert errors
    assert "must include finding_validation phase" in "\n".join(errors)


def test_project_initialization_review_validation_order_is_covered() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/project-initialization/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(workflow)
    phases = broken["phases"]
    review_index = next(index for index, phase in enumerate(phases) if phase.get("id") == "initialization_review")
    validation_index = next(index for index, phase in enumerate(phases) if phase.get("id") == "finding_validation")
    phases[review_index], phases[validation_index] = phases[validation_index], phases[review_index]
    for phase in phases:
        if phase.get("id") == "finding_validation":
            phase["runs_after"] = []

    errors = validate_repo.validate_review_fusion_validation_order(path, broken)
    joined = "\n".join(errors)
    assert "review/validation order must be review -> finding_validation" in joined
    assert "finding_validation phase must run after review" in joined


def test_reference_workflow_without_fusion_is_not_v02_review_control_surface() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/new-project-spec-first/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(workflow)
    broken["phases"] = [phase for phase in broken["phases"] if phase.get("id") != "finding_validation"]

    errors = validate_repo.validate_review_fusion_validation_order(path, broken)
    assert not errors


def test_v02_standard_review_control_uses_report_materiality_source() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/big-feature-contract-first/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))

    errors = validate_repo.validate_v02_review_control_materiality_policy(path, workflow)
    assert not errors
    assert not validate_repo.validate_standard_review_control_glue_guardrail(path, workflow)

    review_only_path = ROOT / "workflows/review-only-fusion/workflow.yaml"
    review_only_workflow = yaml.safe_load(review_only_path.read_text(encoding="utf-8"))
    assert not validate_repo.validate_v02_review_control_materiality_policy(review_only_path, review_only_workflow)
    assert not validate_repo.validate_standard_review_control_glue_guardrail(review_only_path, review_only_workflow)

    broken = copy.deepcopy(workflow)
    broken["review_cycle"].pop("materiality_classification_source")

    errors = validate_repo.validate_v02_review_control_materiality_policy(path, broken)
    assert errors
    assert "review_cycle.materiality_classification_source missing" in "\n".join(errors)

    init_path = ROOT / "workflows/project-initialization/workflow.yaml"
    init_workflow = yaml.safe_load(init_path.read_text(encoding="utf-8"))
    assert not validate_repo.validate_v02_review_control_materiality_policy(init_path, init_workflow)

    missing_init_policy = copy.deepcopy(init_workflow)
    missing_init_policy["review_cycle"].pop("policy")
    errors = validate_repo.validate_v02_review_control_materiality_policy(init_path, missing_init_policy)
    assert "review_cycle.policy must be standard-review-control" in "\n".join(errors)

    missing_init_control_policy = copy.deepcopy(init_workflow)
    missing_init_control_policy["review"].pop("control_policy")
    errors = validate_repo.validate_v02_review_control_materiality_policy(init_path, missing_init_control_policy)
    assert "review.control_policy must be standard-review-control" in "\n".join(errors)

    missing_init_sources = copy.deepcopy(init_workflow)
    missing_init_sources["review_cycle"].pop("materiality_classification_source")
    errors = validate_repo.validate_v02_review_control_materiality_policy(init_path, missing_init_sources)
    assert "review_cycle.materiality_classification_source missing" in "\n".join(errors)

    weak_exit = copy.deepcopy(workflow)
    weak_exit["review_cycle"]["default_exit_when"] = "no_validated_blocking_findings"
    errors = validate_repo.validate_v02_review_control_materiality_policy(path, weak_exit)
    assert "review_cycle.default_exit_when must be no_validated_blockers_or_mandatory_evidence_gaps" in "\n".join(errors)


def test_standard_review_control_templates_use_mandatory_evidence_exit_token() -> None:
    expected = "no_validated_blockers_or_mandatory_evidence_gaps"
    stale = "no_validated_blocking_findings"
    paths = [
        ROOT / "templates/review-cycle-report.md",
        ROOT / "templates/finding-validation-report.md",
        ROOT / "templates/fusion-report.md",
        ROOT / "docs/review-agent-interaction-protocol.md",
        ROOT / "docs/review-fusion-model.md",
    ]

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert expected in text, path
        assert stale not in text, path


def test_standard_review_control_rejects_duplicated_local_glue_without_override_reason() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/big-feature-contract-first/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))

    duplicated_rules = copy.deepcopy(workflow)
    duplicated_rules["review_control_rules"] = {"review_agents_read_only": True}
    errors = validate_repo.validate_standard_review_control_glue_guardrail(path, duplicated_rules)
    assert "review_control_rules duplicates standard-review-control without override_reason" in "\n".join(errors)

    duplicated_cycle = copy.deepcopy(workflow)
    duplicated_cycle["review_cycle"]["rerun_review_on"] = ["accepted_blocker_fixed"]
    duplicated_cycle["review_cycle"]["blocking_default"] = {"severities": ["P0", "P1"]}
    errors = validate_repo.validate_standard_review_control_glue_guardrail(path, duplicated_cycle)
    joined = "\n".join(errors)
    assert "review_cycle duplicates standard-review-control without override_reason" in joined
    assert "blocking_default" in joined
    assert "rerun_review_on" in joined

    duplicated_review = copy.deepcopy(workflow)
    duplicated_review["review"]["blocking_policy"] = {"p0_blocks": True}
    errors = validate_repo.validate_standard_review_control_glue_guardrail(path, duplicated_review)
    assert "review duplicates standard-review-control without override_reason" in "\n".join(errors)

    duplicated_top_level = copy.deepcopy(workflow)
    duplicated_top_level["review_agent_permissions"] = {"default": {"read": True}}
    duplicated_top_level["fusion"] = {"role": "read_only_synthesis"}
    errors = validate_repo.validate_standard_review_control_glue_guardrail(path, duplicated_top_level)
    joined = "\n".join(errors)
    assert "top-level fields duplicate standard-review-control without override_reason" in joined
    assert "fusion" in joined
    assert "review_agent_permissions" in joined

    duplicated_phase = copy.deepcopy(workflow)
    duplicated_phase["phases"].append(
        {
            "id": "extra_review",
            "kind": "review",
            "actor_class": "review_agent",
            "default_permissions": {"read": True, "write": False},
            "may_modify_files": False,
            "may_run_tests": False,
            "read_only": True,
        }
    )
    duplicated_phase["phases"].append(
        {
            "id": "extra_fusion",
            "kind": "fusion",
            "may_run_gates": False,
        }
    )
    errors = validate_repo.validate_standard_review_control_glue_guardrail(path, duplicated_phase)
    joined = "\n".join(errors)
    assert "phase extra_review duplicates standard-review-control without override_reason" in joined
    assert "actor_class" in joined
    assert "default_permissions" in joined
    assert "may_modify_files" in joined
    assert "may_run_tests" in joined
    assert "read_only" in joined
    assert "phase extra_fusion duplicates standard-review-control without override_reason" in joined
    assert "may_run_gates" in joined


def test_standard_review_control_local_glue_requires_explicit_override_reason() -> None:
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/big-feature-contract-first/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    workflow["review_control_rules"] = {
        "override_reason": "Fixture exercises an intentional local policy override.",
        "review_agents_read_only": True,
    }
    workflow["review_cycle"]["override_reason"] = "Fixture exercises an intentional local cycle override."
    workflow["review_cycle"]["rerun_review_on"] = ["accepted_blocker_fixed"]
    workflow["review"]["override_reason"] = "Fixture exercises an intentional local review override."
    workflow["review"]["blocking_policy"] = {"p0_blocks": True}
    workflow["fusion"] = {
        "override_reason": "Fixture exercises an intentional local fusion override.",
        "role": "read_only_synthesis",
    }
    workflow["phases"].append(
        {
            "id": "extra_review",
            "kind": "review",
            "override_reason": "Fixture exercises an intentional local phase override.",
            "default_permissions": {"read": True, "write": False},
        }
    )

    assert not validate_repo.validate_standard_review_control_glue_guardrail(path, workflow)


def test_v02_local_review_cycle_override_requires_materiality_policy() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/big-feature-contract-first/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))

    local_override = copy.deepcopy(workflow)
    local_override["review"].pop("control_policy")
    local_override["review_cycle"].pop("policy")
    local_override["review_cycle"].pop("materiality_classification_source")

    errors = validate_repo.validate_v02_review_control_materiality_policy(path, local_override)
    assert errors
    assert "review_cycle.materiality_classification is required" in "\n".join(errors)

    broken_missing_token = copy.deepcopy(local_override)
    broken_missing_token["review_cycle"]["do_not_rerun_on"] = [
        "duplicate_consolidation",
        "irrelevant_findings_rejected_with_reason",
    ]
    broken_missing_token["review_cycle"]["materiality_classification"] = {
        "required_after_review_fixes": True,
        "material_triggers_take_precedence_over_do_not_rerun": True,
        "material_if_changes": [
            "selected_risk_surfaces_or_failure_path_matrix",
            "review_packet_content",
        ],
        "non_material_if_only": ["report_editorial_changes_only"],
    }
    errors = validate_repo.validate_v02_review_control_materiality_policy(path, broken_missing_token)
    assert "do_not_rerun_on must include nonblocking_findings_with_non_material_fixes_only" in "\n".join(errors)

    broken_missing_materiality = copy.deepcopy(local_override)
    broken_missing_materiality["review_cycle"]["do_not_rerun_on"] = [
        "nonblocking_findings_with_non_material_fixes_only"
    ]
    errors = validate_repo.validate_v02_review_control_materiality_policy(path, broken_missing_materiality)
    assert "review_cycle.materiality_classification is required" in "\n".join(errors)


def test_project_initialization_intent_mode_policy_prevents_discovery_full_onboarding_requirement() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/project-initialization/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert "explicitly_deferred_with_constraints" in workflow["human_interaction"]["allowed_resume_states"]
    assert "defaulted" not in workflow["human_interaction"]["allowed_resume_states"]
    assert "unresolved" not in workflow["human_interaction"]["allowed_resume_states"]
    prepare_policy = workflow["intent_mode_phase_policy"]["prepare-workflow"]
    assert (
        prepare_policy["target_workflow_context_decision_packet"]
        == "conditional_when_bounded_target_workflow_open_decisions_are_discovered"
    )
    target_phase = next(
        phase
        for phase in workflow["phases"]
        if phase.get("id") == "target_workflow_context_decision_packet"
    )
    open_packet = target_phase["open_decision_packet"]
    assert open_packet["packet_kind"] == "target_workflow_open_decisions"
    assert open_packet["owning_requirement_ref_required"] is True
    assert set(open_packet["allowed_decision_scopes"]) == {
        "run_scoped",
        "persistent_policy_candidate",
    }
    assert "owning_requirement_ref" in open_packet["required_fields"]
    assert open_packet["persistent_policy_activation_allowed"] is False

    broken = copy.deepcopy(workflow)
    broken["intent_mode_phase_policy"]["unknown-discovery"]["must_not_require"].remove("human_approval")

    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken)
    assert errors
    assert "unknown-discovery must not require human_approval" in "\n".join(errors)

    broken_risk = copy.deepcopy(workflow)
    broken_risk["intent_mode_phase_policy"]["risk-domain-assessment"]["must_not_require"].remove("human_approval")
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_risk)
    assert errors
    assert "risk-domain-assessment must not require human_approval" in "\n".join(errors)

    broken_attach = copy.deepcopy(workflow)
    for phase in broken_attach["phases"]:
        if phase.get("id") == "attach_or_verify_upstream":
            phase["applies_to_intent_modes"].append("unknown-discovery")
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_attach)
    assert errors
    assert "attach_or_verify_upstream must not apply to unknown-discovery" in "\n".join(errors)

    broken_top_level_resume_state = copy.deepcopy(workflow)
    broken_top_level_resume_state["human_interaction"]["allowed_resume_states"].remove(
        "explicitly_deferred_with_constraints"
    )
    errors = validate_repo.validate_project_initialization_human_interaction(path, broken_top_level_resume_state)
    assert "human_interaction.allowed_resume_states must include explicitly_deferred_with_constraints" in "\n".join(errors)

    broken_top_level_defaulted = copy.deepcopy(workflow)
    broken_top_level_defaulted["human_interaction"]["allowed_resume_states"].append("defaulted")
    errors = validate_repo.validate_project_initialization_human_interaction(path, broken_top_level_defaulted)
    assert "human_interaction.allowed_resume_states must not include defaulted as a global resume state" in "\n".join(errors)

    broken_top_level_unresolved = copy.deepcopy(workflow)
    broken_top_level_unresolved["human_interaction"]["allowed_resume_states"].append("unresolved")
    errors = validate_repo.validate_project_initialization_human_interaction(path, broken_top_level_unresolved)
    assert "human_interaction.allowed_resume_states must not include unresolved as a global resume state" in "\n".join(errors)

    broken_outputs = copy.deepcopy(workflow)
    broken_outputs["outputs"].append("project-operating-decisions.yaml")
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_outputs)
    assert errors
    assert "top-level outputs must be mode-neutral" in "\n".join(errors)

    broken_draft_outputs = copy.deepcopy(workflow)
    broken_draft_outputs["outputs"].append(".agentsflow/project.yaml draft")
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_draft_outputs)
    assert errors
    assert "top-level outputs must be mode-neutral" in "\n".join(errors)

    broken_unknown_outputs = copy.deepcopy(workflow)
    broken_unknown_outputs["mode_gated_outputs"]["unknown-discovery"].append(".agentsflow/project.yaml draft")
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_unknown_outputs)
    assert errors
    assert "mode_gated_outputs.unknown-discovery must not include activation outputs" in "\n".join(errors)

    broken_prepare_activation_outputs = copy.deepcopy(workflow)
    broken_prepare_activation_outputs["mode_gated_outputs"]["prepare-workflow"].append(".agentsflow/project.yaml draft")
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_prepare_activation_outputs)
    assert errors
    assert "mode_gated_outputs.prepare-workflow must not include activation outputs" in "\n".join(errors)

    broken_prepare_outputs = copy.deepcopy(workflow)
    broken_prepare_outputs["mode_gated_outputs"]["prepare-workflow"] = [
        item
        for item in broken_prepare_outputs["mode_gated_outputs"]["prepare-workflow"]
        if "target workflow human decision packet" not in item
    ]
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_prepare_outputs)
    assert errors
    assert "mode_gated_outputs.prepare-workflow missing" in "\n".join(errors)

    broken_prepare_policy = copy.deepcopy(workflow)
    broken_prepare_policy["intent_mode_phase_policy"]["prepare-workflow"].pop(
        "target_workflow_context_decision_packet"
    )
    broken_prepare_policy["intent_mode_phase_policy"]["prepare-workflow"][
        "operating_decisions_interview"
    ] = "conditional_when_bounded_target_workflow_open_decisions_are_discovered"
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_prepare_policy)
    joined = "\n".join(errors)
    assert "target_workflow_context_decision_packet" in joined
    assert "must not use operating_decisions_interview" in joined

    broken_prepare_policy_value = copy.deepcopy(workflow)
    broken_prepare_policy_value["intent_mode_phase_policy"]["prepare-workflow"][
        "target_workflow_context_decision_packet"
    ] = "conditional_when_target_workflow_policy_is_missing"
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_prepare_policy_value)
    assert "bounded target-workflow open decisions" in "\n".join(errors)

    broken_target_open_decision_shape = copy.deepcopy(workflow)
    for phase in broken_target_open_decision_shape["phases"]:
        if phase.get("id") == "target_workflow_context_decision_packet":
            phase["open_decision_packet"]["required_fields"].remove("owning_requirement_ref")
    errors = validate_repo.validate_project_initialization_operating_decisions(path, broken_target_open_decision_shape)
    assert "target_workflow_context_decision_packet required_fields missing: owning_requirement_ref" in "\n".join(errors)

    broken_target_resume = copy.deepcopy(workflow)
    for phase in broken_target_resume["phases"]:
        if phase.get("id") == "target_workflow_context_decision_packet":
            phase["human_interaction"]["allowed_resume_states"].append("unresolved")
            phase["human_interaction"].pop("resume_policy")
    errors = validate_repo.validate_project_initialization_operating_decisions(path, broken_target_resume)
    joined = "\n".join(errors)
    assert "must not allow bare unresolved resume state" in joined
    assert "must block readiness on unresolved blocking-material decisions" in joined

    broken_target_deferred_resume = copy.deepcopy(workflow)
    for phase in broken_target_deferred_resume["phases"]:
        if phase.get("id") == "target_workflow_context_decision_packet":
            phase["human_interaction"]["allowed_resume_states"].remove("explicitly_deferred_with_constraints")
    errors = validate_repo.validate_project_initialization_operating_decisions(path, broken_target_deferred_resume)
    assert "must allow explicitly_deferred_with_constraints resume state" in "\n".join(errors)

    broken_target_answered_resume = copy.deepcopy(workflow)
    for phase in broken_target_answered_resume["phases"]:
        if phase.get("id") == "target_workflow_context_decision_packet":
            phase["human_interaction"]["allowed_resume_states"].remove("answered")
    errors = validate_repo.validate_project_initialization_operating_decisions(path, broken_target_answered_resume)
    assert "must allow answered resume state" in "\n".join(errors)

    broken_unconditional_packet = copy.deepcopy(workflow)
    broken_unconditional_packet["intent_mode_phase_policy"]["prepare-workflow"]["requires"].append(
        "target_workflow_context_decision_packet"
    )
    broken_unconditional_packet["intent_mode_phase_policy"]["prepare-workflow"].pop("conditional_requires")
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_unconditional_packet)
    joined = "\n".join(errors)
    assert "must not require target_workflow_context_decision_packet unconditionally" in joined
    assert "conditional_requires must include target_workflow_context_decision_packet" in joined

    broken_prepare_gate = copy.deepcopy(workflow)
    for phase in broken_prepare_gate["phases"]:
        if phase.get("id") == "project_initialization_gate":
            phase["applies_to_intent_modes"].append("prepare-workflow")
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_prepare_gate)
    assert errors
    assert "phase project_initialization_gate must apply exactly to: adoption-onboarding" in "\n".join(errors)

    broken_target_gate = copy.deepcopy(workflow)
    broken_target_gate["phases"] = [
        phase for phase in broken_target_gate["phases"] if phase.get("id") != "target_workflow_readiness_gate"
    ]
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_target_gate)
    assert errors
    assert "must include target_workflow_readiness_gate phase" in "\n".join(errors)

    broken_target_gate_order = copy.deepcopy(workflow)
    for phase in broken_target_gate_order["phases"]:
        if phase.get("id") == "target_workflow_readiness_gate":
            phase.pop("runs_after")
            phase.pop("runs_after_policy")
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_target_gate_order)
    joined = "\n".join(errors)
    assert "target_workflow_readiness_gate must run after target_workflow_context_decision_packet" in joined
    assert "after_conditional_target_workflow_context_decision_packet_when_required" in joined

    broken_target_gate_position = copy.deepcopy(workflow)
    phases = broken_target_gate_position["phases"]
    packet_index = next(
        index
        for index, phase in enumerate(phases)
        if phase.get("id") == "target_workflow_context_decision_packet"
    )
    gate_index = next(
        index
        for index, phase in enumerate(phases)
        if phase.get("id") == "target_workflow_readiness_gate"
    )
    phases[packet_index], phases[gate_index] = phases[gate_index], phases[packet_index]
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_target_gate_position)
    assert "target_workflow_context_decision_packet must appear before target_workflow_readiness_gate" in "\n".join(errors)

    broken_target_binding = copy.deepcopy(workflow)
    broken_target_binding["phases"] = [
        phase for phase in broken_target_binding["phases"] if phase.get("id") != "target_workflow_binding_draft"
    ]
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_target_binding)
    assert "must include target_workflow_binding_draft phase" in "\n".join(errors)

    broken_target_binding_required = copy.deepcopy(workflow)
    broken_target_binding_required["intent_mode_phase_policy"]["prepare-workflow"]["requires"].remove(
        "target_workflow_binding_draft"
    )
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_target_binding_required)
    assert "prepare-workflow requires must include target_workflow_binding_draft" in "\n".join(errors)

    broken_target_binding_order = copy.deepcopy(workflow)
    for phase in broken_target_binding_order["phases"]:
        if phase.get("id") == "target_workflow_binding_draft":
            phase["runs_after"] = []
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_target_binding_order)
    assert "target_workflow_binding_draft must run after target_workflow_readiness_gate" in "\n".join(errors)

    broken_target_binding_position = copy.deepcopy(workflow)
    phases = broken_target_binding_position["phases"]
    gate_index = next(
        index
        for index, phase in enumerate(phases)
        if phase.get("id") == "target_workflow_readiness_gate"
    )
    binding_index = next(
        index
        for index, phase in enumerate(phases)
        if phase.get("id") == "target_workflow_binding_draft"
    )
    phases[gate_index], phases[binding_index] = phases[binding_index], phases[gate_index]
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_target_binding_position)
    assert "target_workflow_readiness_gate must appear before target_workflow_binding_draft" in "\n".join(errors)

    broken_review = copy.deepcopy(workflow)
    for phase in broken_review["phases"]:
        if phase.get("id") == "initialization_review":
            phase["runs_after"] = ["project_initialization_gate"]
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_review)
    assert errors
    joined = "\n".join(errors)
    assert "initialization_review must run after target_workflow_readiness_gate" in joined
    assert "initialization_review must run after target_workflow_binding_draft" in joined

    broken_prepare_leak = copy.deepcopy(workflow)
    for phase in broken_prepare_leak["phases"]:
        if phase.get("id") == "target_workflow_context_decision_packet":
            phase["outputs"].append("project-operating-decisions.yaml")
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_prepare_leak)
    assert errors
    assert "target_workflow_context_decision_packet must not produce prepare-workflow forbidden artifact" in "\n".join(errors)

    broken_pre_gate_handoff_leak = copy.deepcopy(workflow)
    for phase in broken_pre_gate_handoff_leak["phases"]:
        if phase.get("id") == "target_workflow_context_decision_packet":
            phase["outputs"].append("target workflow binding draft for prepare-workflow")
            phase["outputs"].append("target workflow gate readiness report for prepare-workflow")
            phase["outputs"].append("target-workflow-readiness-gate-report.md")
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_pre_gate_handoff_leak)
    joined = "\n".join(errors)
    assert "must not produce target workflow binding/readiness handoff before target_workflow_binding_draft" in joined
    assert "must not produce target workflow readiness gate report before target_workflow_readiness_gate" in joined

    broken_operating_scope = copy.deepcopy(workflow)
    for phase in broken_operating_scope["phases"]:
        if phase.get("id") == "operating_decisions_interview":
            phase["applies_to_intent_modes"].append("prepare-workflow")
    errors = validate_repo.validate_project_initialization_operating_decisions(path, broken_operating_scope)
    assert errors
    assert "operating_decisions_interview must apply only to adoption-onboarding" in "\n".join(errors)

    broken_legacy_discovery_scope = copy.deepcopy(workflow)
    for phase in broken_legacy_discovery_scope["phases"]:
        if phase.get("id") == "legacy_agent_system_discovery":
            phase.pop("applies_to_intent_modes")
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_legacy_discovery_scope)
    assert errors
    assert (
        "phase legacy_agent_system_discovery must apply exactly to: adoption-onboarding, legacy-cleanup"
        in "\n".join(errors)
    )

    broken_order = copy.deepcopy(workflow)
    legacy_phase = next(
        phase for phase in broken_order["phases"] if phase.get("id") == "legacy_adoption_mode_decision"
    )
    broken_order["phases"].remove(legacy_phase)
    broken_order["phases"].insert(2, legacy_phase)
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_order)
    assert errors
    assert "legacy_adoption_mode_decision must run after expert_assessment" in "\n".join(errors)


def test_project_initialization_requires_documentation_disposition_decision() -> None:
    import yaml

    path = ROOT / "workflows/project-initialization/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    templates = set(workflow["uses"]["templates"])
    assert "project-documentation-disposition.yaml" in templates

    mode_outputs = workflow["mode_gated_outputs"]
    for mode in ["adoption-onboarding", "prepare-workflow", "legacy-cleanup"]:
        assert any(
            "project-documentation-disposition.yaml" in output
            for output in mode_outputs[mode]
        ), mode

    phases = workflow["phases"]
    phase_by_id = {phase["id"]: phase for phase in phases if "id" in phase}
    disposition = phase_by_id.get("documentation_disposition_decision")
    assert disposition is not None
    assert set(disposition["applies_to_intent_modes"]) == {
        "adoption-onboarding",
        "prepare-workflow",
        "legacy-cleanup",
    }
    assert "project-documentation-disposition.yaml" in disposition["outputs"]
    assert "project-knowledge-extraction.md when documentation_legacy_adoption.mode is knowledge-extraction" in disposition["outputs"]
    assert disposition["legacy_adoption_question_required"] is True
    assert disposition["agent_may_select_legacy_adoption_without_human"] is False
    assert "defaulted" not in disposition["human_interaction"]["allowed_resume_states"]
    assert "unresolved" not in disposition["human_interaction"]["allowed_resume_states"]
    assert "light-extraction" not in disposition["supported_documentation_legacy_adoption_modes"]
    assert "knowledge-extraction" in disposition["supported_documentation_legacy_adoption_modes"]
    assert disposition["supported_documentation_extraction_depths"] == [
        "light",
        "standard",
        "deep",
    ]
    assert disposition["default_documentation_extraction_depth_by_intent_mode"][
        "prepare-workflow"
    ] == "standard"
    assert "implementation phase" in disposition["implementation_readiness_rule"]
    assert "documentation-history-index.md" in disposition["inputs"]
    assert "project-inventory.json" in disposition["inputs"]
    assert "project-assessment.json" in disposition["inputs"]
    assert "documentation_and_history_discovery" in disposition["runs_after"]
    assert "expert_assessment" in disposition["runs_after"]

    legacy = phase_by_id["legacy_adoption_mode_decision"]
    target = phase_by_id["target_workflow_context_decision_packet"]
    target_binding = phase_by_id["target_workflow_binding_draft"]
    overlay = phase_by_id["overlay_draft"]
    for phase in [legacy, target, target_binding, overlay]:
        assert "project-documentation-disposition.yaml" in phase["inputs"]
    conditional_extraction_input = (
        "project-knowledge-extraction.md when documentation_legacy_adoption.mode is knowledge-extraction"
    )
    assert conditional_extraction_input in target["inputs"]
    assert conditional_extraction_input in target_binding["inputs"]


def test_target_workflow_readiness_gate_requires_documentation_disposition() -> None:
    import yaml

    gate = yaml.safe_load((ROOT / "gates/target_workflow_readiness_gate.yaml").read_text(encoding="utf-8"))
    assert "project-documentation-disposition.yaml" in gate["inputs"]
    assert any(
        "project-documentation-disposition.yaml" in evidence
        for evidence in gate["required_evidence"]
    )
    assert any("existing project policy/workflow binding evidence" in item for item in gate["inputs"])
    assert any("target workflow preflight findings" in item for item in gate["inputs"])
    assert any("human decision packet" in item for item in gate["inputs"])
    assert any("project-knowledge-extraction.md" in item for item in gate["inputs"])
    assert any("human risk acceptance evidence" in item for item in gate["inputs"])
    assert any("extraction depth upgrade evidence" in item for item in gate["inputs"])
    assert any("existing project policy/workflow binding evidence" in item for item in gate["required_evidence"])
    assert any("human decision packet" in item for item in gate["required_evidence"])
    assert any("risk-surface" in item for item in gate["required_evidence"])
    assert any("Failure Path Matrix" in item for item in gate["required_evidence"])
    assert any("project-knowledge-extraction.md" in item for item in gate["required_evidence"])
    assert any("human risk acceptance evidence" in item for item in gate["required_evidence"])
    open_packet = gate["open_decision_packet"]
    assert open_packet["packet_kind"] == "target_workflow_open_decisions"
    assert open_packet["owning_requirement_ref_required"] is True
    assert set(open_packet["allowed_decision_scopes"]) == {
        "run_scoped",
        "persistent_policy_candidate",
    }
    assert "owning_requirement_ref" in open_packet["required_fields"]
    assert open_packet["persistent_policy_activation_allowed"] is False
    assert "missing_light_extraction_risk_acceptance" in gate["pass_policy"]["needs_human_decision_on"]
    assert "missing_risk_surface_policy" in gate["pass_policy"]["needs_human_decision_on"]
    assert "missing_failure_path_matrix_policy" in gate["pass_policy"]["needs_human_decision_on"]
    assert "unresolved_material_design_decision" in gate["pass_policy"]["needs_human_decision_on"]


def test_target_workflow_readiness_gate_blocks_unresolved_material_design_decisions() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "gates/target_workflow_readiness_gate.yaml"
    gate = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken_gate = copy.deepcopy(gate)
    broken_gate["pass_policy"]["needs_human_decision_on"].remove("unresolved_material_design_decision")
    errors = validate_repo.validate_gate_manifest(ROOT, path, broken_gate)
    assert "target_workflow_readiness_gate must block unresolved material design decisions" in "\n".join(errors)

    broken_required_ref = copy.deepcopy(gate)
    broken_required_ref["open_decision_packet"]["required_fields"].remove("owning_requirement_ref")
    errors = validate_repo.validate_gate_manifest(ROOT, path, broken_required_ref)
    assert "target_workflow_readiness_gate required_fields missing: owning_requirement_ref" in "\n".join(errors)

    broken_scope = copy.deepcopy(gate)
    broken_scope["open_decision_packet"]["allowed_decision_scopes"].remove("persistent_policy_candidate")
    errors = validate_repo.validate_gate_manifest(ROOT, path, broken_scope)
    assert "target_workflow_readiness_gate allowed_decision_scopes missing: persistent_policy_candidate" in "\n".join(errors)

    broken_existing_context = copy.deepcopy(gate)
    broken_existing_context["inputs"] = [
        item for item in broken_existing_context["inputs"] if "existing project policy/workflow binding evidence" not in item
    ]
    broken_existing_context["required_evidence"] = [
        item
        for item in broken_existing_context["required_evidence"]
        if "existing project policy/workflow binding evidence" not in item
    ]
    errors = validate_repo.validate_gate_manifest(ROOT, path, broken_existing_context)
    joined = "\n".join(errors)
    assert "inputs must allow existing project policy/workflow binding evidence" in joined
    assert "required_evidence must include existing project policy/workflow binding evidence or preflight findings" in joined

    broken_preflight = copy.deepcopy(gate)
    broken_preflight["inputs"] = [
        item for item in broken_preflight["inputs"] if "target workflow preflight findings" not in item
    ]
    errors = validate_repo.validate_gate_manifest(ROOT, path, broken_preflight)
    assert "inputs must allow target workflow preflight findings" in "\n".join(errors)

    broken_human_packet = copy.deepcopy(gate)
    broken_human_packet["inputs"] = [
        item for item in broken_human_packet["inputs"] if "human decision packet" not in item
    ]
    broken_human_packet["required_evidence"] = [
        item for item in broken_human_packet["required_evidence"] if "human decision packet" not in item
    ]
    errors = validate_repo.validate_gate_manifest(ROOT, path, broken_human_packet)
    joined = "\n".join(errors)
    assert "inputs must allow human decision packet" in joined
    assert "required_evidence must include human decision packet" in joined

    broken_extraction_artifact = copy.deepcopy(gate)
    broken_extraction_artifact["inputs"] = [
        item for item in broken_extraction_artifact["inputs"] if "project-knowledge-extraction.md" not in item
    ]
    broken_extraction_artifact["required_evidence"] = [
        item
        for item in broken_extraction_artifact["required_evidence"]
        if "project-knowledge-extraction.md" not in item
    ]
    errors = validate_repo.validate_gate_manifest(ROOT, path, broken_extraction_artifact)
    joined = "\n".join(errors)
    assert "inputs must include conditional project-knowledge-extraction.md" in joined
    assert "required_evidence must include conditional project-knowledge-extraction.md" in joined

    broken_light_risk_acceptance = copy.deepcopy(gate)
    broken_light_risk_acceptance["inputs"] = [
        item
        for item in broken_light_risk_acceptance["inputs"]
        if "human risk acceptance evidence" not in item
        and "extraction depth upgrade evidence" not in item
    ]
    broken_light_risk_acceptance["required_evidence"] = [
        item
        for item in broken_light_risk_acceptance["required_evidence"]
        if "human risk acceptance evidence" not in item
    ]
    broken_light_risk_acceptance["pass_policy"]["needs_human_decision_on"].remove(
        "missing_light_extraction_risk_acceptance"
    )
    errors = validate_repo.validate_gate_manifest(ROOT, path, broken_light_risk_acceptance)
    joined = "\n".join(errors)
    assert "inputs must include light extraction risk acceptance evidence" in joined
    assert "inputs must include light extraction upgrade evidence" in joined
    assert "required_evidence must include light extraction risk acceptance evidence or upgrade evidence" in joined
    assert "must block missing light extraction risk acceptance" in joined

    broken_light_upgrade_required_evidence = copy.deepcopy(gate)
    broken_light_upgrade_required_evidence["required_evidence"] = [
        item.replace(
            ", or evidence that extraction_depth was upgraded to standard or deep",
            "",
        )
        for item in broken_light_upgrade_required_evidence["required_evidence"]
    ]
    errors = validate_repo.validate_gate_manifest(ROOT, path, broken_light_upgrade_required_evidence)
    assert "required_evidence must include light extraction upgrade evidence" in "\n".join(errors)

    broken_pass_policy = copy.deepcopy(gate)
    broken_pass_policy["pass_policy"] = "invalid"
    errors = validate_repo.validate_gate_manifest(ROOT, path, broken_pass_policy)
    joined = "\n".join(errors)
    assert "pass_policy must be a mapping" in joined
    assert "target_workflow_readiness_gate must block unresolved material design decisions" in joined


def test_project_initialization_gate_requires_documentation_disposition() -> None:
    import yaml

    gate = yaml.safe_load((ROOT / "gates/project_initialization_gate.yaml").read_text(encoding="utf-8"))
    assert "project-documentation-disposition.yaml" in gate["inputs"]
    assert any(
        "project-documentation-disposition.yaml" in evidence
        for evidence in gate["required_evidence"]
    )


def test_human_interaction_protocol_lists_documentation_disposition_pause() -> None:
    protocol = (ROOT / "docs/human-interaction-protocol.md").read_text(encoding="utf-8")
    assert "documentation_disposition_decision" in protocol
    normalized = " ".join(protocol.split())
    assert "before legacy adoption, target-workflow readiness, or overlay drafting" in normalized


def test_big_feature_requires_manifest_plan_gate() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/big-feature-contract-first/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(workflow)
    broken["phases"] = [phase for phase in broken["phases"] if phase.get("id") != "plan_gate"]
    broken["review"]["gates"].remove("plan_gate")
    broken["concrete_gates"].remove("plan_gate")

    errors = validate_repo.validate_big_feature_plan_gate_policy(path, broken)
    joined = "\n".join(errors)
    assert "must include plan_gate phase" in joined
    assert "review.gates must include plan_gate" in joined
    assert "concrete_gates must include plan_gate" in joined

    broken_plan = copy.deepcopy(workflow)
    for phase in broken_plan["phases"]:
        if phase.get("id") == "technical_plan":
            phase["outputs"].remove("repository-grounding-report.md")
    errors = validate_repo.validate_big_feature_plan_gate_policy(path, broken_plan)
    assert "technical_plan phase missing outputs: repository-grounding-report.md" in "\n".join(errors)

    broken_strictness = copy.deepcopy(workflow)
    for phase in broken_strictness["phases"]:
        if phase.get("id") in {"technical_plan", "plan_gate"}:
            phase["applies_to_strictness"] = ["L2", "L3", "L4"]
    errors = validate_repo.validate_big_feature_plan_gate_policy(path, broken_strictness)
    joined = "\n".join(errors)
    assert "technical_plan phase must apply exactly to effective strictness values L3 and L4" in joined
    assert "plan_gate phase must apply exactly to effective strictness values L3 and L4" in joined

    broken_gate_order = copy.deepcopy(workflow)
    for phase in broken_gate_order["phases"]:
        if phase.get("id") == "plan_gate":
            phase["runs_after"] = ["impact"]
    errors = validate_repo.validate_big_feature_plan_gate_policy(path, broken_gate_order)
    assert "plan_gate phase must run after technical_plan" in "\n".join(errors)

    broken_red = copy.deepcopy(workflow)
    for phase in broken_red["phases"]:
        if phase.get("id") == "red_capture":
            phase["runs_after"] = []
            phase.pop("runs_after_policy", None)
    errors = validate_repo.validate_big_feature_plan_gate_policy(path, broken_red)
    joined = "\n".join(errors)
    assert "red_capture phase must run after plan_gate" in joined
    assert "after_applicable_strictness_gate" in joined


def test_workflow_binding_rejects_too_low_max_review_cycles(tmp_path) -> None:
    import copy
    import shutil
    import yaml

    project = tmp_path / "project"
    shutil.copytree(ROOT / "examples/project-overlay/.agentsflow", project / ".agentsflow")
    binding_path = project / ".agentsflow/workflows/big-feature-contract-first.binding.yaml"
    binding = yaml.safe_load(binding_path.read_text(encoding="utf-8"))
    binding.pop("review_cycle", None)
    binding_path.write_text(yaml.safe_dump(binding, sort_keys=False), encoding="utf-8")

    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode == 0, result.stdout + result.stderr

    missing_risk_policy = copy.deepcopy(binding)
    missing_risk_policy.pop("risk_surface_policy")
    binding_path.write_text(yaml.safe_dump(missing_risk_policy, sort_keys=False), encoding="utf-8")
    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode != 0
    assert "risk_surface_policy" in (result.stdout + result.stderr)

    weak_evidence_policy = copy.deepcopy(binding)
    weak_evidence_policy["evidence_policy"]["freshness"]["review_packet_after_latest_green_gate_required"] = False
    binding_path.write_text(yaml.safe_dump(weak_evidence_policy, sort_keys=False), encoding="utf-8")
    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode != 0
    assert "review_packet_after_latest_green_gate_required" in (result.stdout + result.stderr)

    missing_escalation_metadata = copy.deepcopy(binding)
    missing_escalation_metadata["review"].pop("selected_risk_surfaces")
    binding_path.write_text(yaml.safe_dump(missing_escalation_metadata, sort_keys=False), encoding="utf-8")
    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode != 0
    assert "selected_risk_surfaces" in (result.stdout + result.stderr)

    blank_escalation_surface = copy.deepcopy(binding)
    blank_escalation_surface["review"]["selected_risk_surfaces"] = ["   "]
    binding_path.write_text(yaml.safe_dump(blank_escalation_surface, sort_keys=False), encoding="utf-8")
    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode != 0
    assert "selected_risk_surfaces" in (result.stdout + result.stderr)

    binding["review_cycle"] = {}
    binding_path.write_text(yaml.safe_dump(binding, sort_keys=False), encoding="utf-8")

    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode == 0, result.stdout + result.stderr

    binding["review_cycle"]["max_review_cycles"] = 1
    binding_path.write_text(yaml.safe_dump(binding, sort_keys=False), encoding="utf-8")

    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode != 0
    assert "max_review_cycles" in (result.stdout + result.stderr)

    binding["review_cycle"]["max_review_cycles"] = "five"
    binding_path.write_text(yaml.safe_dump(binding, sort_keys=False), encoding="utf-8")

    result = run("scripts/validate_project_binding.py", "--project", str(project), "--agentsflow-root", ".")
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "review_cycle.max_review_cycles" in output
    assert "not of type 'integer'" in output


def test_repo_validation_checks_evidence_probe_run_artifacts(tmp_path) -> None:
    import json
    import shutil

    root = tmp_path / "repo"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__", "run-artifacts"),
    )
    run_dir = root / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator"
    report = json.loads((root / "templates/evidence-probe-report.json").read_text(encoding="utf-8"))
    report["commands_run"][0]["instrument_id"] = "not-declared"
    (run_dir / "evidence-probe-report.invalid.json").write_text(json.dumps(report), encoding="utf-8")

    result = run("scripts/validate_repo.py", "--root", str(root))
    assert result.returncode != 0
    assert "not declared in allowed_instruments" in (result.stdout + result.stderr)


def test_repo_validation_checks_all_documentation_disposition_artifacts(tmp_path) -> None:
    import shutil

    root = tmp_path / "repo"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__", "run-artifacts"),
    )
    rogue_dir = root / "examples" / "symlinked-initialization"
    rogue_dir.mkdir()
    (rogue_dir / "project-documentation-disposition.yaml").symlink_to(
        root / "templates" / "project-documentation-disposition.yaml"
    )

    result = run("scripts/validate_repo.py", "--root", str(root))
    assert result.returncode != 0
    assert "artifact_role template is reserved" in (result.stdout + result.stderr)


def test_validate_repo_uses_modular_facade() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415
    from repo_validation.runner import validate_repository  # noqa: PLC0415

    assert validate_repo.validate_repository is validate_repository
    facade_lines = (ROOT / "scripts/validate_repo.py").read_text(encoding="utf-8").splitlines()
    assert len(facade_lines) <= 160


def test_repo_validation_rejects_duplicate_yaml_keys(tmp_path) -> None:
    import shutil

    root = tmp_path / "repo"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__", "run-artifacts"),
    )
    workflow = root / "workflows/big-feature-contract-first/workflow.yaml"
    workflow.write_text(
        workflow.read_text(encoding="utf-8") + "\n_duplicate_test: one\n_duplicate_test: two\n",
        encoding="utf-8",
    )

    result = run("scripts/validate_repo.py", "--root", str(root))
    assert result.returncode != 0
    assert "duplicate YAML key" in (result.stdout + result.stderr)


def test_validate_repo_tracked_only_ignores_untracked_files(tmp_path) -> None:
    import shutil

    root = tmp_path / "repo"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__", "run-artifacts"),
    )
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "-f", "."], cwd=root, check=True, capture_output=True, text=True)

    untracked = root / ".agentsflow" / "untracked.yaml"
    untracked.parent.mkdir(parents=True, exist_ok=True)
    untracked.write_text("duplicate: one\nduplicate: two\n", encoding="utf-8")

    default_result = run("scripts/validate_repo.py", "--root", str(root))
    assert default_result.returncode != 0
    assert "duplicate YAML key" in (default_result.stdout + default_result.stderr)

    tracked_result = run("scripts/validate_repo.py", "--root", str(root), "--tracked-only")
    assert tracked_result.returncode == 0, tracked_result.stdout + tracked_result.stderr


def test_validate_repo_rejects_tracked_agentsflow_run_artifacts(tmp_path) -> None:
    import shutil

    root = tmp_path / "repo"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__", "run-artifacts"),
    )
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
    run_artifact = root / "run-artifacts" / "agentsflow" / "runs" / "2026-06-24-local-run" / "run.yaml"
    run_artifact.parent.mkdir(parents=True)
    run_artifact.write_text("run_id: 2026-06-24-local-run\n", encoding="utf-8")
    other_run_artifact = root / "run-artifacts" / "other" / "provider-output.json"
    other_run_artifact.parent.mkdir(parents=True)
    other_run_artifact.write_text('{"local":"artifact"}\n', encoding="utf-8")
    subprocess.run(["git", "add", "-f", "."], cwd=root, check=True, capture_output=True, text=True)

    result = run("scripts/validate_repo.py", "--root", str(root))
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "tracked local run artifact is not allowed" in output
    assert "run-artifacts/agentsflow/runs/2026-06-24-local-run/run.yaml" in output
    assert "run-artifacts/other/provider-output.json" in output

    tracked_result = run("scripts/validate_repo.py", "--root", str(root), "--tracked-only")
    assert tracked_result.returncode != 0
    tracked_output = tracked_result.stdout + tracked_result.stderr
    assert "tracked local run artifact is not allowed" in tracked_output
    assert "run-artifacts/other/provider-output.json" in tracked_output


def test_validate_repo_accepts_explicit_pr_merge_readiness_report() -> None:
    report = (
        "examples/pr-merge-readiness/complete/pr-merge-readiness-report.json"
    )

    result = run(
        "scripts/validate_repo.py",
        "--root",
        str(ROOT),
        "--pr-merge-readiness-report",
        report,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_validate_repo_rejects_explicit_invalid_pr_merge_readiness_report(tmp_path) -> None:
    report = tmp_path / "pr-merge-readiness-report.json"
    report.write_text(json.dumps({"version": 1}), encoding="utf-8")

    result = run(
        "scripts/validate_repo.py",
        "--root",
        str(ROOT),
        "--pr-merge-readiness-report",
        str(report),
    )

    assert result.returncode != 0
    assert "schema error" in (result.stdout + result.stderr)


def test_v02_review_control_requires_required_gate_order() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/review-only-fusion/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(workflow)
    for phase in broken["phases"]:
        if phase.get("id") == "independent_review":
            phase["runs_after"] = []

    errors = validate_repo.validate_required_review_gate_order(path, broken)
    assert errors
    assert "must run after evidence_gate" in "\n".join(errors)


def test_big_feature_review_phase_requires_verification_gate_order() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/big-feature-contract-first/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(workflow)
    for phase in broken["phases"]:
        if phase.get("id") == "review":
            phase["runs_after"] = []

    errors = validate_repo.validate_required_review_gate_order(path, broken)
    assert errors
    assert "must run after verification_gate" in "\n".join(errors)


def test_v02_review_control_gate_order_rejects_wrong_phase_kinds() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/review-only-fusion/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(workflow)
    for phase in broken["phases"]:
        if phase.get("id") == "evidence_gate":
            phase["kind"] = "planning"
        if phase.get("id") == "independent_review":
            phase["kind"] = "specification"

    errors = validate_repo.validate_required_review_gate_order(path, broken)
    assert errors
    joined = "\n".join(errors)
    assert "must be kind verification or gate" in joined
    assert "must be kind review" in joined


def test_workflow_default_strictness_is_required() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/big-feature-contract-first/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(workflow)
    broken.pop("default_strictness", None)

    schema_errors = validate_repo.validate_against_schema(
        path,
        broken,
        validate_repo.workflow_schema(ROOT),
    )
    policy_errors = validate_repo.validate_workflow_default_strictness(path, broken)
    joined = "\n".join(schema_errors + policy_errors)
    assert "default_strictness" in joined


def test_workflow_default_strictness_must_be_supported() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/big-feature-contract-first/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(workflow)
    broken["default_strictness"] = "L0"

    errors = validate_repo.validate_workflow_default_strictness(path, broken)
    assert "default_strictness L0 must be listed in supported_profiles.strictness" in "\n".join(errors)


def test_primary_e2e_workflow_run_artifacts_schema_pass() -> None:
    import json

    import jsonschema
    import yaml

    run_schema = json.loads((ROOT / "schemas/workflow-run.schema.json").read_text(encoding="utf-8"))
    report_schema = json.loads((ROOT / "schemas/reviewer-report.schema.json").read_text(encoding="utf-8"))
    run_root = ROOT / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator"

    jsonschema.Draft202012Validator(run_schema).validate(
        yaml.safe_load((run_root / "run.yaml").read_text(encoding="utf-8"))
    )
    for name in ["reviewer-report.generalist-a.json", "reviewer-report.generalist-b.json"]:
        jsonschema.Draft202012Validator(report_schema).validate(
            json.loads((run_root / name).read_text(encoding="utf-8"))
        )


def test_reviewer_report_normalization_source_hash_is_validated(tmp_path) -> None:
    import copy
    import hashlib
    import json
    import shutil
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "root"
    root.mkdir()
    shutil.copytree(ROOT / "schemas", root / "schemas")
    raw_path = root / "reviewer-report.generalist-a.raw.md"
    raw_path.write_text("## Findings\n\nNo blockers.\n", encoding="utf-8")
    source_hash = "sha256:" + hashlib.sha256(raw_path.read_bytes()).hexdigest()
    report = {
        "reviewer": {
            "id": "internal-agent-generalist-a",
            "provider": "internal-agent",
            "role": "generalist",
            "model": "codex",
        },
        "summary": "No blockers.",
        "findings": [],
        "normalization": {
            "method": "orchestrator-extraction",
            "source_path": "reviewer-report.generalist-a.raw.md",
            "source_hash": source_hash,
            "schema_validation": "passed",
            "normalized_by": "main-orchestrating-agent",
        },
    }
    report_path = root / "reviewer-report.generalist-a.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    assert validate_repo.validate_reviewer_report_artifact(root, report_path) == []

    stale_hash = copy.deepcopy(report)
    stale_hash["normalization"]["source_hash"] = "sha256:" + "0" * 64
    report_path.write_text(json.dumps(stale_hash, indent=2), encoding="utf-8")
    errors = validate_repo.validate_reviewer_report_artifact(root, report_path)
    assert "normalization.source_hash hash mismatch" in "\n".join(errors)

    self_hash = copy.deepcopy(report)
    self_hash["normalization"]["output_hash"] = "sha256:" + "1" * 64
    report_path.write_text(json.dumps(self_hash, indent=2), encoding="utf-8")
    errors = validate_repo.validate_reviewer_report_artifact(root, report_path)
    assert "normalization.output_hash must be recorded outside reviewer-report JSON" in "\n".join(errors)


def test_workflow_run_strictness_requires_source_and_override_reason(tmp_path) -> None:
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    base = {
        "version": 1,
        "run_id": "2026-06-19-strictness-run",
        "workflow": "big-feature-contract-first",
        "agentsflow_version": "v0.2.0",
        "binding": ".agentsflow/workflows/big-feature-contract-first.binding.yaml",
        "status": "in_progress",
    }

    raw_path = tmp_path / "raw-run.yaml"
    raw = dict(base)
    raw["strictness"] = "L2"
    raw_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    raw_errors = validate_repo.validate_workflow_run_artifact(ROOT, raw_path)
    assert "strictness_source" in "\n".join(raw_errors)

    override_path = tmp_path / "override-run.yaml"
    override = dict(base)
    override["strictness"] = "L2"
    override["strictness_source"] = "project_override"
    override_path.write_text(yaml.safe_dump(override, sort_keys=False), encoding="utf-8")
    override_errors = validate_repo.validate_workflow_run_artifact(ROOT, override_path)
    assert "strictness_override_reason" in "\n".join(override_errors)


def test_workflow_run_rejects_disguised_workflow_default_strictness(tmp_path) -> None:
    import shutil
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    project = tmp_path / "project"
    shutil.copytree(ROOT / "examples/project-overlay/.agentsflow", project / ".agentsflow")
    run_dir = project / "Docs/agentsflow/runs/2026-06-19-disguised-default"
    run_dir.mkdir(parents=True)
    run_path = run_dir / "run.yaml"
    run_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-19-disguised-default",
                "workflow": "big-feature-contract-first",
                "agentsflow_version": "v0.2.0",
                "binding": ".agentsflow/workflows/big-feature-contract-first.binding.yaml",
                "strictness": "L2",
                "strictness_source": "workflow_default",
                "status": "in_progress",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    errors = validate_repo.validate_workflow_run_artifact(ROOT, run_path)
    assert "strictness_source workflow_default requires strictness L3" in "\n".join(errors)


def test_workflow_run_phase_guard_rejects_future_phase_artifact(tmp_path) -> None:
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    run_path = tmp_path / "run.yaml"
    run_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-19-bro-shadow",
                "workflow": "project-initialization",
                "agentsflow_version": "v0.2.0",
                "binding": ".agentsflow/workflows/project-initialization.binding.yaml",
                "status": "in_progress",
                "phase_guard": {
                    "current_phase": "raw_scan",
                    "allowed_next_phases": ["project_inventory"],
                    "allowed_outputs": ["project-raw-scan.json", "observed-facts.md"],
                    "draft_artifacts": [],
                    "forbidden_outputs_until_phase_exit": [
                        {
                            "path": "task.contract.md",
                            "until_phase": "contract",
                            "reason": "Feature contracts are not raw-scan outputs.",
                        }
                    ],
                },
                "artifacts": {
                    "root": "Docs/agentsflow/runs/2026-06-19-bro-shadow",
                    "raw_scan": "project-raw-scan.json",
                    "contract": "task.contract.md",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    errors = validate_repo.validate_workflow_run_artifact(ROOT, run_path)
    assert errors
    joined = "\n".join(errors)
    assert "current phase raw_scan" in joined
    assert "task.contract.md" in joined


def test_workflow_run_phase_guard_rejects_unlisted_artifact_without_explicit_forbidden(
    tmp_path,
) -> None:
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    run_path = tmp_path / "run.yaml"
    run_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-19-bro-shadow",
                "workflow": "project-initialization",
                "agentsflow_version": "v0.2.0",
                "binding": ".agentsflow/workflows/project-initialization.binding.yaml",
                "status": "in_progress",
                "phase_guard": {
                    "current_phase": "raw_scan",
                    "allowed_next_phases": ["project_inventory"],
                    "allowed_outputs": ["project-raw-scan.json", "observed-facts.md"],
                    "draft_artifacts": [],
                    "forbidden_outputs_until_phase_exit": [],
                },
                "artifacts": {
                    "root": "Docs/agentsflow/runs/2026-06-19-bro-shadow",
                    "raw_scan": "project-raw-scan.json",
                    "contract": "task.contract.md",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    errors = validate_repo.validate_workflow_run_artifact(ROOT, run_path)
    assert errors
    joined = "\n".join(errors)
    assert "not allowed in current phase raw_scan" in joined
    assert "task.contract.md" in joined


def test_workflow_run_phase_guard_checks_phase_evidence_and_status_artifacts(
    tmp_path,
) -> None:
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    run_path = tmp_path / "run.yaml"
    run_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-19-bro-shadow",
                "workflow": "project-initialization",
                "agentsflow_version": "v0.2.0",
                "binding": ".agentsflow/workflows/project-initialization.binding.yaml",
                "status": "in_progress",
                "phase_guard": {
                    "current_phase": "raw_scan",
                    "allowed_next_phases": ["project_inventory"],
                    "allowed_outputs": ["project-raw-scan.json", "observed-facts.md"],
                    "draft_artifacts": [],
                    "forbidden_outputs_until_phase_exit": [],
                },
                "artifacts": {
                    "root": "Docs/agentsflow/runs/2026-06-19-bro-shadow",
                    "raw_scan": "project-raw-scan.json",
                },
                "phase_evidence": {
                    "contract": "task.contract.md",
                    "root": "evidence-report.md",
                },
                "phase_status": [
                    {
                        "phase": "raw_scan",
                        "status": "in_progress",
                        "artifacts": ["observed-facts.md"],
                        "gate_report": "verification-gate-report.md",
                        "notes": ["ordinary status text is not an artifact"],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    errors = validate_repo.validate_workflow_run_artifact(ROOT, run_path)
    assert errors
    joined = "\n".join(errors)
    assert "phase_evidence.contract path task.contract.md" in joined
    assert "phase_evidence.root path evidence-report.md" in joined
    assert "phase_status[0].gate_report path verification-gate-report.md" in joined
    assert "ordinary status text" not in joined


def test_workflow_run_phase_guard_rejects_list_shaped_phase_evidence(tmp_path) -> None:
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    run_path = tmp_path / "run.yaml"
    run_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-19-bro-shadow",
                "workflow": "project-initialization",
                "agentsflow_version": "v0.2.0",
                "binding": ".agentsflow/workflows/project-initialization.binding.yaml",
                "status": "in_progress",
                "phase_guard": {
                    "current_phase": "raw_scan",
                    "allowed_next_phases": ["project_inventory"],
                    "allowed_outputs": ["project-raw-scan.json", "observed-facts.md"],
                    "draft_artifacts": [],
                    "forbidden_outputs_until_phase_exit": [],
                },
                "artifacts": {
                    "root": "Docs/agentsflow/runs/2026-06-19-bro-shadow",
                    "raw_scan": "project-raw-scan.json",
                },
                "phase_evidence": ["task.contract.md"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    errors = validate_repo.validate_workflow_run_artifact(ROOT, run_path)
    assert errors
    joined = "\n".join(errors)
    assert "phase_evidence" in joined
    assert "task.contract.md" in joined


def test_workflow_run_phase_guard_rejects_draft_artifact_as_evidence_or_output(
    tmp_path,
) -> None:
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    run_path = tmp_path / "run.yaml"
    run_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-19-bro-shadow",
                "workflow": "big-feature-contract-first",
                "agentsflow_version": "v0.2.0",
                "binding": ".agentsflow/workflows/big-feature-contract-first.binding.yaml",
                "status": "in_progress",
                "phase_guard": {
                    "current_phase": "operating_context_preflight",
                    "allowed_next_phases": ["contract"],
                    "allowed_outputs": ["human-questions.yaml", "human-decisions.yaml"],
                    "draft_artifacts": ["task.contract.md"],
                    "forbidden_outputs_until_phase_exit": [],
                },
                "artifacts": {
                    "root": "Docs/agentsflow/runs/2026-06-19-bro-shadow",
                    "task_contract_draft": "task.contract.md",
                },
                "phase_evidence": {
                    "contract": "task.contract.md",
                },
                "phase_status": [
                    {
                        "phase": "operating_context_preflight",
                        "outputs": ["task.contract.md"],
                        "task_contract_draft": "task.contract.md",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    errors = validate_repo.validate_workflow_run_artifact(ROOT, run_path)
    assert errors
    joined = "\n".join(errors)
    assert "phase_evidence.contract path task.contract.md" in joined
    assert "phase_status[0].outputs[0] path task.contract.md" in joined
    assert "phase_status[0].task_contract_draft path task.contract.md" in joined
    assert "artifacts.task_contract_draft path task.contract.md" not in joined


def test_workflow_run_phase_guard_rejects_allowed_and_draft_overlap(tmp_path) -> None:
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    run_path = tmp_path / "run.yaml"
    run_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-19-bro-shadow",
                "workflow": "big-feature-contract-first",
                "agentsflow_version": "v0.2.0",
                "binding": ".agentsflow/workflows/big-feature-contract-first.binding.yaml",
                "status": "in_progress",
                "phase_guard": {
                    "current_phase": "operating_context_preflight",
                    "allowed_next_phases": ["contract"],
                    "allowed_outputs": ["task.contract.md"],
                    "draft_artifacts": ["task.contract.md"],
                    "forbidden_outputs_until_phase_exit": [],
                },
                "artifacts": {
                    "root": "Docs/agentsflow/runs/2026-06-19-bro-shadow",
                    "task_contract_draft": "task.contract.md",
                },
                "phase_evidence": {
                    "contract": "task.contract.md",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    errors = validate_repo.validate_workflow_run_artifact(ROOT, run_path)
    assert errors
    joined = "\n".join(errors)
    assert "allowed_outputs and draft_artifacts must not overlap" in joined
    assert "phase_evidence.contract path task.contract.md" in joined


def test_workflow_run_phase_guard_uses_top_level_draft_slot(tmp_path) -> None:
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    invalid_path = tmp_path / "invalid-run.yaml"
    invalid_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-19-bro-shadow",
                "workflow": "big-feature-contract-first",
                "agentsflow_version": "v0.2.0",
                "binding": ".agentsflow/workflows/big-feature-contract-first.binding.yaml",
                "status": "in_progress",
                "phase_guard": {
                    "current_phase": "operating_context_preflight",
                    "allowed_next_phases": ["contract"],
                    "allowed_outputs": ["human-questions.yaml"],
                    "draft_artifacts": ["task.contract.md"],
                    "forbidden_outputs_until_phase_exit": [],
                },
                "artifacts": {
                    "root": "Docs/agentsflow/runs/2026-06-19-bro-shadow",
                    "contract": {
                        "draft_path": "task.contract.md",
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    invalid_errors = validate_repo.validate_workflow_run_artifact(ROOT, invalid_path)
    assert invalid_errors
    assert "artifacts.contract.draft_path path task.contract.md" in "\n".join(invalid_errors)

    not_draft_path = tmp_path / "not-draft-run.yaml"
    not_draft_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-19-bro-shadow",
                "workflow": "big-feature-contract-first",
                "agentsflow_version": "v0.2.0",
                "binding": ".agentsflow/workflows/big-feature-contract-first.binding.yaml",
                "status": "in_progress",
                "phase_guard": {
                    "current_phase": "operating_context_preflight",
                    "allowed_next_phases": ["contract"],
                    "allowed_outputs": ["human-questions.yaml"],
                    "draft_artifacts": ["task.contract.md"],
                    "forbidden_outputs_until_phase_exit": [],
                },
                "artifacts": {
                    "root": "Docs/agentsflow/runs/2026-06-19-bro-shadow",
                    "not_draft_contract": "task.contract.md",
                    "nondraft_contract": "task.contract.md",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    not_draft_errors = validate_repo.validate_workflow_run_artifact(ROOT, not_draft_path)
    assert not_draft_errors
    joined_not_draft_errors = "\n".join(not_draft_errors)
    assert "artifacts.not_draft_contract path task.contract.md" in joined_not_draft_errors
    assert "artifacts.nondraft_contract path task.contract.md" in joined_not_draft_errors

    valid_path = tmp_path / "valid-run.yaml"
    valid_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-19-bro-shadow",
                "workflow": "big-feature-contract-first",
                "agentsflow_version": "v0.2.0",
                "binding": ".agentsflow/workflows/big-feature-contract-first.binding.yaml",
                "status": "in_progress",
                "phase_guard": {
                    "current_phase": "operating_context_preflight",
                    "allowed_next_phases": ["contract"],
                    "allowed_outputs": ["human-questions.yaml"],
                    "draft_artifacts": ["task.contract.md"],
                    "forbidden_outputs_until_phase_exit": [],
                },
                "artifacts": {
                    "root": "Docs/agentsflow/runs/2026-06-19-bro-shadow",
                    "task_contract_draft": {
                        "path": "task.contract.md",
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    assert validate_repo.validate_workflow_run_artifact(ROOT, valid_path) == []


def test_workflow_run_phase_guard_rejects_malformed_artifacts_root_paths(
    tmp_path,
) -> None:
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    run_path = tmp_path / "run.yaml"
    run_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-19-bro-shadow",
                "workflow": "project-initialization",
                "agentsflow_version": "v0.2.0",
                "binding": ".agentsflow/workflows/project-initialization.binding.yaml",
                "status": "in_progress",
                "phase_guard": {
                    "current_phase": "raw_scan",
                    "allowed_next_phases": ["project_inventory"],
                    "allowed_outputs": ["project-raw-scan.json"],
                    "draft_artifacts": [],
                    "forbidden_outputs_until_phase_exit": [],
                },
                "artifacts": {
                    "root": {
                        "contract": "task.contract.md",
                    },
                    "raw_scan": "project-raw-scan.json",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    errors = validate_repo.validate_workflow_run_artifact(ROOT, run_path)
    assert errors
    joined = "\n".join(errors)
    assert "artifacts.root.contract path task.contract.md" in joined


def test_workflow_run_phase_guard_allows_current_phase_artifacts(tmp_path) -> None:
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    run_path = tmp_path / "run.yaml"
    run_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-19-bro-shadow",
                "workflow": "project-initialization",
                "agentsflow_version": "v0.2.0",
                "binding": ".agentsflow/workflows/project-initialization.binding.yaml",
                "status": "in_progress",
                "phase_guard": {
                    "current_phase": "raw_scan",
                    "allowed_next_phases": ["project_inventory"],
                    "allowed_outputs": ["project-raw-scan.json", "observed-facts.md"],
                    "draft_artifacts": [],
                    "forbidden_outputs_until_phase_exit": [
                        {
                            "path": "task.contract.md",
                            "until_phase": "contract",
                            "reason": "Feature contracts are not raw-scan outputs.",
                        }
                    ],
                },
                "artifacts": {
                    "root": "Docs/agentsflow/runs/2026-06-19-bro-shadow",
                    "raw_scan": "project-raw-scan.json",
                    "facts": "observed-facts.md",
                },
                "phase_evidence": {
                    "raw_scan": "project-raw-scan.json",
                },
                "phase_status": [
                    {
                        "phase": "raw_scan",
                        "status": "in_progress",
                        "artifacts": ["observed-facts.md"],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    assert validate_repo.validate_workflow_run_artifact(ROOT, run_path) == []


def test_repo_validation_checks_top_level_workflow_run_phase_guard(tmp_path) -> None:
    import shutil

    import yaml

    root = tmp_path / "repo"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__", "run-artifacts"),
    )
    run_dir = root / "Docs/agentsflow/runs/2026-06-19-phase-guard"
    run_dir.mkdir(parents=True)
    (run_dir / "run.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "run_id": "2026-06-19-phase-guard",
                "workflow": "project-initialization",
                "agentsflow_version": "v0.2.0",
                "binding": ".agentsflow/workflows/project-initialization.binding.yaml",
                "status": "in_progress",
                "phase_guard": {
                    "current_phase": "raw_scan",
                    "allowed_next_phases": ["project_inventory"],
                    "allowed_outputs": ["project-raw-scan.json"],
                    "draft_artifacts": [],
                    "forbidden_outputs_until_phase_exit": [],
                },
                "artifacts": {
                    "root": "Docs/agentsflow/runs/2026-06-19-phase-guard",
                    "raw_scan": "project-raw-scan.json",
                    "contract": "task.contract.md",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = run("scripts/validate_repo.py", "--root", str(root))
    assert result.returncode != 0
    joined = result.stdout + result.stderr
    assert "Docs/agentsflow/runs/2026-06-19-phase-guard/run.yaml" in joined
    assert "task.contract.md" in joined


def test_repository_validation_passes() -> None:
    result = run("scripts/validate_repo.py", "--root", ".")
    assert result.returncode == 0, result.stdout + result.stderr


def test_project_raw_scan_runs(tmp_path) -> None:
    out = tmp_path / "raw-scan.json"
    result = run("scripts/project_raw_scan.py", "--root", ".", "--output", str(out), "--max-files", "50")
    assert result.returncode == 0, result.stdout + result.stderr
    assert out.exists()


def test_external_reviewer_lite_mock_generates_bounded_bundle(tmp_path) -> None:
    import jsonschema

    raw = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": json.dumps(
            {
                "reviewer": {
                    "id": "generalist-claude",
                    "provider": "claude-code",
                    "role": "generalist",
                },
                "summary": "Lite review found no blockers.",
                "findings": [],
            }
        ),
    }
    raw_path = tmp_path / "mock-lite-raw.json"
    raw_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    bundle_dir = tmp_path / "lite-review"

    result = run(
        "scripts/reviewers/run_external_review_lite.py",
        "--provider",
        "claude-code",
        "--config",
        "examples/external-reviewers/claude-code/claude-code.yaml",
        "--output-dir",
        str(bundle_dir),
        "--goal",
        "Review the branch in lite mode.",
        "--run-id",
        "test-lite-run",
        "--base-ref",
        "HEAD",
        "--head-ref",
        "HEAD",
        "--include",
        "AGENTS.md",
        "--include-uncommitted",
        "--mock-response",
        str(raw_path),
        env=clean_env(),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    request_path = bundle_dir / "external-review-lite-request.json"
    report_path = bundle_dir / "reviewer-report.claude-lite.json"
    invocation_path = bundle_dir / "reviewer-invocation.claude-lite.json"
    assert request_path.exists()
    assert (bundle_dir / "artifacts" / "branch.diff").exists()
    assert (bundle_dir / "artifacts" / "git-status.txt").exists()
    assert (bundle_dir / "artifacts" / "staged.diff").exists()
    assert (bundle_dir / "artifacts" / "unstaged.diff").exists()
    assert (bundle_dir / "artifacts" / "AGENTS.md").exists()

    request = json.loads(request_path.read_text(encoding="utf-8"))
    request_schema = json.loads((ROOT / "schemas/external-review-lite-request.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(request_schema).validate(request)
    assert request["context_mode"] == "lite"
    assert request["dirty_worktree"]["policy"] == "include_staged_and_unstaged_diffs"
    if request["dirty_worktree"]["status"] == "dirty":
        assert request["material_change_id"].startswith(request["branch"]["head_commit"] + "+dirty-")
        assert request["dirty_worktree"]["material_change_id_basis_hash"].startswith("sha256:")
    assert request["artifacts"][0]["kind"] == "branch_diff"
    assert any(artifact.get("source_path") == "AGENTS.md" for artifact in request["artifacts"])

    normalized = json.loads(report_path.read_text(encoding="utf-8"))
    assert normalized["reviewer"]["id"] == "generalist-claude"
    assert normalized["summary"] == "Lite review found no blockers."
    assert normalized["normalization"]["normalized_by"] == "scripts/reviewers/run_external_review_lite.py"

    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation_schema = json.loads(
        (ROOT / "schemas/external-review-lite-invocation.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(invocation_schema).validate(invocation)
    effective_config_path = bundle_dir / "effective-provider-config.json"
    assert effective_config_path.exists()
    effective_config = json.loads(effective_config_path.read_text(encoding="utf-8"))
    assert invocation["context_mode"] == "lite"
    assert invocation["wrapper"] == "scripts/reviewers/run_external_review_lite.py"
    assert invocation["prompt_transport"] == "file"
    assert invocation["tools"] == "Read"
    assert invocation["max_turns"] == 42
    assert invocation["sandbox_mode"] == "require_escalated"
    assert invocation["effective_provider_config_path"] == str(effective_config_path)
    assert invocation["effective_provider_config_hash"] != invocation["provider_config_hash"]
    assert effective_config["permissions"]["read_packet_only"] is False
    assert effective_config["permissions"]["read_review_bundle_only"] is True
    assert "review_packet_schema" not in effective_config["inputs"]
    assert effective_config["inputs"]["review_request_schema"] == "schemas/external-review-lite-request.schema.json"
    assert (
        effective_config["outputs"]["invocation_metadata_schema"]
        == "schemas/external-review-lite-invocation.schema.json"
    )
    assert invocation["raw_output_disposition"]["stored"] is True
    assert invocation["raw_output_disposition"]["kind"] == "raw_output"
    assert invocation["review_request_hash"] == invocation["input_hash"]


def test_external_reviewer_lite_documented_mock_smoke_uses_default_reviewer(tmp_path) -> None:
    bundle_dir = tmp_path / "external-review-lite"

    def run_documented_smoke():
        return run(
            "scripts/reviewers/run_external_review_lite.py",
            "--provider",
            "claude-code",
            "--config",
            "examples/external-reviewers/claude-code/claude-code.yaml",
            "--output-dir",
            str(bundle_dir),
            "--goal",
            "Smoke-test external reviewer normalization.",
            "--run-id",
            "external-reviewer-smoke",
            "--base-ref",
            "HEAD",
            "--head-ref",
            "HEAD",
            "--include-uncommitted",
            "--mock-response",
            "examples/external-reviewers/claude-code/mock-raw-output.json",
            "--replace-output-dir",
            env=clean_env(),
        )

    result = run_documented_smoke()

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((bundle_dir / "reviewer-report.claude-lite.json").read_text(encoding="utf-8"))
    invocation = json.loads((bundle_dir / "reviewer-invocation.claude-lite.json").read_text(encoding="utf-8"))
    assert report["reviewer"]["id"] == "generalist-claude"
    assert report["reviewer"]["role"] == "generalist"
    assert invocation["reviewer_role"] == "generalist"

    rerun = run_documented_smoke()

    assert rerun.returncode == 0, rerun.stdout + rerun.stderr


def test_external_reviewer_lite_replace_output_dir_requires_prior_lite_bundle(tmp_path) -> None:
    bundle_dir = tmp_path / "not-a-lite-bundle"
    bundle_dir.mkdir()
    (bundle_dir / "important.txt").write_text("keep", encoding="utf-8")

    result = run(
        "scripts/reviewers/run_external_review_lite.py",
        "--provider",
        "claude-code",
        "--config",
        "examples/external-reviewers/claude-code/claude-code.yaml",
        "--output-dir",
        str(bundle_dir),
        "--replace-output-dir",
        "--goal",
        "Review the branch in lite mode.",
        "--run-id",
        "test-lite-run",
        "--base-ref",
        "HEAD",
        "--head-ref",
        "HEAD",
        "--include-uncommitted",
        "--mock-response",
        str(tmp_path / "missing.json"),
        env=clean_env(),
    )

    assert result.returncode == 2
    assert "Refusing to delete" in result.stderr
    assert (bundle_dir / "important.txt").exists()


def test_external_reviewer_lite_live_relative_output_dir_uses_readable_prompt_path(tmp_path) -> None:
    import jsonschema
    import shutil

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_claude = fake_bin / "claude"
    fake_claude.write_text(
        """#!/usr/bin/env python3
import json
import pathlib
import sys

prompt_arg = sys.argv[2]
prompt_path = pathlib.Path(prompt_arg.rsplit(": ", 1)[-1])
if not prompt_path.is_file():
    print(json.dumps({"type": "result", "subtype": "error", "is_error": True, "result": f"missing prompt: {prompt_path}"}))
    sys.exit(1)
report = {
    "reviewer": {"id": "generalist-claude", "provider": "claude-code", "role": "generalist"},
    "summary": "Lite live fake review found no blockers.",
    "findings": [],
}
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": json.dumps(report)}))
""",
        encoding="utf-8",
    )
    fake_claude.chmod(0o755)
    output_rel = Path("run-artifacts/agentsflow/test-lite-relative") / tmp_path.name / "external-review-lite"
    shutil.rmtree(ROOT / output_rel, ignore_errors=True)
    env = clean_env()
    env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")

    try:
        result = run(
            "scripts/reviewers/run_external_review_lite.py",
            "--provider",
            "claude-code",
            "--config",
            "examples/external-reviewers/claude-code/claude-code.yaml",
            "--output-dir",
            output_rel.as_posix(),
            "--goal",
            "Review the branch in lite mode.",
            "--run-id",
            "test-lite-run",
            "--base-ref",
            "HEAD",
            "--head-ref",
            "HEAD",
            "--include-uncommitted",
            env=env,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        invocation_path = ROOT / output_rel / "reviewer-invocation.claude-lite.json"
        invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
        invocation_schema = json.loads(
            (ROOT / "schemas/external-review-lite-invocation.schema.json").read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(invocation_schema).validate(invocation)
        assert invocation["execution_mode"] == "real"
        assert invocation["exit_code"] == 0
        assert invocation["effective_provider_config_hash"] != invocation["provider_config_hash"]
        assert invocation["raw_output_disposition"]["stored"] is True
    finally:
        shutil.rmtree(ROOT / output_rel.parent, ignore_errors=True)


def test_external_reviewer_lite_malformed_output_preserves_failure_raw_hash(tmp_path) -> None:
    import hashlib
    import jsonschema

    raw = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": "not reviewer report json",
    }
    raw_path = tmp_path / "mock-lite-malformed-raw.json"
    raw_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    bundle_dir = tmp_path / "lite-review-malformed"

    result = run(
        "scripts/reviewers/run_external_review_lite.py",
        "--provider",
        "claude-code",
        "--config",
        "examples/external-reviewers/claude-code/claude-code.yaml",
        "--output-dir",
        str(bundle_dir),
        "--goal",
        "Review the branch in lite mode.",
        "--run-id",
        "test-lite-run",
        "--base-ref",
        "HEAD",
        "--head-ref",
        "HEAD",
        "--include-uncommitted",
        "--mock-response",
        str(raw_path),
        env=clean_env(),
    )

    assert result.returncode == 2
    invocation_path = bundle_dir / "reviewer-invocation.claude-lite.json"
    raw_output_path = bundle_dir / "reviewer-report.claude-lite.raw.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation_schema = json.loads(
        (ROOT / "schemas/external-review-lite-invocation.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(invocation_schema).validate(invocation)
    assert invocation["failure_stage"] == "provider_output_processing"
    assert invocation["raw_output_path"] == str(raw_output_path)
    assert invocation["raw_output_disposition"]["kind"] == "raw_output"
    assert invocation["raw_output_hash"] != "sha256:" + "0" * 64
    assert invocation["raw_output_hash"] == "sha256:" + hashlib.sha256(raw_output_path.read_bytes()).hexdigest()


def test_external_reviewer_lite_malformed_output_without_raw_persistence_records_diagnostic(tmp_path) -> None:
    import jsonschema

    raw = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": "No findings.",
    }
    raw_path = tmp_path / "mock-lite-malformed-raw.json"
    raw_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    config_path = tmp_path / "claude-code-no-raw.yaml"
    config_path.write_text(
        (ROOT / "examples/external-reviewers/claude-code/claude-code.yaml")
        .read_text(encoding="utf-8")
        .replace("preserve_raw_output: true", "preserve_raw_output: false"),
        encoding="utf-8",
    )
    bundle_dir = tmp_path / "lite-review-malformed-no-raw"

    result = run(
        "scripts/reviewers/run_external_review_lite.py",
        "--provider",
        "claude-code",
        "--config",
        str(config_path),
        "--output-dir",
        str(bundle_dir),
        "--goal",
        "Review the branch in lite mode.",
        "--run-id",
        "test-lite-run",
        "--base-ref",
        "HEAD",
        "--head-ref",
        "HEAD",
        "--include-uncommitted",
        "--mock-response",
        str(raw_path),
        env=clean_env(),
    )

    assert result.returncode == 2
    invocation_path = bundle_dir / "reviewer-invocation.claude-lite.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation_schema = json.loads(
        (ROOT / "schemas/external-review-lite-invocation.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(invocation_schema).validate(invocation)
    assert invocation["failure_stage"] == "provider_output_processing"
    assert invocation["raw_output_path"] == ""
    assert invocation["raw_output_disposition"]["kind"] == "omission_reason"
    diagnostic = invocation["provider_output_diagnostic"]["claude_envelope"]
    assert diagnostic["result_type"] == "str"
    assert diagnostic["result_length"] == len("No findings.")
    assert diagnostic["embedded_reviewer_report_json"] is False


def test_external_reviewer_lite_provider_exception_writes_failure_invocation(tmp_path) -> None:
    import jsonschema

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_claude = fake_bin / "claude"
    fake_claude.write_text("#!/bin/sh\nsleep 5\n", encoding="utf-8")
    fake_claude.chmod(0o755)
    config_path = tmp_path / "claude-code-timeout.yaml"
    config_path.write_text(
        (ROOT / "examples/external-reviewers/claude-code/claude-code.yaml")
        .read_text(encoding="utf-8")
        .replace("timeout_seconds: 1500", "timeout_seconds: 0"),
        encoding="utf-8",
    )
    bundle_dir = tmp_path / "external-review-lite"
    env = clean_env()
    env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")

    result = run(
        "scripts/reviewers/run_external_review_lite.py",
        "--provider",
        "claude-code",
        "--config",
        str(config_path),
        "--output-dir",
        str(bundle_dir),
        "--goal",
        "Review the branch in lite mode.",
        "--run-id",
        "test-lite-run",
        "--base-ref",
        "HEAD",
        "--head-ref",
        "HEAD",
        "--include-uncommitted",
        env=env,
    )

    assert result.returncode == 2
    invocation_path = bundle_dir / "reviewer-invocation.claude-lite.json"
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    invocation_schema = json.loads(
        (ROOT / "schemas/external-review-lite-invocation.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(invocation_schema).validate(invocation)
    assert invocation["failure_stage"] == "provider_invocation_exception"
    assert invocation["command"] == "provider-call-not-completed"
    assert invocation["raw_output_disposition"]["kind"] == "omission_reason"
    assert invocation["raw_output_hash"] == "sha256:" + "0" * 64


def test_claude_code_provider_command_defaults_model_and_effort() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "scripts" / "reviewers"))
    from providers import claude_code  # noqa: PLC0415

    cmd = claude_code.build_command(
        {
            "execution": {
                "command": "claude",
                "output_format": "json",
                "permission_mode": "default",
                "max_turns": 3,
                "no_session_persistence": True,
                "use_bare_mode": False,
            }
        },
        "prompt",
    )
    assert "--model" in cmd
    assert cmd[cmd.index("--model") + 1] == "opus"
    assert "--effort" in cmd
    assert cmd[cmd.index("--effort") + 1] == "max"
    assert "--tools" in cmd
    assert cmd[cmd.index("--tools") + 1] == ""


def test_claude_code_provider_defaults_timeout_to_900_seconds(monkeypatch) -> None:
    import sys
    from types import SimpleNamespace

    sys.path.insert(0, str(ROOT / "scripts" / "reviewers"))
    from providers import claude_code  # noqa: PLC0415

    captured: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["timeout"] = kwargs.get("timeout")
        return SimpleNamespace(stdout="{}", stderr="", returncode=0)

    monkeypatch.setattr(claude_code.subprocess, "run", fake_run)
    result = claude_code.invoke({"execution": {"command": "claude"}}, "prompt", cwd=ROOT)
    assert result.exit_code == 0
    assert captured["timeout"] == 900
