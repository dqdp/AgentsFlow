from __future__ import annotations

import os
import subprocess
import sys
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
    import subprocess, sys
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

    invalid_role = json.loads((ROOT / "templates/project-assessment.role.json").read_text(encoding="utf-8"))
    invalid_role["role"] = "generalist"
    assert list(validator.iter_errors(invalid_role))


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
    validator.validate(packet)

    focused = copy.deepcopy(packet)
    focused["reviewer_instance_id"] = "adversarial"
    focused["reviewer_role"] = "adversarial"
    assert list(validator.iter_errors(focused))

    focused["focus_zone"] = {"primary_focus": ["false completion", "bypasses"]}
    validator.validate(focused)


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


def test_collision_control_prompt_contract_requires_non_null_batch() -> None:
    import copy
    import json

    import jsonschema
    import yaml

    schema = json.loads((ROOT / "schemas/review-prompt-contract.schema.json").read_text(encoding="utf-8"))
    contract = yaml.safe_load((ROOT / "templates/review-prompt-contract.yaml").read_text(encoding="utf-8"))
    broken = copy.deepcopy(contract)
    broken["identity"]["review_profile"] = "collision-control"
    broken["identity"]["composition"] = "control"
    broken["identity"]["primary_gate"] = False
    broken["collision_control"] = None

    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(broken))
    assert errors
    assert "not of type 'object'" in "\n".join(error.message for error in errors)


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
    temp_report.write_text(json.dumps(undeclared_command), encoding="utf-8")
    try:
        errors = validate_repo.validate_evidence_probe_report_artifact(ROOT, temp_report)
    finally:
        temp_report.unlink(missing_ok=True)
    assert errors
    assert "not declared in allowed_instruments" in "\n".join(errors)


def test_review_prompt_contract_rejects_missing_shared_hash() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts" / "reviewers"))
    import run_external_reviewer  # noqa: PLC0415

    contract = yaml.safe_load(
        (
            ROOT
            / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-prompt-contract.yaml"
        ).read_text(encoding="utf-8")
    )
    broken = copy.deepcopy(contract)
    broken["rendered_prompts"][0].pop("shared_prompt_content_hash")

    try:
        run_external_reviewer.validate_prompt_contract_invariants(broken)
    except ValueError as exc:
        assert "shared_prompt_content_hash" in str(exc)
    else:
        raise AssertionError("missing shared prompt hash was accepted")


def test_review_prompt_contract_rejects_run_artifact_drift() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = (
        ROOT
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-prompt-contract.yaml"
    )
    contract = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(contract)
    broken["rendered_prompts"][0]["shared_packet_content_hash"] = "sha256:" + "0" * 64

    errors = validate_repo.validate_review_prompt_contract_invariants(ROOT, path, broken, True)
    assert errors
    assert "shared_packet_content_hash" in "\n".join(errors)


def test_review_prompt_contract_rejects_missing_run_references() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = (
        ROOT
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-prompt-contract.yaml"
    )
    contract = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(contract)
    broken["rendered_prompts"][0]["prompt_path"] = "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-prompts/missing.md"

    errors = validate_repo.validate_review_prompt_contract_run_references(ROOT, path, broken)
    assert errors
    assert "prompt_path does not exist" in "\n".join(errors)


def test_review_prompt_contract_rejects_rendered_packet_hash_drift() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = (
        ROOT
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-prompt-contract.yaml"
    )
    contract = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(contract)
    broken["rendered_prompts"][0]["packet_hash"] = "sha256:" + "0" * 64

    errors = validate_repo.validate_review_prompt_contract_run_references(ROOT, path, broken)
    assert errors
    assert "rendered_prompts[0].packet_hash" in "\n".join(errors)


def test_review_packet_must_match_contract_reviewer_and_path(tmp_path) -> None:
    import json
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    source = (
        ROOT
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-packets/generalist-a.json"
    )
    copied = tmp_path / "generalist-a.json"
    copied.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    errors = validate_repo.validate_review_packet_artifact(ROOT, copied, True)
    assert errors
    assert "matching reviewer and path" in "\n".join(errors)

    packet = json.loads(source.read_text(encoding="utf-8"))
    packet["reviewer_instance_id"] = "generalist-b"
    wrong_reviewer = tmp_path / "wrong-reviewer.json"
    wrong_reviewer.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    errors = validate_repo.validate_review_packet_artifact(ROOT, wrong_reviewer, True)
    assert errors
    assert "matching reviewer and path" in "\n".join(errors)


def test_review_prompt_contract_allows_reviewed_artifact_subject() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = (
        ROOT
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-prompt-contract.yaml"
    )
    contract = yaml.safe_load(path.read_text(encoding="utf-8"))
    with_artifact = copy.deepcopy(contract)
    with_artifact["inputs"]["reviewed_artifact"] = with_artifact["inputs"].pop("task_contract")

    errors = validate_repo.validate_review_prompt_contract_run_references(ROOT, path, with_artifact)
    assert not errors

    without_subject = copy.deepcopy(contract)
    without_subject["inputs"].pop("task_contract")
    errors = validate_repo.validate_review_prompt_contract_run_references(ROOT, path, without_subject)
    assert errors
    assert "one of inputs.task_contract" in "\n".join(errors)


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


def test_v02_review_cycle_requires_materiality_policy() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    path = ROOT / "workflows/big-feature-contract-first/workflow.yaml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(workflow)
    broken["review_cycle"].pop("materiality_classification")

    errors = validate_repo.validate_v02_review_control_materiality_policy(path, broken)
    assert errors
    assert "review_cycle.materiality_classification is required" in "\n".join(errors)

    broken_missing_token = copy.deepcopy(workflow)
    broken_missing_token["review_cycle"]["do_not_rerun_on"].remove(
        "nonblocking_findings_with_non_material_fixes_only"
    )
    broken_missing_token["review_cycle"].pop("materiality_classification")
    errors = validate_repo.validate_v02_review_control_materiality_policy(path, broken_missing_token)
    assert "do_not_rerun_on must include nonblocking_findings_with_non_material_fixes_only" in "\n".join(errors)
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
    prepare_policy = workflow["intent_mode_phase_policy"]["prepare-workflow"]
    assert (
        prepare_policy["target_workflow_context_decision_packet"]
        == "conditional_when_target_workflow_context_or_material_design_decision_is_missing"
    )
    target_phase = next(
        phase
        for phase in workflow["phases"]
        if phase.get("id") == "target_workflow_context_decision_packet"
    )
    required_decision_categories = {
        "scope",
        "adr",
        "risk",
        "contract",
        "gate",
        "review",
        "evidence",
        "authority",
        "workflow-design",
    }
    assert set(target_phase["decision_categories"]) == required_decision_categories

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
    ] = "conditional_when_target_workflow_context_or_material_design_decision_is_missing"
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_prepare_policy)
    joined = "\n".join(errors)
    assert "target_workflow_context_decision_packet" in joined
    assert "must not use operating_decisions_interview" in joined

    broken_prepare_policy_value = copy.deepcopy(workflow)
    broken_prepare_policy_value["intent_mode_phase_policy"]["prepare-workflow"][
        "target_workflow_context_decision_packet"
    ] = "conditional_when_target_workflow_policy_is_missing"
    errors = validate_repo.validate_project_initialization_intent_mode_policy(path, broken_prepare_policy_value)
    assert "missing context or material design decisions" in "\n".join(errors)

    broken_target_design_scope = copy.deepcopy(workflow)
    for phase in broken_target_design_scope["phases"]:
        if phase.get("id") == "target_workflow_context_decision_packet":
            phase["decision_categories"].remove("authority")
    errors = validate_repo.validate_project_initialization_operating_decisions(path, broken_target_design_scope)
    assert "target_workflow_context_decision_packet decision_categories missing: authority" in "\n".join(errors)

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


def test_target_workflow_readiness_gate_requires_documentation_disposition() -> None:
    import yaml

    gate = yaml.safe_load((ROOT / "gates/target_workflow_readiness_gate.yaml").read_text(encoding="utf-8"))
    required_decision_categories = {
        "scope",
        "adr",
        "risk",
        "contract",
        "gate",
        "review",
        "evidence",
        "authority",
        "workflow-design",
    }
    assert "project-documentation-disposition.yaml" in gate["inputs"]
    assert any(
        "project-documentation-disposition.yaml" in evidence
        for evidence in gate["required_evidence"]
    )
    assert any("existing project policy/workflow binding evidence" in item for item in gate["inputs"])
    assert any("target workflow preflight findings" in item for item in gate["inputs"])
    assert any("human decision packet" in item for item in gate["inputs"])
    assert any("existing project policy/workflow binding evidence" in item for item in gate["required_evidence"])
    assert any("human decision packet" in item for item in gate["required_evidence"])
    assert set(gate["decision_categories"]) == required_decision_categories
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

    broken_categories = copy.deepcopy(gate)
    broken_categories["decision_categories"].remove("evidence")
    errors = validate_repo.validate_gate_manifest(ROOT, path, broken_categories)
    assert "target_workflow_readiness_gate decision_categories missing: evidence" in "\n".join(errors)

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
    assert "max_review_cycles must be an integer" in (result.stdout + result.stderr)


def test_repo_validation_checks_evidence_probe_run_artifacts(tmp_path) -> None:
    import json
    import shutil

    root = tmp_path / "repo"
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"))
    run_dir = root / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator"
    report = json.loads((root / "templates/evidence-probe-report.json").read_text(encoding="utf-8"))
    report["commands_run"][0]["instrument_id"] = "not-declared"
    (run_dir / "evidence-probe-report.invalid.json").write_text(json.dumps(report), encoding="utf-8")

    result = run("scripts/validate_repo.py", "--root", str(root))
    assert result.returncode != 0
    assert "not declared in allowed_instruments" in (result.stdout + result.stderr)


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
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"))
    workflow = root / "workflows/big-feature-contract-first/workflow.yaml"
    workflow.write_text(
        workflow.read_text(encoding="utf-8") + "\n_duplicate_test: one\n_duplicate_test: two\n",
        encoding="utf-8",
    )

    result = run("scripts/validate_repo.py", "--root", str(root))
    assert result.returncode != 0
    assert "duplicate YAML key" in (result.stdout + result.stderr)


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


def test_workflow_run_phase_guard_checks_review_and_evidence_phase_status_keys(
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
                    "allowed_outputs": ["human-questions.yaml"],
                    "draft_artifacts": [],
                    "forbidden_outputs_until_phase_exit": [],
                },
                "artifacts": {
                    "root": "Docs/agentsflow/runs/2026-06-19-bro-shadow",
                    "human_questions": "human-questions.yaml",
                },
                "phase_status": [
                    {
                        "phase": "operating_context_preflight",
                        "review_prompt_contract": "review-prompt-contract.yaml",
                        "review_packets": ["review-packets/generalist-a.json"],
                        "reviewer_report_summaries": ["reviewer-report.generalist-a.md"],
                        "evidence_bundle": "evidence-report.md",
                        "report_summaries": ["final-report.md"],
                        "phase_output": "task.contract.md",
                        "red_capture_evidence": "red-capture-gate-report.md",
                        "task_contract": "task.contract.md",
                        "bundle": "task.contract.md",
                        "ref": "task.contract.md",
                        "artifact_refs": ["task.contract.md"],
                        "output_refs": ["plan.md"],
                        "red_capture_evidence_bundle": "red-capture-gate-report.md",
                        "target_workflow_context_decision_packet": (
                            "target-workflow-context-decision-packet.yaml"
                        ),
                        "review_packet_summary": "review-packet-summary.md",
                        "technical_plan": "plan.md",
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
    assert "phase_status[0].review_prompt_contract path review-prompt-contract.yaml" in joined
    assert "phase_status[0].review_packets[0] path review-packets/generalist-a.json" in joined
    assert "phase_status[0].reviewer_report_summaries[0] path reviewer-report.generalist-a.md" in joined
    assert "phase_status[0].evidence_bundle path evidence-report.md" in joined
    assert "phase_status[0].report_summaries[0] path final-report.md" in joined
    assert "phase_status[0].phase_output path task.contract.md" in joined
    assert "phase_status[0].red_capture_evidence path red-capture-gate-report.md" in joined
    assert "phase_status[0].task_contract path task.contract.md" in joined
    assert "phase_status[0].bundle path task.contract.md" in joined
    assert "phase_status[0].ref path task.contract.md" in joined
    assert "phase_status[0].artifact_refs[0] path task.contract.md" in joined
    assert "phase_status[0].output_refs[0] path plan.md" in joined
    assert (
        "phase_status[0].red_capture_evidence_bundle path red-capture-gate-report.md"
        in joined
    )
    assert (
        "phase_status[0].target_workflow_context_decision_packet path "
        "target-workflow-context-decision-packet.yaml"
    ) in joined
    assert "phase_status[0].review_packet_summary path review-packet-summary.md" in joined
    assert "phase_status[0].technical_plan path plan.md" in joined


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
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"))
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


def test_external_reviewer_wrapper_mock_passes(tmp_path) -> None:
    out = tmp_path / "reviewer-report.claude-architecture.json"
    result = run(
        "scripts/reviewers/run_external_reviewer.py",
        "--provider", "claude-code",
        "--config", "examples/external-reviewers/claude-code/claude-code.yaml",
        "--input", "examples/external-reviewers/claude-code/review-packet.architecture.json",
        "--mock-response", "examples/external-reviewers/claude-code/mock-raw-output.json",
        "--output", str(out),
        env=clean_env(),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert out.exists()


def test_external_reviewer_wrapper_rejects_invalid_packet_schema(tmp_path) -> None:
    import json

    packet = json.loads(
        (ROOT / "examples/external-reviewers/claude-code/review-packet.architecture.json").read_text(
            encoding="utf-8"
        )
    )
    packet["review_profile"] = "garbage"
    packet_path = tmp_path / "invalid-review-packet.json"
    packet_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    out = tmp_path / "reviewer-report.json"

    result = run(
        "scripts/reviewers/run_external_reviewer.py",
        "--provider", "claude-code",
        "--config", "examples/external-reviewers/claude-code/claude-code.yaml",
        "--input", str(packet_path),
        "--mock-response", "examples/external-reviewers/claude-code/mock-raw-output.json",
        "--output", str(out),
        env=clean_env(),
    )
    assert result.returncode != 0
    assert "review packet schema validation failed" in (result.stdout + result.stderr)


def test_external_reviewer_wrapper_rejects_unlisted_packet_path(tmp_path) -> None:
    packet_path = tmp_path / "review-packet.architecture.json"
    packet_path.write_text(
        (ROOT / "examples/external-reviewers/claude-code/review-packet.architecture.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    out = tmp_path / "reviewer-report.json"

    result = run(
        "scripts/reviewers/run_external_reviewer.py",
        "--provider", "claude-code",
        "--config", "examples/external-reviewers/claude-code/claude-code.yaml",
        "--input", str(packet_path),
        "--mock-response", "examples/external-reviewers/claude-code/mock-raw-output.json",
        "--output", str(out),
        env=clean_env(),
    )
    assert result.returncode != 0
    assert "matching reviewer and path" in (result.stdout + result.stderr)


def test_external_reviewer_wrapper_rejects_duplicate_packet_contract_entries(tmp_path) -> None:
    import copy
    import json

    import yaml

    packet = json.loads(
        (ROOT / "examples/external-reviewers/claude-code/review-packet.architecture.json").read_text(
            encoding="utf-8"
        )
    )
    packet_path = tmp_path / "review-packet.architecture.json"
    contract_path = tmp_path / "review-prompt-contract.architecture.yaml"
    packet["review_prompt_contract"]["path"] = str(contract_path)
    packet_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")

    contract = yaml.safe_load(
        (ROOT / "examples/external-reviewers/claude-code/review-prompt-contract.architecture.yaml").read_text(
            encoding="utf-8"
        )
    )
    contract["inputs"]["review_packets"][0]["path"] = str(packet_path)
    contract["inputs"]["review_packets"].insert(1, copy.deepcopy(contract["inputs"]["review_packets"][0]))
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    out = tmp_path / "reviewer-report.json"

    result = run(
        "scripts/reviewers/run_external_reviewer.py",
        "--provider", "claude-code",
        "--config", "examples/external-reviewers/claude-code/claude-code.yaml",
        "--input", str(packet_path),
        "--mock-response", "examples/external-reviewers/claude-code/mock-raw-output.json",
        "--output", str(out),
        env=clean_env(),
    )
    assert result.returncode != 0
    assert "duplicate entries" in (result.stdout + result.stderr)


def test_external_reviewer_wrapper_rejects_unsafe_permission_mode(tmp_path) -> None:
    import yaml

    config = yaml.safe_load(
        (ROOT / "examples/external-reviewers/claude-code/claude-code.yaml").read_text(
            encoding="utf-8"
        )
    )
    config["execution"]["permission_mode"] = "dangerously-allow-edits"
    config_path = tmp_path / "claude-code.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    out = tmp_path / "reviewer-report.json"

    result = run(
        "scripts/reviewers/run_external_reviewer.py",
        "--provider", "claude-code",
        "--config", str(config_path),
        "--input", "examples/external-reviewers/claude-code/review-packet.architecture.json",
        "--mock-response", "examples/external-reviewers/claude-code/mock-raw-output.json",
        "--output", str(out),
        env=clean_env(),
    )
    assert result.returncode != 0
    assert "permission_mode: plan" in (result.stdout + result.stderr)


def test_external_reviewer_wrapper_rejects_non_claude_command(tmp_path) -> None:
    import yaml

    config = yaml.safe_load(
        (ROOT / "examples/external-reviewers/claude-code/claude-code.yaml").read_text(
            encoding="utf-8"
        )
    )
    config["execution"]["command"] = "not-claude"
    config_path = tmp_path / "claude-code.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    out = tmp_path / "reviewer-report.json"

    result = run(
        "scripts/reviewers/run_external_reviewer.py",
        "--provider", "claude-code",
        "--config", str(config_path),
        "--input", "examples/external-reviewers/claude-code/review-packet.architecture.json",
        "--mock-response", "examples/external-reviewers/claude-code/mock-raw-output.json",
        "--output", str(out),
        env=clean_env(),
    )
    assert result.returncode != 0
    assert "execution.command: claude" in (result.stdout + result.stderr)


def test_external_reviewer_wrapper_rejects_invalid_finding_severity(tmp_path) -> None:
    import json

    raw = json.loads(
        (ROOT / "examples/external-reviewers/claude-code/mock-raw-output.json").read_text(
            encoding="utf-8"
        )
    )
    raw["findings"] = [
        {
            "id": "BAD-SEVERITY",
            "severity": "BLOCKER",
            "category": "test",
            "title": "Invalid severity",
            "evidence": [],
        }
    ]
    raw_path = tmp_path / "bad-raw-output.json"
    raw_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    out = tmp_path / "reviewer-report.json"

    result = run(
        "scripts/reviewers/run_external_reviewer.py",
        "--provider", "claude-code",
        "--config", "examples/external-reviewers/claude-code/claude-code.yaml",
        "--input", "examples/external-reviewers/claude-code/review-packet.architecture.json",
        "--mock-response", str(raw_path),
        "--output", str(out),
        env=clean_env(),
    )
    assert result.returncode != 0
    assert "invalid severity" in (result.stdout + result.stderr)
    invocation = out.with_suffix(".invocation.json")
    assert invocation.exists()
    assert "provider_output_processing" in invocation.read_text(encoding="utf-8")


def test_external_reviewer_wrapper_rejects_live_example_scope(tmp_path) -> None:
    out = tmp_path / "reviewer-report.json"
    result = run(
        "scripts/reviewers/run_external_reviewer.py",
        "--provider", "claude-code",
        "--config", "examples/external-reviewers/claude-code/claude-code.yaml",
        "--input", "examples/external-reviewers/claude-code/review-packet.architecture.json",
        "--output", str(out),
        env=clean_env(),
    )
    assert result.returncode != 0
    assert "artifact_scope: run" in (result.stdout + result.stderr)


def test_external_reviewer_wrapper_rejects_forbidden_env(tmp_path) -> None:
    out = tmp_path / "reviewer-report.json"
    for env_name in FORBIDDEN_CLAUDE_ENV:
        env = clean_env()
        env[env_name] = "" if env_name == "ANTHROPIC_API_KEY" else "forbidden"
        result = run(
            "scripts/reviewers/run_external_reviewer.py",
            "--provider", "claude-code",
            "--config", "examples/external-reviewers/claude-code/claude-code.yaml",
            "--input", "examples/external-reviewers/claude-code/review-packet.architecture.json",
            "--mock-response", "examples/external-reviewers/claude-code/mock-raw-output.json",
            "--output", str(out),
            env=env,
        )
        assert result.returncode != 0
        assert env_name in (result.stdout + result.stderr)
