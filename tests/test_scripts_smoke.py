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
    assert "missing project gate binding(s): verification_gate" in (result.stdout + result.stderr)


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


def test_project_inventory_validation_passes() -> None:
    result = run("scripts/validate_project_inventory.py", "--inventory", "examples/project-initialization/project-inventory.json")
    assert result.returncode == 0, result.stdout + result.stderr


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


def test_review_packet_schema_allows_plus_focused_baseline_without_focus_zone() -> None:
    import json

    import jsonschema

    schema = json.loads((ROOT / "schemas/review-packet.schema.json").read_text(encoding="utf-8"))
    packet = json.loads(
        (
            ROOT
            / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-packets/generalist-a.json"
        ).read_text(encoding="utf-8")
    )
    packet["review_profile"] = "homogeneous-plus-focused"
    packet["composition"] = "homogeneous-plus-focused"
    jsonschema.Draft202012Validator(schema).validate(packet)


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


def test_mvp_review_phase_requires_top_level_review_policy() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    workflow = yaml.safe_load((ROOT / "workflows/review-only-fusion/workflow.yaml").read_text(encoding="utf-8"))
    broken = copy.deepcopy(workflow)
    broken.pop("review", None)

    errors = validate_repo.validate_mvp_review_phase_policy(
        ROOT / "workflows/review-only-fusion/workflow.yaml",
        broken,
    )
    assert errors
    assert "top-level review policy" in errors[0]


def test_mvp_review_phase_requires_required_gate_order() -> None:
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


def test_mvp_review_gate_order_rejects_wrong_phase_kinds() -> None:
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
