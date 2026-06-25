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


def write_minimal_review_preparation(path: Path, contract_path: Path, root: Path | None = None) -> None:
    import hashlib
    import yaml

    base = root.resolve() if root is not None else ROOT

    def resolve_ref(ref: object) -> Path:
        ref_path = Path(str(ref))
        if ref_path.is_absolute():
            return ref_path
        return base / ref_path

    def rel_or_abs(ref_path: Path) -> str:
        if root is None:
            return str(ref_path.resolve())
        try:
            return ref_path.resolve().relative_to(base).as_posix()
        except ValueError:
            return str(ref_path.resolve())

    def sha(ref_path: Path) -> str:
        return "sha256:" + hashlib.sha256(ref_path.read_bytes()).hexdigest()

    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    assignments = contract.get("reviewer_assignments", []) or []
    assignment_reviewers = [str(item.get("reviewer")) for item in assignments if isinstance(item, dict)]
    inputs = contract.setdefault("inputs", {})
    packet_entries = {
        str(item.get("reviewer")): item
        for item in inputs.get("review_packets", []) or []
        if isinstance(item, dict) and item.get("reviewer")
    }
    rendered_prompts = {
        str(item.get("reviewer")): item
        for item in contract.get("rendered_prompts", []) or []
        if isinstance(item, dict) and item.get("reviewer")
    }
    prompt_dir = contract_path.parent / "review-prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    for reviewer in assignment_reviewers:
        if reviewer not in rendered_prompts:
            prompt_path = prompt_dir / f"{reviewer}.md"
            prompt_path.write_text(f"Review prompt for {reviewer}.\n", encoding="utf-8")
            prompt_ref = rel_or_abs(prompt_path)
            rendered_prompts[reviewer] = {
                "reviewer": reviewer,
                "prompt_path": prompt_ref,
            }
    contract["rendered_prompts"] = [rendered_prompts[reviewer] for reviewer in assignment_reviewers if reviewer in rendered_prompts]
    for prompt in contract["rendered_prompts"]:
        prompt_path = resolve_ref(prompt["prompt_path"])
        prompt["prompt_hash"] = sha(prompt_path)
        prompt.setdefault("packet_hash", "sha256:" + "0" * 64)
        prompt.setdefault("schema_hash", "sha256:" + "0" * 64)
        prompt.setdefault("rubric_hash", "sha256:" + "0" * 64)
        prompt.setdefault("role_contract_hash", "sha256:" + "0" * 64)
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    ref = str(contract_path.resolve())
    if root is not None:
        try:
            ref = contract_path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    contract_hash = sha(contract_path)
    review_packets = []
    for reviewer in assignment_reviewers:
        packet_entry = packet_entries.get(reviewer)
        packet_ref = packet_entry.get("path") if packet_entry else next(
            item.get("packet_path") for item in assignments if item.get("reviewer") == reviewer
        )
        packet_path = resolve_ref(packet_ref)
        review_packets.append(
            {
                "reviewer": reviewer,
                "path": str(packet_ref),
                "hash": sha(packet_path),
                **(
                    {"shared_packet_content_hash": packet_entry["shared_packet_content_hash"]}
                    if packet_entry and packet_entry.get("shared_packet_content_hash")
                    else {}
                ),
            }
        )
    rendered_prompt_entries = []
    for reviewer in assignment_reviewers:
        prompt = rendered_prompts[reviewer]
        prompt_path = resolve_ref(prompt["prompt_path"])
        rendered_prompt_entries.append(
            {
                "reviewer": reviewer,
                "path": str(prompt["prompt_path"]),
                "hash": sha(prompt_path),
                "packet_hash": prompt.get("packet_hash", "sha256:" + "0" * 64),
                "schema_hash": prompt.get("schema_hash", "sha256:" + "0" * 64),
                "rubric_hash": prompt.get("rubric_hash", "sha256:" + "0" * 64),
                "role_contract_hash": prompt.get("role_contract_hash", "sha256:" + "0" * 64),
            }
        )
    invocation_set_path = str(inputs.get("review_invocation_set", "review-invocation-set.json"))
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "artifact_kind": "review_artifact_preparation",
                "artifact_scope": "run",
                "status": "completed",
                "review_prompt_contract": {
                    "path": ref,
                    "hash": contract_hash,
                },
                "source_context": {
                    "dirty_policy": "fail-closed",
                    "worktree": {
                        "status_command": "git status --porcelain=v1 --untracked-files=all",
                        "status_entries": [],
                        "included_dirty_paths": [],
                        "excluded_dirty_paths": [],
                    },
                },
                "input_artifacts": [
                    {
                        "path": ref,
                        "kind": "review_prompt_contract",
                        "hash": contract_hash,
                    }
                ],
                "generated_artifacts": {
                    "review_packets": review_packets,
                    "rendered_prompts": rendered_prompt_entries,
                    "review_invocation_set": {"path": invocation_set_path, "status": "predeclared"},
                },
                "reviewer_assignments": assignments,
                "validation": {
                    "schema": "schemas/review-artifact-preparation.schema.json",
                    "deterministic_script": "scripts/reviewers/prepare_review_set_artifacts.py",
                    "script_contract": "scripts/contracts/prepare_review_set_artifacts.yaml",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
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
    result = run("scripts/bdd_binding_check.py", "--bindings", str(binding_path))
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
    import yaml

    documents = [
        ROOT / "AGENTS.md",
        ROOT / "docs/review-control-model.md",
        ROOT / "docs/review-agent-interaction-protocol.md",
        ROOT / "docs/review-fusion-model.md",
        ROOT / "docs/review-profile-model.md",
        ROOT / "docs/review-prompt-contract.md",
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
    validation_template = (ROOT / "templates/finding-validation-report.md").read_text(encoding="utf-8").lower()
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
    assert "plausible blocker-path candidate findings have" in pr_readiness_workflow
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

    sys.path.insert(0, str(ROOT / "scripts" / "reviewers"))
    from prompt_rendering import render_review_prompt  # noqa: PLC0415

    packet = json.loads(
        (ROOT / "examples/external-reviewers/claude-code/review-packet.architecture.json").read_text(
            encoding="utf-8"
        )
    )
    role_contract = yaml.safe_load((ROOT / "profiles/reviewer_roles/architecture.yaml").read_text(encoding="utf-8"))
    rendered = render_review_prompt(packet, role_contract).lower()

    assert "blocker path" in rendered
    assert "acceptance consequence" in rendered
    assert "membership alone is not severity" in rendered
    assert "relevance inputs" in rendered
    assert "contract_gap" in rendered


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
            "answer": {
                "unrelated": True,
            },
            "status": "confirmed",
            "answered_by": "project-owner",
            "classification": "blocking-material",
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
            "answer": {
                "accepts_light_extraction_implementation_risk": True,
            },
            "status": "confirmed",
            "answered_by": "project-owner",
            "classification": "blocking-material",
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


def test_review_prompt_contract_schema_requires_verification_gate_report_input() -> None:
    import copy
    import json

    import jsonschema
    import yaml

    schema = json.loads((ROOT / "schemas/review-prompt-contract.schema.json").read_text(encoding="utf-8"))
    contract = yaml.safe_load((ROOT / "templates/review-prompt-contract.yaml").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(contract)

    missing_gate = copy.deepcopy(contract)
    missing_gate["inputs"].pop("verification_gate_report")
    assert list(validator.iter_errors(missing_gate))

    whitespace_gate = copy.deepcopy(contract)
    whitespace_gate["inputs"]["verification_gate_report"] = "   "
    assert list(validator.iter_errors(whitespace_gate))


def test_review_prompt_contract_template_assignments_use_invocation_set_evidence() -> None:
    import yaml

    contract = yaml.safe_load((ROOT / "templates/review-prompt-contract.yaml").read_text(encoding="utf-8"))
    assert contract.get("reviewer_assignments")
    assert contract["inputs"]["evidence_report"].endswith("evidence-report.md")
    assert contract["inputs"]["review_invocation_set"].endswith("review-invocation-set.json")
    assert all(
        assignment["report_path"].endswith(".json")
        for assignment in contract["reviewer_assignments"]
    )


def test_review_prompt_contract_schema_requires_json_reviewer_report_paths() -> None:
    import copy
    import json

    import jsonschema
    import yaml

    schema = json.loads((ROOT / "schemas/review-prompt-contract.schema.json").read_text(encoding="utf-8"))
    contract = yaml.safe_load((ROOT / "templates/review-prompt-contract.yaml").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(contract)

    broken = copy.deepcopy(contract)
    broken["reviewer_assignments"][0]["report_path"] = (
        "Docs/agentsflow/runs/YYYY-MM-DD-task-slug/reviewer-report.generalist-a.md"
    )

    errors = list(validator.iter_errors(broken))
    assert errors
    assert any(list(error.absolute_path)[-1:] == ["report_path"] for error in errors)


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
        (ROOT / "examples/external-reviewers/claude-code/review-packet.architecture.json").read_text(
            encoding="utf-8"
        )
    )
    role_contract = yaml.safe_load((ROOT / "profiles/reviewer_roles/architecture.yaml").read_text(encoding="utf-8"))
    rendered = render_review_prompt(packet, role_contract)

    assert "Return exactly one schema-valid reviewer-report JSON object" in rendered
    assert "If there are no findings, return an empty findings array" in rendered
    assert '"reviewer":{"id":"<reviewer_instance_id>"' in rendered


def test_external_wrapper_rejects_assignments_without_review_invocation_set() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts" / "reviewers"))
    import run_external_reviewer  # noqa: PLC0415

    contract = yaml.safe_load((ROOT / "templates/review-prompt-contract.yaml").read_text(encoding="utf-8"))
    broken = copy.deepcopy(contract)
    broken["inputs"]["evidence_report"] = broken["inputs"].get("review_invocation_set")
    broken["inputs"].pop("review_invocation_set", None)

    try:
        run_external_reviewer.validate_prompt_contract_invariants(broken)
    except ValueError as exc:
        assert "inputs.review_invocation_set" in str(exc)
    else:
        raise AssertionError("assignment-enabled contract without review_invocation_set was accepted")


def test_external_wrapper_rejects_aliased_evidence_and_review_invocation_set() -> None:
    import copy
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts" / "reviewers"))
    import run_external_reviewer  # noqa: PLC0415

    contract = yaml.safe_load((ROOT / "templates/review-prompt-contract.yaml").read_text(encoding="utf-8"))
    broken = copy.deepcopy(contract)
    broken["inputs"]["evidence_report"] = broken["inputs"]["review_invocation_set"]

    try:
        run_external_reviewer.validate_prompt_contract_invariants(broken)
    except ValueError as exc:
        assert "inputs.evidence_report" in str(exc)
    else:
        raise AssertionError("assignment-enabled contract with aliased evidence_report was accepted")


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


def test_homogeneous_plus_focused_requires_homogeneous_baseline_pair() -> None:
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
    focused = copy.deepcopy(contract)
    focused["identity"]["review_profile"] = "homogeneous-plus-focused"
    focused["identity"]["topology"] = "homogeneous-plus-focused"
    focused["identity"]["composition"] = "homogeneous-plus-focused"
    focused["prompt_policy"] = {
        "baseline_same_prompt": True,
        "baseline_same_packet": True,
        "baseline_same_rubric": True,
        "focused_reviewers_require_explicit_focus_zone": True,
        "focus_zones_may_overlap": True,
        "all_reviewers_must_report_p0_p1_outside_focus": True,
        "same_output_schema": True,
    }
    focused["reviewer_set"].append(
        {
            "instance_id": "adversarial-codex",
            "role_id": "adversarial",
            "role_contract": "profiles/reviewer_roles/adversarial.yaml",
            "independent": True,
            "focus_zone": {
                "primary_focus": ["false-green review evidence"],
            },
        }
    )
    adversarial_prompt = copy.deepcopy(focused["rendered_prompts"][0])
    adversarial_prompt["reviewer"] = "adversarial-codex"
    focused["rendered_prompts"].append(adversarial_prompt)
    for item in focused["rendered_prompts"]:
        if item["reviewer"] == "generalist-b":
            item["shared_prompt_content_hash"] = "sha256:" + "0" * 64

    errors = validate_repo.validate_review_prompt_contract_invariants(ROOT, path, focused, True)

    assert "homogeneous-plus-focused baseline rendered_prompts must share shared_prompt_content_hash" in "\n".join(errors)


def test_external_wrapper_rejects_divergent_homogeneous_plus_focused_baseline() -> None:
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
    focused = copy.deepcopy(contract)
    focused["identity"]["review_profile"] = "homogeneous-plus-focused"
    focused["identity"]["topology"] = "homogeneous-plus-focused"
    focused["identity"]["composition"] = "homogeneous-plus-focused"
    focused["prompt_policy"] = {
        "baseline_same_prompt": True,
        "baseline_same_packet": True,
        "baseline_same_rubric": True,
        "focused_reviewers_require_explicit_focus_zone": True,
        "focus_zones_may_overlap": True,
        "all_reviewers_must_report_p0_p1_outside_focus": True,
        "same_output_schema": True,
    }
    focused["reviewer_set"].append(
        {
            "instance_id": "adversarial-codex",
            "role_id": "adversarial",
            "role_contract": "profiles/reviewer_roles/adversarial.yaml",
            "independent": True,
            "focus_zone": {
                "primary_focus": ["false-green review evidence"],
            },
        }
    )
    adversarial_prompt = copy.deepcopy(focused["rendered_prompts"][0])
    adversarial_prompt["reviewer"] = "adversarial-codex"
    focused["rendered_prompts"].append(adversarial_prompt)
    for item in focused["rendered_prompts"]:
        if item["reviewer"] == "generalist-b":
            item["shared_packet_content_hash"] = "sha256:" + "0" * 64

    try:
        run_external_reviewer.validate_prompt_contract_invariants(focused)
    except ValueError as exc:
        assert "baseline rendered_prompts must share shared_packet_content_hash" in str(exc)
    else:
        raise AssertionError("divergent homogeneous-plus-focused baseline was accepted")


def test_review_prompt_contract_rejects_run_artifact_drift(tmp_path) -> None:
    import copy
    import hashlib
    import json
    import shutil
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

    stale_shared_content = copy.deepcopy(contract)
    stale_shared_content["inputs"]["review_packets"][0]["shared_packet_content_hash"] = "sha256:" + "0" * 64
    stale_shared_content["inputs"]["review_packets"][1]["shared_packet_content_hash"] = "sha256:" + "0" * 64
    stale_shared_content["rendered_prompts"][0]["shared_packet_content_hash"] = "sha256:" + "0" * 64
    stale_shared_content["rendered_prompts"][1]["shared_packet_content_hash"] = "sha256:" + "0" * 64
    errors = validate_repo.validate_review_prompt_contract_run_references(ROOT, path, stale_shared_content)
    assert errors
    assert "shared_packet_content_hash" in "\n".join(errors)

    prompt_root = tmp_path / "agentsflow-rendered-prompt-drift"
    shutil.copytree(
        ROOT,
        prompt_root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__", "run-artifacts"),
    )
    prompt_contract_path = (
        prompt_root
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-prompt-contract.yaml"
    )
    prompt_path = (
        prompt_root
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-prompts/generalist-a.md"
    )
    prompt_text = prompt_path.read_text(encoding="utf-8")
    prompt_path.write_text(prompt_text.replace("risk_surface_profile", "stale_risk_surface_profile"), encoding="utf-8")
    prompt_contract = yaml.safe_load(prompt_contract_path.read_text(encoding="utf-8"))
    prompt_contract["rendered_prompts"][0]["prompt_hash"] = (
        "sha256:" + hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    )
    prompt_contract_path.write_text(yaml.safe_dump(prompt_contract, sort_keys=False), encoding="utf-8")
    errors = validate_repo.validate_review_prompt_contract_run_references(
        prompt_root,
        prompt_contract_path,
        prompt_contract,
    )
    assert "prompt_path content must match current packet and role contract" in "\n".join(errors)

    root = tmp_path / "agentsflow-shared-packet-drift"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__", "run-artifacts"),
    )
    copied_path = (
        root
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-prompt-contract.yaml"
    )
    packet_path = (
        root
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-packets/generalist-a.json"
    )
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["known_blockers"] = [{"id": "unexpected"}]
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    copied_contract = yaml.safe_load(copied_path.read_text(encoding="utf-8"))
    errors = validate_repo.validate_review_prompt_contract_run_references(root, copied_path, copied_contract)
    assert errors
    assert "content must match shared-content.json" in "\n".join(errors)

    shared_content_path = (
        root
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-packets/shared-content.json"
    )
    shared_content = json.loads(shared_content_path.read_text(encoding="utf-8"))
    shared_content["excluded_envelope_fields"].append("known_blockers")
    shared_content_path.write_text(json.dumps(shared_content, indent=2) + "\n", encoding="utf-8")
    errors = validate_repo.validate_review_prompt_contract_run_references(root, copied_path, copied_contract)
    assert errors
    assert "excluded_envelope_fields may only contain envelope fields" in "\n".join(errors)

    shared_content["excluded_envelope_fields"] = ["reviewer_instance_id"]
    shared_content_path.write_text(json.dumps(shared_content, indent=2) + "\n", encoding="utf-8")
    packet["excluded_envelope_fields"] = ["known_blockers"]
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    errors = validate_repo.validate_review_prompt_contract_run_references(root, copied_path, copied_contract)
    assert errors
    assert "must not contain reserved shared-content metadata field excluded_envelope_fields" in "\n".join(errors)

    packet.pop("excluded_envelope_fields")
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    split_packet_dir = packet_path.parent / "split"
    split_packet_dir.mkdir()
    split_packet_path = split_packet_dir / "generalist-b.json"
    original_b_path = packet_path.parent / "generalist-b.json"
    split_packet_path.write_text(original_b_path.read_text(encoding="utf-8"), encoding="utf-8")
    split_contract = copy.deepcopy(copied_contract)
    split_contract["inputs"]["review_packets"][1]["path"] = str(split_packet_path.relative_to(root))
    errors = validate_repo.validate_review_prompt_contract_run_references(root, copied_path, split_contract)
    assert errors
    assert "missing sibling shared-content.json" in "\n".join(errors)

    shared_content_path.unlink()
    errors = validate_repo.validate_review_prompt_contract_run_references(root, copied_path, copied_contract)
    assert errors
    assert "must have exactly one sibling shared-content.json" in "\n".join(errors)


def test_review_prompt_contract_allows_provider_as_shared_packet_envelope_field(tmp_path) -> None:
    import hashlib
    import json
    import shutil
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415
    from repo_validation.review import _render_expected_review_prompt  # noqa: PLC0415

    root = tmp_path / "agentsflow-mixed-provider-shared-packet"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__", "run-artifacts"),
    )
    run_dir = root / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator"
    contract_path = run_dir / "review-prompt-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    packet_dir = run_dir / "review-packets"
    shared_content_path = packet_dir / "shared-content.json"
    shared_content = json.loads(shared_content_path.read_text(encoding="utf-8"))
    shared_content["excluded_envelope_fields"] = ["reviewer_instance_id", "provider"]
    shared_content_path.write_text(json.dumps(shared_content, indent=2) + "\n", encoding="utf-8")
    shared_content_hash = "sha256:" + hashlib.sha256(shared_content_path.read_bytes()).hexdigest()

    role_path = root / "profiles/reviewer_roles/generalist.yaml"
    role_data = yaml.safe_load(role_path.read_text(encoding="utf-8"))
    packet_providers = {
        "generalist-a": "internal-agent",
        "generalist-b": "claude-code",
    }
    packet_hashes: dict[str, str] = {}
    for reviewer, provider in packet_providers.items():
        packet_path = packet_dir / f"{reviewer}.json"
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["provider"] = provider
        packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
        packet_hashes[reviewer] = "sha256:" + hashlib.sha256(packet_path.read_bytes()).hexdigest()

        prompt_path = run_dir / "review-prompts" / f"{reviewer}.md"
        prompt_path.write_text(_render_expected_review_prompt(packet, role_data), encoding="utf-8")
        prompt_hash = "sha256:" + hashlib.sha256(prompt_path.read_bytes()).hexdigest()
        for rendered in contract["rendered_prompts"]:
            if rendered["reviewer"] == reviewer:
                rendered["prompt_hash"] = prompt_hash
                rendered["packet_hash"] = packet_hashes[reviewer]
                rendered["shared_packet_content_hash"] = shared_content_hash

    for packet_ref in contract["inputs"]["review_packets"]:
        reviewer = packet_ref["reviewer"]
        packet_ref["packet_hash"] = packet_hashes[reviewer]
        packet_ref["shared_packet_content_hash"] = shared_content_hash
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, contract)
    assert not errors


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


def test_review_prompt_contract_run_path_requires_run_scope() -> None:
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
    relabeled = copy.deepcopy(contract)
    relabeled["artifact_scope"] = "template"
    errors = validate_repo.validate_review_prompt_contract_run_references(ROOT, path, relabeled)
    assert errors
    assert "artifact_scope: run" in "\n".join(errors)


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

    errors = validate_repo.validate_review_packet_artifact(root, packet_path, True)
    joined = "\n".join(errors)
    assert "evidence_freshness.latest_green_gate must match verification_gate_report.path" in joined
    assert "evidence_freshness.latest_green_gate must reference a verification gate report artifact" in joined


def test_review_packet_rejects_directory_latest_green_gate_reference(tmp_path) -> None:
    import json
    import shutil
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "agentsflow-directory-green-reference"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"),
    )
    run_dir = root / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator"
    for packet_name in ["generalist-a.json", "generalist-b.json", "shared-content.json"]:
        packet_path = run_dir / "review-packets" / packet_name
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["verification_gate_report"]["path"] = "review-packets"
        packet["evidence_freshness"]["latest_green_gate"] = "review-packets"
        packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    contract_path = run_dir / "review-prompt-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    contract["inputs"]["verification_gate_report"] = (
        "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-packets"
    )
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    errors = validate_repo.validate_review_packet_artifact(
        root,
        run_dir / "review-packets/generalist-a.json",
        True,
    )
    joined = "\n".join(errors)
    assert "verification_gate_report.path must reference a verification gate report artifact" in joined
    assert "evidence_freshness.latest_green_gate must reference a verification gate report artifact" in joined
    contract_errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, contract)
    assert "inputs.verification_gate_report must be a file artifact" in "\n".join(contract_errors)


def test_review_packet_rejects_non_gate_file_latest_green_gate_reference(tmp_path) -> None:
    import json
    import shutil
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "agentsflow-non-gate-green-reference"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"),
    )
    run_dir = root / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator"
    for packet_name in ["generalist-a.json", "generalist-b.json", "shared-content.json"]:
        packet_path = run_dir / "review-packets" / packet_name
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["verification_gate_report"]["path"] = "task.contract.md"
        packet["evidence_freshness"]["latest_green_gate"] = "task.contract.md"
        packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    contract_path = run_dir / "review-prompt-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    contract["inputs"]["verification_gate_report"] = (
        "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/task.contract.md"
    )
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    errors = validate_repo.validate_review_packet_artifact(
        root,
        run_dir / "review-packets/generalist-a.json",
        True,
    )
    joined = "\n".join(errors)
    assert "verification_gate_report.path must reference a verification gate report artifact" in joined
    assert "evidence_freshness.latest_green_gate must reference a verification gate report artifact" in joined
    contract_errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, contract)
    assert "inputs.verification_gate_report must reference a verification gate report artifact" in "\n".join(contract_errors)


def test_review_packet_rejects_placeholder_verification_gate_reference(tmp_path) -> None:
    import json
    import shutil
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "agentsflow-placeholder-green-reference"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"),
    )
    run_dir = root / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator"
    for packet_name in ["generalist-a.json", "generalist-b.json", "shared-content.json"]:
        packet_path = run_dir / "review-packets" / packet_name
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["verification_gate_report"]["path"] = "<verification-gate-report.md>"
        packet["evidence_freshness"]["latest_green_gate"] = "<verification-gate-report.md>"
        packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    contract_path = run_dir / "review-prompt-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    contract["inputs"]["verification_gate_report"] = "<verification-gate-report.md>"
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    errors = validate_repo.validate_review_packet_artifact(
        root,
        run_dir / "review-packets/generalist-a.json",
        True,
    )
    joined = "\n".join(errors)
    assert "verification_gate_report.path must reference a verification gate report artifact" in joined
    assert "evidence_freshness.latest_green_gate must reference a verification gate report artifact" in joined
    assert "review_prompt_contract inputs.verification_gate_report must reference a verification gate report artifact" in joined


def test_review_packet_rejects_unstructured_json_verification_gate_report(tmp_path) -> None:
    import json
    import shutil
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "agentsflow-unstructured-json-green-report"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"),
    )
    run_dir = root / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator"
    (run_dir / "verification-gate-report.json").write_text(
        json.dumps({"kind": "unrelated_report"}, indent=2) + "\n",
        encoding="utf-8",
    )
    for packet_name in ["generalist-a.json", "generalist-b.json", "shared-content.json"]:
        packet_path = run_dir / "review-packets" / packet_name
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["verification_gate_report"]["path"] = "verification-gate-report.json"
        packet["evidence_freshness"]["latest_green_gate"] = "verification-gate-report.json"
        packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    contract_path = run_dir / "review-prompt-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    contract["inputs"]["verification_gate_report"] = (
        "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/verification-gate-report.json"
    )
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    errors = validate_repo.validate_review_packet_artifact(
        root,
        run_dir / "review-packets/generalist-a.json",
        True,
    )
    joined = "\n".join(errors)
    assert "verification_gate_report.path must reference a verification gate report artifact" in joined
    assert "evidence_freshness.latest_green_gate must reference a verification gate report artifact" in joined
    assert "review_prompt_contract inputs.verification_gate_report must reference a verification gate report artifact" in joined
    contract_errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, contract)
    assert "inputs.verification_gate_report must reference a verification gate report artifact" in "\n".join(contract_errors)


def test_repository_validation_scans_root_run_review_artifacts(tmp_path) -> None:
    import json
    import shutil
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "agentsflow-root-run-review-artifacts"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"),
    )
    source_run_dir = (
        root
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator"
    )
    root_run_dir = root / "Docs/agentsflow/runs/2026-06-17-add-calculator"
    root_run_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_run_dir, root_run_dir)

    packet_path = root_run_dir / "review-packets/generalist-a.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["verification_gate_report"]["path"] = "<verification-gate-report.md>"
    packet["evidence_freshness"]["latest_green_gate"] = "<verification-gate-report.md>"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    contract_path = root_run_dir / "review-prompt-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    contract["inputs"]["verification_gate_report"] = "<verification-gate-report.md>"
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    errors = validate_repo.validate_repository(root)
    joined = "\n".join(errors)
    assert f"{packet_path}: verification_gate_report.path must reference a verification gate report artifact" in joined
    assert f"{packet_path}: evidence_freshness.latest_green_gate must reference a verification gate report artifact" in joined
    assert f"{contract_path}: inputs.verification_gate_report does not exist: <verification-gate-report.md>" in joined


def test_repository_validation_ignores_local_run_artifacts_review_artifacts(tmp_path) -> None:
    import json
    import shutil
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "agentsflow-run-artifacts-review-artifacts"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__", "run-artifacts"),
    )
    source_run_dir = (
        root
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator"
    )
    run_artifacts_dir = root / "run-artifacts/agentsflow/runs/2026-06-17-add-calculator"
    run_artifacts_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_run_dir, run_artifacts_dir)

    packet_path = run_artifacts_dir / "review-packets/generalist-a.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["verification_gate_report"]["path"] = "<verification-gate-report.md>"
    packet["evidence_freshness"]["latest_green_gate"] = "<verification-gate-report.md>"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    contract_path = run_artifacts_dir / "review-prompt-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    contract["inputs"]["verification_gate_report"] = "<verification-gate-report.md>"
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    errors = validate_repo.validate_repository(root)
    assert errors == []


def test_repository_validation_rejects_cross_run_verification_gate_report(tmp_path) -> None:
    import json
    import shutil
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "agentsflow-cross-run-green-report"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"),
    )
    source_run_dir = (
        root
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator"
    )
    root_run_dir = root / "Docs/agentsflow/runs/2026-06-17-add-calculator"
    root_run_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_run_dir, root_run_dir)
    cross_run_report_ref = (
        "examples/e2e/minimal-python-project/Docs/agentsflow/runs/"
        "2026-06-17-add-calculator/verification-gate-report.md"
    )

    packet_path = root_run_dir / "review-packets/generalist-a.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["verification_gate_report"]["path"] = cross_run_report_ref
    packet["evidence_freshness"]["latest_green_gate"] = cross_run_report_ref
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    contract_path = root_run_dir / "review-prompt-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    contract["inputs"]["verification_gate_report"] = cross_run_report_ref
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    errors = validate_repo.validate_repository(root)
    joined = "\n".join(errors)
    assert (
        f"{packet_path}: verification_gate_report.path must reference a verification gate report artifact "
        f"in the same run directory: {cross_run_report_ref}"
    ) in joined
    assert (
        f"{packet_path}: evidence_freshness.latest_green_gate must reference a verification gate report artifact "
        f"in the same run directory: {cross_run_report_ref}"
    ) in joined
    assert (
        f"{contract_path}: inputs.verification_gate_report must reference a verification gate report artifact "
        f"in the same run directory: {cross_run_report_ref}"
    ) in joined


def test_review_packet_requires_verification_gate_reference_for_real_run(tmp_path) -> None:
    import json
    import shutil
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "agentsflow-missing-green-reference"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"),
    )
    run_dir = root / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator"
    packet_path = run_dir / "review-packets/generalist-a.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet.pop("verification_gate_report")
    packet["evidence_freshness"]["latest_green_gate"] = "task.contract.md"
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    contract_path = run_dir / "review-prompt-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    contract["inputs"].pop("verification_gate_report")
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    errors = validate_repo.validate_review_packet_artifact(root, packet_path, True)
    joined = "\n".join(errors)
    assert "verification_gate_report.path is required" in joined
    assert "review_prompt_contract inputs.verification_gate_report is required" in joined


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
    assert "defaulted" not in workflow["human_interaction"]["allowed_resume_states"]
    assert "unresolved" not in workflow["human_interaction"]["allowed_resume_states"]
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
        "risk-surface",
        "failure-path-matrix",
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
    required_decision_categories = {
        "scope",
        "adr",
        "risk",
        "risk-surface",
        "failure-path-matrix",
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
    assert any("project-knowledge-extraction.md" in item for item in gate["inputs"])
    assert any("human risk acceptance evidence" in item for item in gate["inputs"])
    assert any("extraction depth upgrade evidence" in item for item in gate["inputs"])
    assert any("existing project policy/workflow binding evidence" in item for item in gate["required_evidence"])
    assert any("human decision packet" in item for item in gate["required_evidence"])
    assert any("risk-surface" in item for item in gate["required_evidence"])
    assert any("Failure Path Matrix" in item for item in gate["required_evidence"])
    assert any("project-knowledge-extraction.md" in item for item in gate["required_evidence"])
    assert any("human risk acceptance evidence" in item for item in gate["required_evidence"])
    assert set(gate["decision_categories"]) == required_decision_categories
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

    broken_categories = copy.deepcopy(gate)
    broken_categories["decision_categories"].remove("evidence")
    errors = validate_repo.validate_gate_manifest(ROOT, path, broken_categories)
    assert "target_workflow_readiness_gate decision_categories missing: evidence" in "\n".join(errors)

    broken_risk_surface = copy.deepcopy(gate)
    broken_risk_surface["decision_categories"].remove("risk-surface")
    errors = validate_repo.validate_gate_manifest(ROOT, path, broken_risk_surface)
    assert "target_workflow_readiness_gate decision_categories missing: risk-surface" in "\n".join(errors)

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
    assert "max_review_cycles must be an integer" in (result.stdout + result.stderr)


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
    subprocess.run(["git", "add", "-f", "."], cwd=root, check=True, capture_output=True, text=True)

    result = run("scripts/validate_repo.py", "--root", str(root))
    assert result.returncode != 0
    assert "tracked local AgentsFlow run artifact is not allowed" in (result.stdout + result.stderr)

    tracked_result = run("scripts/validate_repo.py", "--root", str(root), "--tracked-only")
    assert tracked_result.returncode != 0
    assert "tracked local AgentsFlow run artifact is not allowed" in (
        tracked_result.stdout + tracked_result.stderr
    )


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


def test_external_reviewer_wrapper_mock_passes(tmp_path) -> None:
    import json

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
    invocation = json.loads(out.with_suffix(".invocation.json").read_text(encoding="utf-8"))
    assert invocation["requested_model"] == "opus"
    assert invocation["requested_effort"] == "max"
    assert invocation["sandbox_mode"] == "require_escalated"
    assert invocation["tools"] == ""


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


def test_external_reviewer_wrapper_normalizes_claude_code_envelope(tmp_path) -> None:
    import json

    reviewer_report = {
        "reviewer": {
            "id": "claude-code-architecture",
            "provider": "claude-code",
            "role": "architecture",
        },
        "summary": "Envelope summary",
        "findings": [
            {
                "id": "ARCH-ENV",
                "severity": "P2",
                "focus_area": "external-reviewer-normalization",
                "title": "Envelope finding",
                "evidence": ["raw.result", "parser literal fence ``` inside JSON string"],
                "rationale": "The wrapper must normalize the nested Claude Code result.",
                "recommendation": "Parse result JSON before reviewer-report normalization.",
                "blocker_path": "external finding -> required readiness evidence -> unsafe acceptance",
                "acceptance_impact": "Dropping this field would hide the readiness blocker.",
                "mandatory_evidence_gap": True,
            }
        ],
        "requests_for_additional_verification": [
            "Confirm the wrapped string request is normalized into an object."
        ],
    }
    raw = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": "Returning the reviewer report as required.\n\n```json\n" + json.dumps(reviewer_report) + "\n```",
        "total_cost_usd": 1.23,
        "usage": {
            "service_tier": "standard",
            "speed": "standard",
        },
        "modelUsage": {
            "claude-haiku-4-5-20251001": {
                "inputTokens": 10,
                "outputTokens": 1,
            },
            "claude-opus-4-8[1m]": {
                "inputTokens": 100,
                "outputTokens": 10,
            },
        },
    }
    raw_path = tmp_path / "claude-envelope.json"
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
    assert result.returncode == 0, result.stdout + result.stderr
    normalized = json.loads(out.read_text(encoding="utf-8"))
    assert normalized["summary"] == "Envelope summary"
    assert normalized["findings"][0]["id"] == "ARCH-ENV"
    assert normalized["findings"][0]["category"] == "external-reviewer-normalization"
    assert normalized["findings"][0]["why_it_matters"] == "The wrapper must normalize the nested Claude Code result."
    assert normalized["findings"][0]["blocker_path"] == (
        "external finding -> required readiness evidence -> unsafe acceptance"
    )
    assert normalized["findings"][0]["acceptance_impact"] == (
        "Dropping this field would hide the readiness blocker."
    )
    assert normalized["findings"][0]["mandatory_evidence_gap"] is True
    assert normalized["normalization"]["method"] == "deterministic-extraction"
    assert normalized["normalization"]["source_path"] == str(out.with_suffix(".raw.json"))
    assert normalized["normalization"]["schema_validation"] == "passed"
    assert normalized["normalization"]["normalized_by"] == "scripts/reviewers/run_external_reviewer.py"
    assert normalized["requests_for_additional_verification"] == [
        {
            "id": "REQUEST-001",
            "request": "Confirm the wrapped string request is normalized into an object.",
        }
    ]
    assert "output_hash" not in normalized["normalization"]
    invocation = json.loads(out.with_suffix(".invocation.json").read_text(encoding="utf-8"))
    assert invocation["requested_model"] == "opus"
    assert invocation["requested_effort"] == "max"
    assert invocation["sandbox_mode"] == "require_escalated"
    assert invocation["tools"] == ""
    assert invocation["normalization"]["source_hash"] == invocation["raw_output_hash"]
    assert invocation["normalization"]["output_hash"] == invocation["normalized_output_hash"]
    assert invocation["provider_models_used"] == [
        "claude-haiku-4-5-20251001",
        "claude-opus-4-8[1m]",
    ]
    assert invocation["provider_total_cost_usd"] == 1.23
    assert invocation["provider_service_tier"] == "standard"
    assert invocation["provider_speed"] == "standard"


def test_external_reviewer_wrapper_normalizes_schema_adjacent_claude_code_result(tmp_path) -> None:
    import json

    schema_adjacent_report = {
        "review_context": {
            "run_id": "example-external-reviewer",
            "material_change_id": "example",
            "review_packet_path": "examples/external-reviewers/claude-code/review-packet.architecture.json",
            "reviewer_instance_id": "architecture",
        },
        "reviewer_role": "architecture",
        "provider": "claude-code",
        "summary": "Schema-adjacent summary",
        "findings": [
            {
                "id": "ARCH-ADJ",
                "severity": "P2",
                "risk_surface": "external_reviewer_normalization",
                "title": "Schema-adjacent finding",
                "evidence": ["raw.result"],
                "description": "Claude returned useful structured evidence without a reviewer object.",
                "suggested_action": "Normalize the structured report from packet context.",
            }
        ],
        "self_declared_limitations": [],
    }
    raw = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": json.dumps(schema_adjacent_report),
    }
    raw_path = tmp_path / "claude-schema-adjacent.json"
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

    assert result.returncode == 0, result.stdout + result.stderr
    normalized = json.loads(out.read_text(encoding="utf-8"))
    assert normalized["reviewer"]["provider"] == "claude-code"
    assert normalized["reviewer"]["role"] == "architecture"
    assert normalized["summary"] == "Schema-adjacent summary"
    assert normalized["findings"][0]["category"] == "external_reviewer_normalization"
    assert normalized["findings"][0]["why_it_matters"] == (
        "Claude returned useful structured evidence without a reviewer object."
    )
    assert normalized["findings"][0]["recommendation"] == (
        "Normalize the structured report from packet context."
    )
    assert normalized["normalization"]["schema_validation"] == "passed"


def test_external_reviewer_wrapper_can_skip_raw_output_persistence(tmp_path) -> None:
    import json

    reviewer_report = {
        "reviewer": {
            "id": "claude-code-architecture",
            "provider": "claude-code",
            "role": "architecture",
            "model": "claude-opus-4-8",
        },
        "summary": "Envelope summary",
        "findings": [],
    }
    raw = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": "```json\n" + json.dumps(reviewer_report) + "\n```",
    }
    mock_raw_path = tmp_path / "claude-envelope.json"
    mock_raw_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    config_path = tmp_path / "claude-code.yaml"
    config_path.write_text(
        (ROOT / "examples" / "external-reviewers" / "claude-code" / "claude-code.yaml")
        .read_text(encoding="utf-8")
        .replace("preserve_raw_output: true", "preserve_raw_output: false"),
        encoding="utf-8",
    )
    out = tmp_path / "reviewer-report.json"
    raw_output_path = tmp_path / "reviewer-report.raw.json"

    result = run(
        "scripts/reviewers/run_external_reviewer.py",
        "--provider", "claude-code",
        "--config", str(config_path),
        "--input", "examples/external-reviewers/claude-code/review-packet.architecture.json",
        "--mock-response", str(mock_raw_path),
        "--output", str(out),
        "--raw-output", str(raw_output_path),
        env=clean_env(),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert not raw_output_path.exists()
    normalized = json.loads(out.read_text(encoding="utf-8"))
    assert normalized["normalization"]["source_path"] == ""
    invocation = json.loads(out.with_suffix(".invocation.json").read_text(encoding="utf-8"))
    assert invocation["raw_output_path"] == ""
    assert invocation["raw_output_hash"].startswith("sha256:")
    assert invocation["normalization"]["source_path"] == ""
    assert invocation["normalization"]["source_hash"] == invocation["raw_output_hash"]


def test_external_reviewer_wrapper_rejects_non_json_claude_code_envelope(tmp_path) -> None:
    import json

    import jsonschema

    raw_path = tmp_path / "claude-envelope.json"
    raw_path.write_text(
        json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "result": "No findings.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
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
    assert "result must contain reviewer-report JSON" in (result.stdout + result.stderr)
    invocation_path = out.with_suffix(".invocation.json")
    invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas" / "reviewer-invocation.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(invocation)
    assert invocation["failure_stage"] == "provider_output_processing"
    assert "reviewer-report JSON" in invocation["failure_message"]
    assert "normalized_output_hash" not in invocation


def test_external_reviewer_wrapper_records_schema_valid_nonzero_provider_exit(tmp_path, monkeypatch) -> None:
    import json
    import sys

    import jsonschema

    for name in FORBIDDEN_CLAUDE_ENV:
        monkeypatch.delenv(name, raising=False)

    sys.path.insert(0, str(ROOT / "scripts" / "reviewers"))
    import run_external_reviewer  # noqa: PLC0415
    from providers import claude_code  # noqa: PLC0415

    prompt = "fake prompt"
    hash_value = run_external_reviewer.sha256_text(prompt)
    concrete_hash = "sha256:" + "1" * 64

    def fake_validate_review_packet(packet, root, packet_path, packet_schema_path):
        return {
            "input_hash": concrete_hash,
            "review_prompt_contract_hash": concrete_hash,
            "role_contract_hash": concrete_hash,
            "rubric_hash": concrete_hash,
            "schema_hash": concrete_hash,
            "artifact_scope": "run",
            "selected_prompt": {"prompt_hash": hash_value},
            "role_contract": {"kind": "reviewer_role", "name": packet["reviewer_role"]},
        }

    def fake_invoke(config, prompt_text, cwd=None):
        return claude_code.ProviderResult(
            stdout=json.dumps(
                {
                    "type": "result",
                    "subtype": "error",
                    "is_error": True,
                    "result": "provider boom",
                }
            ),
            stderr="provider stderr",
            exit_code=1,
            command_display="claude -p <stdin>",
        )

    out = tmp_path / "reviewer-report.json"
    monkeypatch.setattr(run_external_reviewer, "validate_review_packet", fake_validate_review_packet)
    monkeypatch.setattr(run_external_reviewer, "render_prompt", lambda packet, role_contract: prompt)
    monkeypatch.setattr(claude_code, "invoke", fake_invoke)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_external_reviewer.py",
            "--provider",
            "claude-code",
            "--config",
            "examples/external-reviewers/claude-code/claude-code.yaml",
            "--input",
            "examples/external-reviewers/claude-code/review-packet.architecture.json",
            "--output",
            str(out),
        ],
    )

    assert run_external_reviewer.main() == 2
    invocation = json.loads(out.with_suffix(".invocation.json").read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas" / "reviewer-invocation.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(invocation)
    assert invocation["failure_stage"] == "provider_execution"
    assert "exit code 1" in invocation["failure_message"]
    assert "provider stderr" in invocation["failure_message"]
    assert "normalized_output_hash" not in invocation


def test_external_reviewer_wrapper_rejects_empty_or_unrelated_json_envelope(tmp_path) -> None:
    import json

    for result_text in ["{}", 'prologue {"note": "not a reviewer report"}']:
        raw_path = tmp_path / "claude-envelope.json"
        raw_path.write_text(
            json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "is_error": False,
                    "result": result_text,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
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
        assert "result must contain reviewer-report JSON" in (result.stdout + result.stderr)


def test_external_reviewer_wrapper_rejects_bare_unrelated_json(tmp_path) -> None:
    import json

    raw_path = tmp_path / "claude-bare-unrelated.json"
    raw_path.write_text(
        json.dumps(
            {
                "kind": "unrelated-report",
                "note": "This is valid JSON but not a reviewer report.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
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
    assert "result must contain reviewer-report JSON" in (result.stdout + result.stderr)
    assert not out.exists()


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
    assert "permission_mode: default" in (result.stdout + result.stderr)


def test_external_reviewer_wrapper_rejects_non_escalated_sandbox_or_enabled_tools(tmp_path) -> None:
    import yaml

    base_config = yaml.safe_load(
        (ROOT / "examples/external-reviewers/claude-code/claude-code.yaml").read_text(
            encoding="utf-8"
        )
    )
    for key, value, expected in [
        ("sandbox_mode", "default", "sandbox_mode: require_escalated"),
        ("tools", "Read", 'execution.tools: ""'),
    ]:
        config = yaml.safe_load(yaml.safe_dump(base_config))
        config["execution"][key] = value
        config_path = tmp_path / f"claude-code-{key}.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        out = tmp_path / f"reviewer-report-{key}.json"

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
        assert expected in (result.stdout + result.stderr)


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


def test_external_reviewer_wrapper_rejects_non_default_model_or_effort(tmp_path) -> None:
    import yaml

    base_config = yaml.safe_load(
        (ROOT / "examples/external-reviewers/claude-code/claude-code.yaml").read_text(
            encoding="utf-8"
        )
    )
    for key, value, expected in [
        ("model", "sonnet", "execution.model"),
        ("effort", "high", "execution.effort"),
    ]:
        config = dict(base_config)
        config["execution"] = dict(base_config["execution"])
        config["execution"][key] = value
        config_path = tmp_path / f"claude-code-{key}.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        out = tmp_path / f"reviewer-report-{key}.json"

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
        assert expected in (result.stdout + result.stderr)


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


def test_external_reviewer_wrapper_rejects_forbidden_claude_settings_env(tmp_path) -> None:
    import json

    config_dir = tmp_path / "claude-config"
    config_dir.mkdir()
    settings = config_dir / "__settings.json"
    settings.write_text(
        json.dumps(
            {
                "env": {
                    "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    env = clean_env()
    env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    out = tmp_path / "reviewer-report.json"

    result = run(
        "scripts/reviewers/run_external_reviewer.py",
        "--provider", "claude-code",
        "--config", "examples/external-reviewers/claude-code/claude-code.yaml",
        "--input", "examples/external-reviewers/claude-code/review-packet.architecture.json",
        "--mock-response", "examples/external-reviewers/claude-code/mock-raw-output.json",
        "--output", str(out),
        env=env,
    )
    joined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Forbidden Claude API/proxy setting" in joined
    assert "ANTHROPIC_BASE_URL" in joined
    assert "api.z.ai" not in joined


def test_review_prompt_contract_rejects_model_diversity_without_distinct_assignments() -> None:
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
    broken["provider_policy"] = {
        "require_model_diversity": True,
        "min_distinct_provider_model_families": 2,
    }
    broken["reviewer_assignments"] = [
        {
            "reviewer": "generalist-a",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": broken["inputs"]["review_packets"][0]["path"],
            "report_path": "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/reviewer-report.generalist-a.json",
        },
        {
            "reviewer": "generalist-b",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": broken["inputs"]["review_packets"][1]["path"],
            "report_path": "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/reviewer-report.generalist-b.json",
        },
    ]

    errors = validate_repo.validate_review_prompt_contract_invariants(ROOT, path, broken, True)
    assert errors
    assert "model diversity" in "\n".join(errors)


def test_review_prompt_contract_assignments_require_review_set_evidence() -> None:
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
    broken["provider_policy"] = {
        "allow_external_reviewers": True,
        "require_model_diversity": True,
        "min_distinct_provider_model_families": 2,
    }
    broken["inputs"]["evidence_report"] = "Docs/agentsflow/runs/2026-06-17-add-calculator/review-invocation-set.json"
    broken["inputs"].pop("review_invocation_set", None)
    broken["reviewer_assignments"] = [
        {
            "reviewer": "generalist-a",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": broken["inputs"]["review_packets"][0]["path"],
            "report_path": "missing/internal-report.json",
        },
        {
            "reviewer": "generalist-b",
            "provider": "claude-code",
            "model_family": "opus",
            "provider_config": "examples/external-reviewers/claude-code/claude-code.yaml",
            "packet_path": broken["inputs"]["review_packets"][1]["path"],
            "report_path": "missing/claude-report.json",
            "raw_output_path": "missing/claude-raw.json",
            "invocation_metadata_path": "missing/claude-invocation.json",
        },
    ]

    errors = validate_repo.validate_review_prompt_contract_run_references(ROOT, path, broken)
    joined = "\n".join(errors)
    assert "review_invocation_set" in joined
    assert "report_path" in joined


def test_review_prompt_contract_rejects_failed_invocation_set_as_gate_evidence(tmp_path) -> None:
    import copy
    import json
    import shutil
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "root"
    root.mkdir()
    for rel in ["schemas", "profiles", "templates/review-prompts"]:
        shutil.copytree(ROOT / rel, root / rel)
    run_rel = Path("examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator")
    shutil.copytree(ROOT / run_rel, root / run_rel)
    contract_path = root / run_rel / "review-prompt-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(contract)
    invocation_set = run_rel / "review-invocation-set.failed.json"
    (root / invocation_set).write_text(
        json.dumps(
            {
                "artifact_kind": "review_invocation_set",
                "review_prompt_contract": str(run_rel / "review-prompt-contract.yaml"),
                "status": "failed",
                "provider_model_families": [],
                "reviewers": [
                    {
                        "reviewer": "generalist-a",
                        "provider": "internal-agent",
                        "model_family": "codex",
                        "packet_path": broken["inputs"]["review_packets"][0]["path"],
                        "report_path": "missing/generalist-a.json",
                        "status": "failed",
                    },
                    {
                        "reviewer": "generalist-b",
                        "provider": "internal-agent",
                        "model_family": "codex",
                        "packet_path": broken["inputs"]["review_packets"][1]["path"],
                        "report_path": "missing/generalist-b.json",
                        "status": "failed",
                    },
                ],
                "error": "review set failed",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    broken["inputs"]["review_invocation_set"] = str(invocation_set)
    broken["reviewer_assignments"] = [
        {
            "reviewer": "generalist-a",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": broken["inputs"]["review_packets"][0]["path"],
            "report_path": "missing/generalist-a.json",
        },
        {
            "reviewer": "generalist-b",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": broken["inputs"]["review_packets"][1]["path"],
            "report_path": "missing/generalist-b.json",
        },
    ]

    errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, broken)

    assert "review_invocation_set status must be completed for reviewer_assignments evidence" in "\n".join(errors)


def test_review_prompt_contract_rejects_failed_reviewer_in_completed_invocation_set(tmp_path) -> None:
    import copy
    import json
    import shutil
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "root"
    root.mkdir()
    for rel in ["schemas", "profiles", "templates/review-prompts"]:
        shutil.copytree(ROOT / rel, root / rel)
    run_rel = Path("examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator")
    shutil.copytree(ROOT / run_rel, root / run_rel)
    contract_path = root / run_rel / "review-prompt-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(contract)
    reports_dir = run_rel / "review-reports"
    (root / reports_dir).mkdir(exist_ok=True)
    report_paths = {
        "generalist-a": reports_dir / "reviewer-report.generalist-a.json",
        "generalist-b": reports_dir / "reviewer-report.generalist-b.json",
    }
    for index, reviewer in enumerate(["generalist-a", "generalist-b"]):
        (root / report_paths[reviewer]).write_text(
            json.dumps(
                {
                    "reviewer": {
                        "id": reviewer,
                        "provider": "internal-agent",
                        "role": "generalist",
                        "model": "codex",
                    },
                    "review_context": reviewer_report_context(
                        reviewer,
                        broken["inputs"]["review_packets"][index]["path"],
                    ),
                    "summary": "Internal reviewer artifact.",
                    "findings": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    invocation_set = run_rel / "review-invocation-set.json"
    (root / invocation_set).write_text(
        json.dumps(
            {
                "artifact_kind": "review_invocation_set",
                "review_prompt_contract": str(run_rel / "review-prompt-contract.yaml"),
                "status": "completed",
                "started_at": "2026-06-21T00:00:00+00:00",
                "finished_at": "2026-06-21T00:00:01+00:00",
                "provider_model_families": ["internal-agent/codex"],
                "reviewers": [
                    {
                        "reviewer": "generalist-a",
                        "provider": "internal-agent",
                        "model_family": "codex",
                        "packet_path": broken["inputs"]["review_packets"][0]["path"],
                        "report_path": str(report_paths["generalist-a"]),
                        "status": "report-present",
                    },
                    {
                        "reviewer": "generalist-b",
                        "provider": "internal-agent",
                        "model_family": "codex",
                        "packet_path": broken["inputs"]["review_packets"][1]["path"],
                        "report_path": str(report_paths["generalist-b"]),
                        "status": "failed",
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    broken["inputs"]["review_invocation_set"] = str(invocation_set)
    broken["reviewer_assignments"] = [
        {
            "reviewer": "generalist-a",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": broken["inputs"]["review_packets"][0]["path"],
            "report_path": str(report_paths["generalist-a"]),
        },
        {
            "reviewer": "generalist-b",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": broken["inputs"]["review_packets"][1]["path"],
            "report_path": str(report_paths["generalist-b"]),
        },
    ]

    errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, broken)

    assert "review_invocation_set reviewer generalist-b status must be report-present" in "\n".join(errors)


def test_review_prompt_contract_model_diversity_requires_model_evidence(tmp_path) -> None:
    import copy
    import json
    import shutil
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "root"
    root.mkdir()
    for rel in ["schemas", "profiles", "templates/review-prompts"]:
        shutil.copytree(ROOT / rel, root / rel)
    run_rel = Path("examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator")
    shutil.copytree(ROOT / run_rel, root / run_rel)
    contract_path = root / run_rel / "review-prompt-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(contract)

    reports_dir = run_rel / "review-reports"
    (root / reports_dir).mkdir(exist_ok=True)
    internal_report = reports_dir / "reviewer-report.codex-generalist-a.json"
    (root / internal_report).write_text(
        json.dumps(
            {
                "reviewer": {
                    "id": "codex-generalist-a",
                    "provider": "internal-agent",
                    "role": "generalist",
                    "model": "codex",
                },
                "summary": "Internal report.",
                "findings": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    claude_report = reports_dir / "reviewer-report.claude-generalist-b.json"
    (root / claude_report).write_text(
        json.dumps(
            {
                "reviewer": {
                    "id": "claude-generalist-b",
                    "provider": "claude-code",
                    "role": "generalist",
                    "model": "opus",
                },
                "summary": "Claude report.",
                "findings": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    claude_raw = reports_dir / "reviewer-report.claude-generalist-b.raw.json"
    (root / claude_raw).write_text(json.dumps({"type": "result", "result": "{}"}, indent=2), encoding="utf-8")
    claude_invocation = reports_dir / "reviewer-invocation.claude-generalist-b.json"
    (root / claude_invocation).write_text(
        json.dumps(
            {
                "provider": "claude-code",
                "reviewer_role": "generalist",
                "billing_mode": "subscription-local",
                "api_key_usage_forbidden": True,
                "context_policy": {
                    "start_mode": "fresh_context",
                    "fork_conversation_context": False,
                    "session_persistence": False,
                },
                "command": "claude -p <prompt>",
                "requested_model": "opus",
                "requested_effort": "max",
                "provider_models_used": ["claude-sonnet-4"],
                "started_at": "2026-06-21T00:00:00+00:00",
                "finished_at": "2026-06-21T00:00:01+00:00",
                "exit_code": 0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    invocation_set = run_rel / "review-invocation-set.json"
    (root / invocation_set).write_text(
        json.dumps(
            {
                "artifact_kind": "review_invocation_set",
                "review_prompt_contract": str(run_rel / "review-prompt-contract.yaml"),
                "status": "completed",
                "provider_model_families": [
                    "internal-agent/codex",
                    "claude-code/opus",
                ],
                "reviewers": [
                    {
                        "reviewer": "generalist-a",
                        "provider": "internal-agent",
                        "model_family": "codex",
                        "packet_path": broken["inputs"]["review_packets"][0]["path"],
                        "report_path": str(internal_report),
                        "status": "report-present",
                    },
                    {
                        "reviewer": "generalist-b",
                        "provider": "claude-code",
                        "model_family": "opus",
                        "packet_path": broken["inputs"]["review_packets"][1]["path"],
                        "report_path": str(claude_report),
                        "raw_output_path": str(claude_raw),
                        "invocation_metadata_path": str(claude_invocation),
                        "status": "invoked",
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    broken["provider_policy"] = {
        "allow_external_reviewers": True,
        "require_model_diversity": True,
        "min_distinct_provider_model_families": 2,
    }
    broken["inputs"]["review_invocation_set"] = str(invocation_set)
    broken["reviewer_assignments"] = [
        {
            "reviewer": "generalist-a",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": broken["inputs"]["review_packets"][0]["path"],
            "report_path": str(internal_report),
        },
        {
            "reviewer": "generalist-b",
            "provider": "claude-code",
            "model_family": "opus",
            "provider_config": "examples/external-reviewers/claude-code/claude-code.yaml",
            "packet_path": broken["inputs"]["review_packets"][1]["path"],
            "report_path": str(claude_report),
            "raw_output_path": str(claude_raw),
            "invocation_metadata_path": str(claude_invocation),
        },
    ]
    (root / "examples/external-reviewers/claude-code").mkdir(parents=True, exist_ok=True)
    shutil.copy(
        ROOT / "examples/external-reviewers/claude-code/claude-code.yaml",
        root / "examples/external-reviewers/claude-code/claude-code.yaml",
    )

    errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, broken)
    joined = "\n".join(errors)
    assert "provider_models_used" in joined
    assert "review_invocation_set does not prove" in joined


def test_review_prompt_contract_rejects_mock_external_review_evidence(tmp_path) -> None:
    import copy
    import json
    import shutil
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "root"
    root.mkdir()
    for rel in ["schemas", "profiles", "templates/review-prompts"]:
        shutil.copytree(ROOT / rel, root / rel)
    run_rel = Path("examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator")
    shutil.copytree(ROOT / run_rel, root / run_rel)
    contract_path = root / run_rel / "review-prompt-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(contract)
    reports_dir = run_rel / "review-reports"
    (root / reports_dir).mkdir(exist_ok=True)

    internal_report = reports_dir / "reviewer-report.codex-generalist-a.json"
    claude_report = reports_dir / "reviewer-report.claude-generalist-b.json"
    claude_raw = reports_dir / "reviewer-report.claude-generalist-b.raw.json"
    claude_invocation = reports_dir / "reviewer-invocation.claude-generalist-b.json"
    for report, provider, model in [
        (internal_report, "internal-agent", "codex"),
        (claude_report, "claude-code", "opus"),
    ]:
        assigned_reviewer = "generalist-a" if provider == "internal-agent" else "generalist-b"
        reviewer_id = "codex-generalist-a" if provider == "internal-agent" else "claude-generalist-b"
        packet_ref = (
            contract["inputs"]["review_packets"][0]["path"]
            if provider == "internal-agent"
            else contract["inputs"]["review_packets"][1]["path"]
        )
        (root / report).write_text(
            json.dumps(
                {
                    "reviewer": {
                        "id": reviewer_id,
                        "provider": provider,
                        "role": "generalist",
                        "model": model,
                    },
                    "review_context": reviewer_report_context(assigned_reviewer, packet_ref),
                    "summary": "Report.",
                    "findings": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    (root / claude_raw).write_text(json.dumps({"type": "result", "result": "{}"}, indent=2), encoding="utf-8")
    (root / claude_invocation).write_text(
        json.dumps(
            {
                "provider": "claude-code",
                "reviewer_role": "generalist",
                "billing_mode": "subscription-local",
                "api_key_usage_forbidden": True,
                "context_policy": {
                    "start_mode": "fresh_context",
                    "fork_conversation_context": False,
                    "session_persistence": False,
                },
                "command": "mock-response",
                "execution_mode": "mock",
                "requested_model": "opus",
                "requested_effort": "max",
                "provider_models_used": ["claude-opus-4-8"],
                "started_at": "2026-06-21T00:00:00+00:00",
                "finished_at": "2026-06-21T00:00:01+00:00",
                "exit_code": 0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    invocation_set = run_rel / "review-invocation-set.json"
    (root / invocation_set).write_text(
        json.dumps(
            {
                "artifact_kind": "review_invocation_set",
                "review_prompt_contract": str(run_rel / "review-prompt-contract.yaml"),
                "status": "completed",
                "provider_model_families": ["claude-code/opus", "internal-agent/codex"],
                "reviewers": [
                    {
                        "reviewer": "generalist-a",
                        "provider": "internal-agent",
                        "model_family": "codex",
                        "evidence_model_family": "codex",
                        "packet_path": broken["inputs"]["review_packets"][0]["path"],
                        "report_path": str(internal_report),
                        "status": "report-present",
                    },
                    {
                        "reviewer": "generalist-b",
                        "provider": "claude-code",
                        "model_family": "opus",
                        "evidence_model_family": "opus",
                        "packet_path": broken["inputs"]["review_packets"][1]["path"],
                        "report_path": str(claude_report),
                        "raw_output_path": str(claude_raw),
                        "invocation_metadata_path": str(claude_invocation),
                        "execution_mode": "mock",
                        "status": "invoked",
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    broken["provider_policy"] = {
        "allow_external_reviewers": True,
        "require_model_diversity": True,
        "min_distinct_provider_model_families": 2,
    }
    broken["inputs"]["review_invocation_set"] = str(invocation_set)
    broken["reviewer_assignments"] = [
        {
            "reviewer": "generalist-a",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": broken["inputs"]["review_packets"][0]["path"],
            "report_path": str(internal_report),
        },
        {
            "reviewer": "generalist-b",
            "provider": "claude-code",
            "model_family": "opus",
            "provider_config": "examples/external-reviewers/claude-code/claude-code.yaml",
            "packet_path": broken["inputs"]["review_packets"][1]["path"],
            "report_path": str(claude_report),
            "raw_output_path": str(claude_raw),
            "invocation_metadata_path": str(claude_invocation),
        },
    ]
    (root / "examples/external-reviewers/claude-code").mkdir(parents=True, exist_ok=True)
    shutil.copy(
        ROOT / "examples/external-reviewers/claude-code/claude-code.yaml",
        root / "examples/external-reviewers/claude-code/claude-code.yaml",
    )

    errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, broken)
    joined = "\n".join(errors)
    assert "execution_mode must be real" in joined


def test_review_prompt_contract_binds_external_invocation_to_current_artifacts(tmp_path) -> None:
    import copy
    import json
    import shutil
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "root"
    root.mkdir()
    for rel in ["schemas", "profiles", "templates/review-prompts"]:
        shutil.copytree(ROOT / rel, root / rel)
    run_rel = Path("examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator")
    shutil.copytree(ROOT / run_rel, root / run_rel)
    (root / "examples/external-reviewers/claude-code").mkdir(parents=True, exist_ok=True)
    shutil.copy(
        ROOT / "examples/external-reviewers/claude-code/claude-code.yaml",
        root / "examples/external-reviewers/claude-code/claude-code.yaml",
    )
    contract_path = root / run_rel / "review-prompt-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    reports_dir = run_rel / "review-reports"
    (root / reports_dir).mkdir(exist_ok=True)

    internal_report = reports_dir / "reviewer-report.codex-generalist-a.json"
    claude_report = reports_dir / "reviewer-report.claude-generalist-b.json"
    claude_raw = reports_dir / "reviewer-report.claude-generalist-b.raw.json"
    claude_invocation = reports_dir / "reviewer-invocation.claude-generalist-b.json"
    invocation_set = run_rel / "review-invocation-set.json"
    preparation_path = run_rel / "prepared-review-artifacts.json"

    for report, provider, model in [
        (internal_report, "internal-agent", "codex"),
        (claude_report, "claude-code", "opus"),
    ]:
        assigned_reviewer = "generalist-a" if provider == "internal-agent" else "generalist-b"
        reviewer_id = "codex-generalist-a" if provider == "internal-agent" else "claude-generalist-b"
        packet_ref = (
            contract["inputs"]["review_packets"][0]["path"]
            if provider == "internal-agent"
            else contract["inputs"]["review_packets"][1]["path"]
        )
        (root / report).write_text(
            json.dumps(
                {
                    "reviewer": {
                        "id": reviewer_id,
                        "provider": provider,
                        "role": "generalist",
                        "model": model,
                    },
                    "review_context": reviewer_report_context(assigned_reviewer, packet_ref),
                    "summary": "Report.",
                    "findings": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    (root / claude_raw).write_text(json.dumps({"type": "result", "result": "{}"}, indent=2), encoding="utf-8")

    contract["provider_policy"] = {
        "allow_external_reviewers": True,
        "require_model_diversity": True,
        "min_distinct_provider_model_families": 2,
    }
    contract["inputs"]["artifact_preparation_report"] = str(preparation_path)
    contract["inputs"]["review_invocation_set"] = str(invocation_set)
    contract["reviewer_assignments"] = [
        {
            "reviewer": "generalist-a",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": contract["inputs"]["review_packets"][0]["path"],
            "report_path": str(internal_report),
        },
        {
            "reviewer": "generalist-b",
            "provider": "claude-code",
            "model_family": "opus",
            "provider_config": "examples/external-reviewers/claude-code/claude-code.yaml",
            "packet_path": contract["inputs"]["review_packets"][1]["path"],
            "report_path": str(claude_report),
            "raw_output_path": str(claude_raw),
            "invocation_metadata_path": str(claude_invocation),
        },
    ]
    for reviewer in ["generalist-a", "generalist-b"]:
        (root / run_rel / f"reviewer-report.{reviewer}.json").write_text(
            json.dumps(
                {
                    "reviewer": {
                        "id": reviewer,
                        "provider": "internal-agent",
                        "role": "generalist",
                        "model": "codex",
                    },
                    "review_context": reviewer_report_context(
                        reviewer,
                        contract["inputs"]["review_packets"][0 if reviewer == "generalist-a" else 1]["path"],
                    ),
                    "summary": "Internal reviewer artifact.",
                    "findings": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    prompt_hash = next(
        item["prompt_hash"] for item in contract["rendered_prompts"] if item["reviewer"] == "generalist-b"
    )
    packet_hash = "sha256:" + __import__("hashlib").sha256(
        (root / contract["inputs"]["review_packets"][1]["path"]).read_bytes()
    ).hexdigest()
    role_hash = "sha256:" + __import__("hashlib").sha256(
        (root / "profiles/reviewer_roles/generalist.yaml").read_bytes()
    ).hexdigest()
    schema_hash = "sha256:" + __import__("hashlib").sha256(
        (root / "schemas/reviewer-report.schema.json").read_bytes()
    ).hexdigest()
    raw_hash = "sha256:" + __import__("hashlib").sha256((root / claude_raw).read_bytes()).hexdigest()
    normalized_hash = "sha256:" + __import__("hashlib").sha256((root / claude_report).read_bytes()).hexdigest()
    contract_hash = "sha256:" + __import__("hashlib").sha256(contract_path.read_bytes()).hexdigest()
    rubric_hash = validate_repo.sha256_text(json.dumps(contract["prompt_policy"], sort_keys=True))
    (root / preparation_path).write_text(
        json.dumps(
            {
                "version": 1,
                "artifact_kind": "review_artifact_preparation",
                "artifact_scope": "run",
                "status": "completed",
                "review_prompt_contract": {
                    "path": str(run_rel / "review-prompt-contract.yaml"),
                    "hash": contract_hash,
                },
                "source_context": {
                    "dirty_policy": "fail-closed",
                    "worktree": {
                        "status_command": "git status --porcelain=v1 --untracked-files=all",
                        "status_entries": [],
                        "included_dirty_paths": [],
                        "excluded_dirty_paths": [],
                    },
                },
                "input_artifacts": [
                    {
                        "path": contract["inputs"]["task_contract"],
                        "kind": "task_contract",
                        "hash": validate_repo.sha256_file(root / contract["inputs"]["task_contract"]),
                    }
                ],
                "generated_artifacts": {
                    "shared_packet_content": {
                        "path": str(run_rel / "review-packets/shared-content.json"),
                        "hash": validate_repo.sha256_file(root / run_rel / "review-packets/shared-content.json"),
                    },
                    "review_packets": [
                        {
                            "reviewer": item["reviewer"],
                            "path": item["path"],
                            "hash": validate_repo.sha256_file(root / item["path"]),
                            "shared_packet_content_hash": item.get("shared_packet_content_hash"),
                        }
                        for item in contract["inputs"]["review_packets"]
                    ],
                    "rendered_prompts": [
                        {
                            "reviewer": item["reviewer"],
                            "path": item["prompt_path"],
                            "hash": validate_repo.sha256_file(root / item["prompt_path"]),
                            "packet_hash": item["packet_hash"],
                            "schema_hash": item["schema_hash"],
                            "rubric_hash": item["rubric_hash"],
                            "role_contract_hash": item["role_contract_hash"],
                        }
                        for item in contract["rendered_prompts"]
                    ],
                    "review_invocation_set": {
                        "path": str(invocation_set),
                        "status": "completed",
                    },
                },
                "reviewer_assignments": contract["reviewer_assignments"],
                "validation": {
                    "schema": "schemas/review-artifact-preparation.schema.json",
                    "deterministic_script": "scripts/reviewers/prepare_review_set_artifacts.py",
                    "script_contract": "scripts/contracts/prepare_review_set_artifacts.yaml",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    valid_invocation = {
        "provider": "claude-code",
        "reviewer_role": "generalist",
        "billing_mode": "subscription-local",
        "api_key_usage_forbidden": True,
        "context_policy": {
                "start_mode": "fresh_context",
                "fork_conversation_context": False,
                "session_persistence": False,
            },
            "forbidden_env_checked": [
                "ANTHROPIC_API_KEY",
                "ANTHROPIC_AUTH_TOKEN",
                "ANTHROPIC_BASE_URL",
                "CLAUDE_CODE_USE_BEDROCK",
                "CLAUDE_CODE_USE_VERTEX",
            ],
            "command": "claude -p <prompt> --tools \"\"",
            "wrapper": "scripts/reviewers/run_external_reviewer.py",
            "provider_config_path": "examples/external-reviewers/claude-code/claude-code.yaml",
            "provider_config_hash": validate_repo.sha256_file(
                root / "examples/external-reviewers/claude-code/claude-code.yaml"
            ),
            "execution_mode": "real",
            "permission_mode": "default",
            "prompt_transport": "stdin",
            "sandbox_mode": "require_escalated",
            "tools": "",
            "output_format": "json",
            "requested_model": "opus",
            "requested_effort": "max",
        "provider_models_used": ["claude-opus-4-8"],
        "input_hash": packet_hash,
        "prompt_hash": prompt_hash,
        "review_prompt_contract_hash": contract_hash,
        "role_contract_hash": role_hash,
        "rubric_hash": rubric_hash,
        "schema_hash": schema_hash,
        "raw_output_path": str(claude_raw),
        "raw_output_hash": raw_hash,
        "normalized_output_path": str(claude_report),
        "normalized_output_hash": normalized_hash,
        "started_at": "2026-06-21T00:00:00+00:00",
        "finished_at": "2026-06-21T00:00:01+00:00",
        "exit_code": 0,
    }
    (root / claude_invocation).write_text(json.dumps(valid_invocation, indent=2), encoding="utf-8")
    (root / invocation_set).write_text(
        json.dumps(
            {
                "artifact_kind": "review_invocation_set",
                "review_prompt_contract": str(run_rel / "review-prompt-contract.yaml"),
                "review_prompt_contract_hash": contract_hash,
                "status": "completed",
                "started_at": "2026-06-21T00:00:00+00:00",
                "finished_at": "2026-06-21T00:00:01+00:00",
                "runner_scheduling": "external-first-async",
                "provider_model_families": ["claude-code/opus", "internal-agent/codex"],
                "reviewers": [
                    {
                        "reviewer": "generalist-a",
                        "provider": "internal-agent",
                        "model_family": "codex",
                        "evidence_model_family": "codex",
                        "packet_path": contract["inputs"]["review_packets"][0]["path"],
                        "packet_hash": validate_repo.sha256_file(root / contract["inputs"]["review_packets"][0]["path"]),
                        "report_path": str(internal_report),
                        "report_hash": validate_repo.sha256_file(root / internal_report),
                        "status": "report-present",
                    },
                    {
                        "reviewer": "generalist-b",
                        "provider": "claude-code",
                        "model_family": "opus",
                        "evidence_model_family": "opus",
                        "packet_path": contract["inputs"]["review_packets"][1]["path"],
                        "packet_hash": packet_hash,
                        "report_path": str(claude_report),
                        "report_hash": normalized_hash,
                        "raw_output_path": str(claude_raw),
                        "invocation_metadata_path": str(claude_invocation),
                        "execution_mode": "real",
                        "status": "invoked",
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, contract)
    assert not errors

    stale_invocation_set = json.loads((root / invocation_set).read_text(encoding="utf-8"))
    stale_invocation_set["review_prompt_contract_hash"] = "sha256:" + "0" * 64
    (root / invocation_set).write_text(json.dumps(stale_invocation_set, indent=2), encoding="utf-8")
    errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, contract)
    assert "review_invocation_set.review_prompt_contract_hash hash mismatch" in "\n".join(errors)

    stale_invocation_set["review_prompt_contract_hash"] = contract_hash
    for reviewer_entry in stale_invocation_set["reviewers"]:
        if reviewer_entry["reviewer"] == "generalist-a":
            reviewer_entry["packet_hash"] = "sha256:" + "0" * 64
    (root / invocation_set).write_text(json.dumps(stale_invocation_set, indent=2), encoding="utf-8")
    errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, contract)
    assert "review_invocation_set reviewer generalist-a packet_hash hash mismatch" in "\n".join(errors)

    for reviewer_entry in stale_invocation_set["reviewers"]:
        if reviewer_entry["reviewer"] == "generalist-a":
            reviewer_entry["packet_hash"] = validate_repo.sha256_file(root / contract["inputs"]["review_packets"][0]["path"])
    (root / invocation_set).write_text(json.dumps(stale_invocation_set, indent=2), encoding="utf-8")

    skip_raw_invocation = copy.deepcopy(valid_invocation)
    skip_raw_invocation["raw_output_path"] = ""
    skip_raw_invocation["raw_output_hash"] = "sha256:" + "1" * 64
    (root / claude_invocation).write_text(json.dumps(skip_raw_invocation, indent=2), encoding="utf-8")
    invocation_set_data = json.loads((root / invocation_set).read_text(encoding="utf-8"))
    for reviewer_entry in invocation_set_data["reviewers"]:
        if reviewer_entry["reviewer"] == "generalist-b":
            reviewer_entry["raw_output_path"] = ""
            reviewer_entry["raw_output_hash"] = skip_raw_invocation["raw_output_hash"]
    (root / invocation_set).write_text(json.dumps(invocation_set_data, indent=2), encoding="utf-8")
    (root / claude_raw).unlink()
    errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, contract)
    assert not errors

    (root / claude_raw).write_text(json.dumps({"type": "result", "result": "{}"}, indent=2), encoding="utf-8")
    (root / claude_invocation).write_text(json.dumps(valid_invocation, indent=2), encoding="utf-8")
    for reviewer_entry in invocation_set_data["reviewers"]:
        if reviewer_entry["reviewer"] == "generalist-b":
            reviewer_entry["raw_output_path"] = str(claude_raw)
            reviewer_entry["raw_output_hash"] = raw_hash
    (root / invocation_set).write_text(json.dumps(invocation_set_data, indent=2), encoding="utf-8")

    stale_internal_context = json.loads((root / internal_report).read_text(encoding="utf-8"))
    stale_internal_context["review_context"]["run_id"] = "older-run"
    (root / internal_report).write_text(json.dumps(stale_internal_context, indent=2), encoding="utf-8")
    errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, contract)
    assert "review_context.run_id must match packet" in "\n".join(errors)

    stale_internal_context["review_context"] = reviewer_report_context(
        "generalist-a",
        contract["inputs"]["review_packets"][0]["path"],
    )
    stale_internal_context["review_context"].pop("reviewer_instance_id")
    (root / internal_report).write_text(json.dumps(stale_internal_context, indent=2), encoding="utf-8")
    errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, contract)
    assert "review_context.reviewer_instance_id must match assignment" in "\n".join(errors)

    stale_internal_context["review_context"] = reviewer_report_context(
        "generalist-a",
        contract["inputs"]["review_packets"][0]["path"],
    )
    (root / internal_report).write_text(json.dumps(stale_internal_context, indent=2), encoding="utf-8")

    stale_hash = copy.deepcopy(valid_invocation)
    stale_hash["input_hash"] = "sha256:" + "0" * 64
    (root / claude_invocation).write_text(json.dumps(stale_hash, indent=2), encoding="utf-8")
    errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, contract)
    assert "input_hash must match current review artifact" in "\n".join(errors)

    failed_invocation = copy.deepcopy(valid_invocation)
    failed_invocation["exit_code"] = 1
    (root / claude_invocation).write_text(json.dumps(failed_invocation, indent=2), encoding="utf-8")
    errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, contract)
    assert "exit_code must be 0" in "\n".join(errors)

    stale_output_hash = copy.deepcopy(valid_invocation)
    stale_output_hash["normalized_output_hash"] = "sha256:" + "0" * 64
    (root / claude_invocation).write_text(json.dumps(stale_output_hash, indent=2), encoding="utf-8")
    errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, contract)
    assert "normalized_output_hash must match current review artifact" in "\n".join(errors)

    (root / claude_invocation).write_text(json.dumps(valid_invocation, indent=2), encoding="utf-8")
    stale_report_identity = {
        "reviewer": {
            "id": "claude-generalist-stale",
            "provider": "claude-code",
            "role": "generalist",
            "model": "opus",
        },
        "summary": "Claude report.",
        "findings": [],
    }
    (root / claude_report).write_text(json.dumps(stale_report_identity, indent=2), encoding="utf-8")
    errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, contract)
    assert "reviewer.id must include assigned reviewer generalist-b" in "\n".join(errors)


def test_run_review_set_mixed_internal_and_claude_mock(tmp_path) -> None:
    import json

    import yaml

    source_contract_path = (
        ROOT
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-prompt-contract.yaml"
    )
    contract = yaml.safe_load(source_contract_path.read_text(encoding="utf-8"))
    internal_report_a = tmp_path / "reviewer-report.internal-generalist-a.json"
    internal_report_b = tmp_path / "reviewer-report.internal-generalist-b.json"
    for report, reviewer_id in [
        (internal_report_a, "codex-generalist-a"),
        (internal_report_b, "codex-generalist-b"),
    ]:
        report.write_text(
            json.dumps(
                {
                    "reviewer": {
                        "id": reviewer_id,
                        "provider": "internal-agent",
                        "role": "generalist",
                        "model": "gpt-5-codex",
                    },
                    "review_context": reviewer_report_context(
                        reviewer_id.removeprefix("codex-"),
                        contract["inputs"]["review_packets"][0 if reviewer_id.endswith("-a") else 1]["path"],
                    ),
                    "summary": "Internal reviewer artifact exists.",
                    "findings": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    external_raw = tmp_path / "mock-claude-generalist-b.raw.json"
    external_raw.write_text(
        json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "result": json.dumps(
                    {
                        "reviewer": {
                            "id": "claude-generalist-b",
                            "provider": "claude-code",
                            "role": "generalist",
                            "model": "opus",
                        },
                        "summary": "Claude reviewer mock artifact exists.",
                        "findings": [],
                    }
                ),
                "modelUsage": {
                    "claude-opus-latest": {
                        "inputTokens": 1,
                        "outputTokens": 1,
                    }
                },
                "total_cost_usd": 0.0,
                "usage": {
                    "service_tier": "standard",
                    "speed": "standard",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    external_report = tmp_path / "reviewer-report.claude-generalist-b.json"
    external_raw_output = tmp_path / "reviewer-report.claude-generalist-b.raw.json"
    external_invocation = tmp_path / "reviewer-invocation.claude-generalist-b.json"
    output = tmp_path / "review-invocation-set.json"
    contract["provider_policy"] = {
        "allow_external_reviewers": True,
        "require_model_diversity": True,
        "min_distinct_provider_model_families": 2,
    }
    contract["inputs"]["review_invocation_set"] = str(output)
    contract["reviewer_assignments"] = [
        {
            "reviewer": "generalist-a",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": contract["inputs"]["review_packets"][0]["path"],
            "report_path": str(internal_report_a),
        },
        {
            "reviewer": "generalist-b",
            "provider": "claude-code",
            "model_family": "opus",
            "provider_config": "examples/external-reviewers/claude-code/claude-code.yaml",
            "packet_path": contract["inputs"]["review_packets"][1]["path"],
            "report_path": str(external_report),
            "raw_output_path": str(external_raw_output),
            "invocation_metadata_path": str(external_invocation),
        },
    ]
    contract_path = tmp_path / "review-prompt-contract.yaml"
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    result = run(
        "scripts/reviewers/run_review_set.py",
        "--contract", str(contract_path),
        "--output", str(output),
        "--mock-response", f"generalist-b={external_raw}",
        env=clean_env(),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["status"] == "completed"
    assert data["provider_model_families"] == ["claude-code/opus", "internal-agent/codex"]
    internal_entry = next(item for item in data["reviewers"] if item["provider"] == "internal-agent")
    assert internal_entry["evidence_model_family"] == "codex"
    external_entry = next(item for item in data["reviewers"] if item["provider"] == "claude-code")
    assert external_entry["execution_mode"] == "mock"
    assert external_report.exists()
    assert external_invocation.exists()

    stale_internal = json.loads(internal_report_a.read_text(encoding="utf-8"))
    stale_internal["review_context"]["run_id"] = "older-run"
    internal_report_a.write_text(json.dumps(stale_internal, indent=2) + "\n", encoding="utf-8")
    stale_result = run(
        "scripts/reviewers/run_review_set.py",
        "--contract", str(contract_path),
        "--output", str(output),
        "--mock-response", f"generalist-b={external_raw}",
        env=clean_env(),
    )
    assert stale_result.returncode == 2
    assert "review_context.run_id must match packet" in (stale_result.stdout + stale_result.stderr)


def test_run_review_set_starts_external_reviewers_asynchronously(tmp_path) -> None:
    import json
    import subprocess
    import time

    import yaml

    root = tmp_path / "review-root"
    run_dir = root / "Docs" / "agentsflow" / "runs" / "async-review-set"
    scripts_dir = root / "scripts" / "reviewers"
    (scripts_dir).mkdir(parents=True)
    (root / "schemas").mkdir()
    (root / "examples" / "external-reviewers" / "claude-code").mkdir(parents=True)
    for schema_name in [
        "reviewer-report.schema.json",
        "review-invocation-set.schema.json",
        "review-artifact-preparation.schema.json",
    ]:
        (root / "schemas" / schema_name).write_text(
            (ROOT / "schemas" / schema_name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    fake_wrapper = scripts_dir / "run_external_reviewer.py"
    fake_wrapper.write_text(
        """
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import time
from pathlib import Path


def sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument("--provider")
parser.add_argument("--config")
parser.add_argument("--input")
parser.add_argument("--output")
parser.add_argument("--raw-output")
parser.add_argument("--invocation-output")
args = parser.parse_args()
reviewer = Path(args.output).name.removeprefix("reviewer-report.").removesuffix(".json")
log_path = Path(os.environ["AF_ASYNC_REVIEW_LOG"])
with log_path.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps({"event": "start", "reviewer": reviewer, "time": time.monotonic()}) + "\\n")
time.sleep(0.6)
report_path = Path(args.output)
raw_path = Path(args.raw_output)
invocation_path = Path(args.invocation_output)
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps({
    "reviewer": {"id": "claude-" + reviewer, "provider": "claude-code", "role": "generalist", "model": "opus"},
    "summary": "Fake async external reviewer.",
    "findings": []
}, indent=2) + "\\n", encoding="utf-8")
raw_path.write_text(json.dumps({"result": "ok"}) + "\\n", encoding="utf-8")
now = dt.datetime.now(dt.timezone.utc).isoformat()
invocation_path.write_text(json.dumps({
    "provider": "claude-code",
    "reviewer_role": "generalist",
    "billing_mode": "subscription-local",
    "api_key_usage_forbidden": True,
    "context_policy": {"start_mode": "fresh_context", "fork_conversation_context": False, "session_persistence": False},
    "command": "fake",
    "execution_mode": "mock",
    "requested_model": "opus",
    "requested_effort": "max",
    "provider_models_used": ["claude-opus-latest"],
    "started_at": now,
    "finished_at": now,
    "exit_code": 0,
    "raw_output_hash": sha(raw_path),
    "normalized_output_hash": sha(report_path)
}, indent=2) + "\\n", encoding="utf-8")
""",
        encoding="utf-8",
    )
    (root / "examples/external-reviewers/claude-code/claude-code.yaml").write_text("provider: claude-code\n", encoding="utf-8")
    for reviewer in ["claude-a", "claude-b"]:
        (run_dir / "review-packets").mkdir(parents=True, exist_ok=True)
        (run_dir / "review-packets" / f"{reviewer}.json").write_text("{}", encoding="utf-8")
    internal_report = run_dir / "reports" / "reviewer-report.codex-verification.json"
    internal_report.parent.mkdir(parents=True, exist_ok=True)
    internal_report_payload = {
        "reviewer": {
            "id": "codex-codex-verification",
            "provider": "internal-agent",
            "role": "verification",
            "model": "codex",
        },
        "review_context": reviewer_report_context(
            "codex-verification",
            "Docs/agentsflow/runs/async-review-set/review-packets/claude-a.json",
        ),
        "summary": "Internal report.",
        "findings": [],
    }
    output = run_dir / "review-invocation-set.json"
    contract = {
        "reviewer_set": [
            {"instance_id": "claude-a"},
            {"instance_id": "codex-verification"},
            {"instance_id": "claude-b"},
        ],
        "provider_policy": {
            "allow_external_reviewers": True,
            "require_model_diversity": True,
            "min_distinct_provider_model_families": 2,
        },
        "inputs": {
            "review_invocation_set": str(output.relative_to(root)),
        },
        "reviewer_assignments": [
            {
                "reviewer": "claude-a",
                "provider": "claude-code",
                "model_family": "opus",
                "provider_config": "examples/external-reviewers/claude-code/claude-code.yaml",
                "packet_path": "Docs/agentsflow/runs/async-review-set/review-packets/claude-a.json",
                "report_path": "Docs/agentsflow/runs/async-review-set/reports/reviewer-report.claude-a.json",
                "raw_output_path": "Docs/agentsflow/runs/async-review-set/reports/reviewer-report.claude-a.raw.json",
                "invocation_metadata_path": "Docs/agentsflow/runs/async-review-set/reports/reviewer-invocation.claude-a.json",
            },
            {
                "reviewer": "codex-verification",
                "provider": "internal-agent",
                "model_family": "codex",
                "packet_path": "Docs/agentsflow/runs/async-review-set/review-packets/claude-a.json",
                "report_path": str(internal_report.relative_to(root)),
            },
            {
                "reviewer": "claude-b",
                "provider": "claude-code",
                "model_family": "opus",
                "provider_config": "examples/external-reviewers/claude-code/claude-code.yaml",
                "packet_path": "Docs/agentsflow/runs/async-review-set/review-packets/claude-b.json",
                "report_path": "Docs/agentsflow/runs/async-review-set/reports/reviewer-report.claude-b.json",
                "raw_output_path": "Docs/agentsflow/runs/async-review-set/reports/reviewer-report.claude-b.raw.json",
                "invocation_metadata_path": "Docs/agentsflow/runs/async-review-set/reports/reviewer-invocation.claude-b.json",
            },
        ],
    }
    contract_path = run_dir / "review-prompt-contract.yaml"
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    log_path = tmp_path / "async-starts.jsonl"
    env = clean_env()
    env["AF_ASYNC_REVIEW_LOG"] = str(log_path)
    started = time.monotonic()
    delayed_internal = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import json, pathlib, time; "
                "time.sleep(0.2); "
                f"pathlib.Path({str(internal_report)!r}).write_text("
                f"json.dumps({internal_report_payload!r}, indent=2) + '\\n', encoding='utf-8')"
            ),
        ]
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "reviewers" / "run_review_set.py"),
            "--contract",
            str(contract_path.relative_to(root)),
            "--output",
            str(output.relative_to(root)),
            "--internal-report-wait-seconds",
            "5",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        env=env,
    )
    delayed_internal.wait(timeout=5)
    elapsed = time.monotonic() - started
    assert result.returncode == 0, result.stdout + result.stderr
    starts = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert sorted(event["reviewer"] for event in starts) == ["claude-a", "claude-b"]
    assert abs(starts[1]["time"] - starts[0]["time"]) < 0.5
    assert elapsed < 1.4
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["runner_scheduling"] == "external-first-async"
    assert data["status"] == "completed"


def test_run_review_set_times_out_hung_external_without_losing_completed_peer(tmp_path) -> None:
    import json
    import jsonschema
    import subprocess
    import time

    import yaml

    root = tmp_path / "review-root"
    run_dir = root / "Docs" / "agentsflow" / "runs" / "timeout-review-set"
    scripts_dir = root / "scripts" / "reviewers"
    scripts_dir.mkdir(parents=True)
    (root / "schemas").mkdir()
    (root / "examples" / "external-reviewers" / "claude-code").mkdir(parents=True)
    for schema_name in [
        "reviewer-report.schema.json",
        "review-invocation-set.schema.json",
        "review-artifact-preparation.schema.json",
    ]:
        (root / "schemas" / schema_name).write_text(
            (ROOT / "schemas" / schema_name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    fake_wrapper = scripts_dir / "run_external_reviewer.py"
    fake_wrapper.write_text(
        """
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import time
from pathlib import Path


def sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument("--provider")
parser.add_argument("--config")
parser.add_argument("--input")
parser.add_argument("--output")
parser.add_argument("--raw-output")
parser.add_argument("--invocation-output")
args = parser.parse_args()
reviewer = Path(args.output).name.removeprefix("reviewer-report.").removesuffix(".json")
if reviewer == "claude-hung":
    time.sleep(5)
report_path = Path(args.output)
raw_path = Path(args.raw_output)
invocation_path = Path(args.invocation_output)
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps({
    "reviewer": {"id": "claude-" + reviewer, "provider": "claude-code", "role": "generalist", "model": "opus"},
    "summary": "Fake external reviewer.",
    "findings": []
}, indent=2) + "\\n", encoding="utf-8")
raw_path.write_text(json.dumps({"result": "ok"}) + "\\n", encoding="utf-8")
now = dt.datetime.now(dt.timezone.utc).isoformat()
invocation_path.write_text(json.dumps({
    "provider": "claude-code",
    "reviewer_role": "generalist",
    "billing_mode": "subscription-local",
    "api_key_usage_forbidden": True,
    "context_policy": {"start_mode": "fresh_context", "fork_conversation_context": False, "session_persistence": False},
    "command": "fake",
    "execution_mode": "mock",
    "requested_model": "opus",
    "requested_effort": "max",
    "provider_models_used": ["claude-opus-latest"],
    "started_at": now,
    "finished_at": now,
    "exit_code": 0,
    "raw_output_hash": sha(raw_path),
    "normalized_output_hash": sha(report_path)
}, indent=2) + "\\n", encoding="utf-8")
""",
        encoding="utf-8",
    )
    (root / "examples/external-reviewers/claude-code/claude-code.yaml").write_text("provider: claude-code\n", encoding="utf-8")
    for reviewer in ["claude-ok", "claude-hung"]:
        (run_dir / "review-packets").mkdir(parents=True, exist_ok=True)
        (run_dir / "review-packets" / f"{reviewer}.json").write_text("{}", encoding="utf-8")
    output = run_dir / "review-invocation-set.json"
    contract = {
        "reviewer_set": [{"instance_id": "claude-ok"}, {"instance_id": "claude-hung"}],
        "provider_policy": {"allow_external_reviewers": True, "require_model_diversity": False},
        "inputs": {
            "review_invocation_set": str(output.relative_to(root)),
        },
        "reviewer_assignments": [
            {
                "reviewer": "claude-ok",
                "provider": "claude-code",
                "model_family": "opus",
                "provider_config": "examples/external-reviewers/claude-code/claude-code.yaml",
                "packet_path": "Docs/agentsflow/runs/timeout-review-set/review-packets/claude-ok.json",
                "report_path": "Docs/agentsflow/runs/timeout-review-set/reports/reviewer-report.claude-ok.json",
                "raw_output_path": "Docs/agentsflow/runs/timeout-review-set/reports/reviewer-report.claude-ok.raw.json",
                "invocation_metadata_path": "Docs/agentsflow/runs/timeout-review-set/reports/reviewer-invocation.claude-ok.json",
            },
            {
                "reviewer": "claude-hung",
                "provider": "claude-code",
                "model_family": "opus",
                "provider_config": "examples/external-reviewers/claude-code/claude-code.yaml",
                "packet_path": "Docs/agentsflow/runs/timeout-review-set/review-packets/claude-hung.json",
                "report_path": "Docs/agentsflow/runs/timeout-review-set/reports/reviewer-report.claude-hung.json",
                "raw_output_path": "Docs/agentsflow/runs/timeout-review-set/reports/reviewer-report.claude-hung.raw.json",
                "invocation_metadata_path": "Docs/agentsflow/runs/timeout-review-set/reports/reviewer-invocation.claude-hung.json",
            },
        ],
    }
    contract_path = run_dir / "review-prompt-contract.yaml"
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    started = time.monotonic()
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "reviewers" / "run_review_set.py"),
            "--contract",
            str(contract_path.relative_to(root)),
            "--output",
            str(output.relative_to(root)),
            "--external-reviewer-timeout-seconds",
            "0.5",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        env=clean_env(),
    )
    elapsed = time.monotonic() - started

    assert result.returncode == 2
    assert elapsed < 3
    data = json.loads(output.read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas/review-invocation-set.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(data)
    assert data["status"] == "failed"
    ok_entry = next(item for item in data["reviewers"] if item["reviewer"] == "claude-ok")
    hung_entry = next(item for item in data["reviewers"] if item["reviewer"] == "claude-hung")
    assert ok_entry["status"] == "invoked"
    assert hung_entry["status"] == "timed-out"
    assert "timed out" in hung_entry["error"]
    assert (run_dir / "reports" / "reviewer-report.claude-ok.json").exists()


def test_run_review_set_failure_writes_schema_valid_evidence(tmp_path) -> None:
    import json

    import jsonschema
    import yaml

    source_contract_path = (
        ROOT
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-prompt-contract.yaml"
    )
    contract = yaml.safe_load(source_contract_path.read_text(encoding="utf-8"))
    output = tmp_path / "review-invocation-set.failed.json"
    contract["inputs"]["review_invocation_set"] = str(output)
    missing_internal_report = tmp_path / "missing-internal-report.json"
    contract["reviewer_assignments"] = [
        {
            "reviewer": "generalist-a",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": contract["inputs"]["review_packets"][0]["path"],
            "report_path": str(missing_internal_report),
        },
        {
            "reviewer": "generalist-b",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": contract["inputs"]["review_packets"][1]["path"],
            "report_path": str(tmp_path / "also-missing.json"),
        },
    ]
    contract_path = tmp_path / "review-prompt-contract.yaml"
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    result = run(
        "scripts/reviewers/run_review_set.py",
        "--contract",
        str(contract_path),
        "--output",
        str(output),
        env=clean_env(),
    )

    assert result.returncode == 2
    data = json.loads(output.read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas/review-invocation-set.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(data)
    assert data["status"] == "failed"
    assert data["error"]
    assert data["reviewers"][0]["reviewer"] == "generalist-a"
    assert data["reviewers"][0]["status"] == "failed"
    assert data["reviewers"][0]["error"]


def test_run_review_set_rejects_aliased_evidence_and_invocation_set(tmp_path) -> None:
    import yaml

    source_contract_path = (
        ROOT
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-prompt-contract.yaml"
    )
    contract = yaml.safe_load(source_contract_path.read_text(encoding="utf-8"))
    output = tmp_path / "review-invocation-set.json"
    contract["inputs"]["review_invocation_set"] = str(output)
    contract["inputs"]["evidence_report"] = str(output)
    contract["reviewer_assignments"] = [
        {
            "reviewer": "generalist-a",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": contract["inputs"]["review_packets"][0]["path"],
            "report_path": str(tmp_path / "reviewer-report.internal-generalist-a.json"),
        },
        {
            "reviewer": "generalist-b",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": contract["inputs"]["review_packets"][1]["path"],
            "report_path": str(tmp_path / "reviewer-report.internal-generalist-b.json"),
        },
    ]
    contract_path = tmp_path / "review-prompt-contract.yaml"
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    result = run(
        "scripts/reviewers/run_review_set.py",
        "--contract",
        str(contract_path),
        "--output",
        str(output),
        env=clean_env(),
    )

    assert result.returncode == 2
    assert "inputs.evidence_report must not match inputs.review_invocation_set" in (result.stdout + result.stderr)


def test_run_review_set_requires_output_to_match_review_invocation_set(tmp_path) -> None:
    import json

    import yaml

    source_contract_path = (
        ROOT
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-prompt-contract.yaml"
    )
    contract = yaml.safe_load(source_contract_path.read_text(encoding="utf-8"))
    internal_report_a = tmp_path / "reviewer-report.internal-generalist-a.json"
    internal_report_b = tmp_path / "reviewer-report.internal-generalist-b.json"
    for report, reviewer_id in [
        (internal_report_a, "codex-generalist-a"),
        (internal_report_b, "codex-generalist-b"),
    ]:
        report.write_text(
            json.dumps(
                {
                    "reviewer": {
                        "id": reviewer_id,
                        "provider": "internal-agent",
                        "role": "generalist",
                        "model": "codex",
                    },
                    "summary": "Internal reviewer artifact exists.",
                    "findings": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    contract["inputs"]["review_invocation_set"] = str(tmp_path / "expected-review-invocation-set.json")
    contract["reviewer_assignments"] = [
        {
            "reviewer": "generalist-a",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": contract["inputs"]["review_packets"][0]["path"],
            "report_path": str(internal_report_a),
        },
        {
            "reviewer": "generalist-b",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": contract["inputs"]["review_packets"][1]["path"],
            "report_path": str(internal_report_b),
        },
    ]
    contract_path = tmp_path / "review-prompt-contract.yaml"
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    wrong_output = tmp_path / "wrong-review-invocation-set.json"

    result = run(
        "scripts/reviewers/run_review_set.py",
        "--contract",
        str(contract_path),
        "--output",
        str(wrong_output),
        env=clean_env(),
    )

    assert result.returncode == 2
    assert "--output must match inputs.review_invocation_set" in (result.stdout + result.stderr)


def test_run_review_set_rejects_duplicate_report_paths(tmp_path) -> None:
    import json

    import yaml

    source_contract_path = (
        ROOT
        / "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/review-prompt-contract.yaml"
    )
    contract = yaml.safe_load(source_contract_path.read_text(encoding="utf-8"))
    output = tmp_path / "review-invocation-set.json"
    shared_report = tmp_path / "reviewer-report.shared.json"
    shared_report.write_text(
        json.dumps(
            {
                "reviewer": {
                    "id": "codex-generalist-a",
                    "provider": "internal-agent",
                    "role": "generalist",
                    "model": "codex",
                },
                "summary": "Shared reviewer artifact.",
                "findings": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    contract["inputs"]["review_invocation_set"] = str(output)
    contract["reviewer_assignments"] = [
        {
            "reviewer": "generalist-a",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": contract["inputs"]["review_packets"][0]["path"],
            "report_path": str(shared_report),
        },
        {
            "reviewer": "generalist-b",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": contract["inputs"]["review_packets"][1]["path"],
            "report_path": str(shared_report),
        },
    ]
    contract_path = tmp_path / "review-prompt-contract.yaml"
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    result = run(
        "scripts/reviewers/run_review_set.py",
        "--contract",
        str(contract_path),
        "--output",
        str(output),
        env=clean_env(),
    )

    assert result.returncode == 2
    assert "report_path values must be unique" in (result.stdout + result.stderr)


def test_review_artifact_preparation_schema_passes() -> None:
    import json

    import jsonschema

    schema = json.loads((ROOT / "schemas/review-artifact-preparation.schema.json").read_text(encoding="utf-8"))
    template = json.loads((ROOT / "templates/review-artifact-preparation.json").read_text(encoding="utf-8"))

    jsonschema.Draft202012Validator(schema).validate(template)


def test_review_prompt_contract_rejects_markdown_reviewer_report_gate_path() -> None:
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
    broken["provider_policy"] = {
        "allow_external_reviewers": False,
        "require_model_diversity": False,
    }
    broken["reviewer_assignments"] = [
        {
            "reviewer": "generalist-a",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": broken["inputs"]["review_packets"][0]["path"],
            "report_path": "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/reviewer-report.generalist-a.md",
        },
        {
            "reviewer": "generalist-b",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": broken["inputs"]["review_packets"][1]["path"],
            "report_path": "examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator/reviewer-report.generalist-b.json",
        },
    ]

    errors = validate_repo.validate_review_prompt_contract_run_references(ROOT, path, broken)

    assert "reviewer_assignments[0].report_path must be a JSON reviewer report" in "\n".join(errors)


def test_review_prompt_contract_rejects_aliased_evidence_and_invocation_set(tmp_path) -> None:
    import copy
    import json
    import shutil
    import sys

    import yaml

    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_repo  # noqa: PLC0415

    root = tmp_path / "root"
    root.mkdir()
    for rel in ["schemas", "profiles", "templates/review-prompts"]:
        shutil.copytree(ROOT / rel, root / rel)
    run_rel = Path("examples/e2e/minimal-python-project/Docs/agentsflow/runs/2026-06-17-add-calculator")
    shutil.copytree(ROOT / run_rel, root / run_rel)
    contract_path = root / run_rel / "review-prompt-contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    broken = copy.deepcopy(contract)
    invocation_set_path = run_rel / "review-invocation-set.json"
    (root / invocation_set_path).write_text(
        json.dumps(
            {
                "artifact_kind": "review_invocation_set",
                "review_prompt_contract": str(run_rel / "review-prompt-contract.yaml"),
                "status": "failed",
                "provider_model_families": [],
                "reviewers": [],
                "error": "test fixture",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    broken["inputs"]["evidence_report"] = str(invocation_set_path)
    broken["inputs"]["review_invocation_set"] = str(invocation_set_path)

    errors = validate_repo.validate_review_prompt_contract_run_references(root, contract_path, broken)

    assert "inputs.evidence_report must not match inputs.review_invocation_set" in "\n".join(errors)


def _write_minimal_preparation_fixture(root: Path) -> tuple[Path, Path, Path, Path]:
    import json
    import shutil

    import yaml

    for rel in ["schemas", "profiles", "templates/review-prompts"]:
        shutil.copytree(ROOT / rel, root / rel)
    run_dir = root / "Docs/agentsflow/runs/2026-06-21-prep"
    (run_dir / "review-packets").mkdir(parents=True)
    (run_dir / "review-prompts").mkdir()
    (run_dir / "reports").mkdir()
    (root / "src").mkdir()
    (root / "AGENTS.md").write_text("# Test Instructions\n", encoding="utf-8")
    (run_dir / "task.contract.md").write_text("# Task Contract\n", encoding="utf-8")
    (run_dir / "verification-gate-report.json").write_text(
        json.dumps(
            {
                "kind": "verification_gate_report",
                "result_state": "pass",
                "checks": [{"id": "pytest", "status": "pass"}],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    shared_packet = {
        "agentsflow_version": "0.2",
        "workflow": "big-feature-contract-first",
        "run_id": "2026-06-21-prep",
        "reviewer_role": "generalist",
        "reviewer_instance_id": "generalist-a",
        "review_goal": "Review the prepared artifact slice.",
        "review_profile": "homogeneous-dual",
        "composition": "homogeneous",
        "prompt_policy": {
            "same_prompt": True,
            "same_packet": True,
            "same_rubric": True,
            "same_output_schema": True,
        },
        "role_contract": "profiles/reviewer_roles/generalist.yaml",
        "review_prompt_contract": {
            "path": "Docs/agentsflow/runs/2026-06-21-prep/review-prompt-contract.yaml",
            "schema": "schemas/review-prompt-contract.schema.json",
        },
        "risk_surface_profile": {
            "selected_risk_surfaces": [],
            "review_topology_source": "workflow_default",
        },
        "failure_path_matrix": {
            "path": "Docs/agentsflow/runs/2026-06-21-prep/failure-path-matrix.yaml",
            "rows": [],
        },
        "verification_gate_report": {
            "path": "Docs/agentsflow/runs/2026-06-21-prep/verification-gate-report.json",
        },
        "evidence_freshness": {
            "latest_green_gate": "Docs/agentsflow/runs/2026-06-21-prep/verification-gate-report.json",
        },
        "known_blockers": [],
        "output_schema": "schemas/reviewer-report.schema.json",
        "changed_files": ["src/new.py"],
    }
    shared_packet_path = run_dir / "review-packets/shared-source.json"
    shared_packet_path.write_text(json.dumps(shared_packet, indent=2), encoding="utf-8")
    contract = {
        "version": 1,
        "artifact_kind": "review_prompt_contract",
        "artifact_scope": "run",
        "identity": {
            "run_id": "2026-06-21-prep",
            "workflow": "big-feature-contract-first",
            "phase_id": "review",
            "review_profile": "homogeneous-dual",
            "topology": "homogeneous-dual",
            "composition": "homogeneous",
            "primary_gate": True,
        },
        "inputs": {
            "review_packet_schema": "schemas/review-packet.schema.json",
            "review_packets": [
                {
                    "reviewer": "generalist-a",
                    "path": "Docs/agentsflow/runs/2026-06-21-prep/review-packets/generalist-a.json",
                    "schema": "schemas/review-packet.schema.json",
                    "packet_hash": "sha256:<pending>",
                    "shared_packet_content_hash": "sha256:<pending>",
                },
                {
                    "reviewer": "generalist-b",
                    "path": "Docs/agentsflow/runs/2026-06-21-prep/review-packets/generalist-b.json",
                    "schema": "schemas/review-packet.schema.json",
                    "packet_hash": "sha256:<pending>",
                    "shared_packet_content_hash": "sha256:<pending>",
                },
            ],
            "output_schema": "schemas/reviewer-report.schema.json",
            "task_contract": "Docs/agentsflow/runs/2026-06-21-prep/task.contract.md",
            "verification_gate_report": "Docs/agentsflow/runs/2026-06-21-prep/verification-gate-report.json",
            "evidence_report": "Docs/agentsflow/runs/2026-06-21-prep/evidence-report.md",
            "artifact_preparation_report": "Docs/agentsflow/runs/2026-06-21-prep/prepared-review-artifacts.json",
            "review_invocation_set": "Docs/agentsflow/runs/2026-06-21-prep/review-invocation-set.json",
        },
        "reviewer_set": [
            {
                "instance_id": "generalist-a",
                "role_id": "generalist",
                "role_contract": "profiles/reviewer_roles/generalist.yaml",
                "independent": True,
            },
            {
                "instance_id": "generalist-b",
                "role_id": "generalist",
                "role_contract": "profiles/reviewer_roles/generalist.yaml",
                "independent": True,
            },
        ],
        "provider_policy": {
            "allow_external_reviewers": True,
            "require_model_diversity": True,
            "min_distinct_provider_model_families": 2,
        },
        "reviewer_assignments": [
            {
                "reviewer": "generalist-a",
                "provider": "internal-agent",
                "model_family": "codex",
                "packet_path": "Docs/agentsflow/runs/2026-06-21-prep/review-packets/generalist-a.json",
                "report_path": "Docs/agentsflow/runs/2026-06-21-prep/reports/reviewer-report.generalist-a.json",
            },
            {
                "reviewer": "generalist-b",
                "provider": "claude-code",
                "model_family": "opus",
                "provider_config": "examples/external-reviewers/claude-code/claude-code.yaml",
                "packet_path": "Docs/agentsflow/runs/2026-06-21-prep/review-packets/generalist-b.json",
                "report_path": "Docs/agentsflow/runs/2026-06-21-prep/reports/reviewer-report.generalist-b.json",
                "raw_output_path": "Docs/agentsflow/runs/2026-06-21-prep/reports/reviewer-report.generalist-b.raw.json",
                "invocation_metadata_path": "Docs/agentsflow/runs/2026-06-21-prep/reports/reviewer-invocation.generalist-b.json",
            },
        ],
        "context_policy": {
            "start_mode": "fresh_context",
            "fork_conversation_context": False,
            "allowed_context_sources": ["review_packet", "referenced_artifacts"],
        },
        "permission_policy": {
            "read_only": True,
            "forbidden_actions": ["run_tests", "run_scripts", "modify_files", "create_patch", "update_evidence"],
        },
        "prompt_components": {
            "shared_base_instructions": "templates/review-prompts/base.md",
            "finding_lifecycle": "candidate-unvalidated",
            "output_instructions": "schemas/reviewer-report.schema.json",
        },
        "prompt_policy": {
            "same_prompt": True,
            "same_packet": True,
            "same_rubric": True,
            "same_output_schema": True,
        },
        "rendered_prompts": [
            {
                "reviewer": "generalist-a",
                "prompt_path": "Docs/agentsflow/runs/2026-06-21-prep/review-prompts/generalist-a.md",
                "prompt_hash": "sha256:<pending>",
                "shared_prompt_content_hash": "sha256:<pending>",
                "packet_hash": "sha256:<pending>",
                "shared_packet_content_hash": "sha256:<pending>",
                "schema_hash": "sha256:<pending>",
                "rubric_hash": "sha256:<pending>",
                "role_contract_hash": "sha256:<pending>",
            },
            {
                "reviewer": "generalist-b",
                "prompt_path": "Docs/agentsflow/runs/2026-06-21-prep/review-prompts/generalist-b.md",
                "prompt_hash": "sha256:<pending>",
                "shared_prompt_content_hash": "sha256:<pending>",
                "packet_hash": "sha256:<pending>",
                "shared_packet_content_hash": "sha256:<pending>",
                "schema_hash": "sha256:<pending>",
                "rubric_hash": "sha256:<pending>",
                "role_contract_hash": "sha256:<pending>",
            },
        ],
        "collision_control": None,
        "validation": {
            "schema": "schemas/review-prompt-contract.schema.json",
            "assembly_invariants": ["homogeneous-dual uses exactly two reviewers."],
        },
    }
    contract_path = run_dir / "review-prompt-contract.yaml"
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    preparation_path = run_dir / "prepared-review-artifacts.json"
    return contract_path, shared_packet_path, preparation_path, run_dir


def _git_commit_all(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, text=True, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "AgentsFlow Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=root, text=True, capture_output=True, check=True)


def test_prepare_review_set_artifacts_rejects_uncovered_dirty_paths(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    contract_path, shared_packet_path, preparation_path, run_dir = _write_minimal_preparation_fixture(root)
    _git_commit_all(root)
    (root / "src/new.py").write_text("print('new')\n", encoding="utf-8")

    result = run(
        "scripts/reviewers/prepare_review_set_artifacts.py",
        "--root",
        str(root),
        "--contract",
        str(contract_path.relative_to(root)),
        "--shared-packet",
        str(shared_packet_path.relative_to(root)),
        "--preparation-output",
        str(preparation_path.relative_to(root)),
        env=clean_env(),
    )

    assert result.returncode != 0
    assert "uncovered dirty worktree path" in (result.stdout + result.stderr)
    assert not (run_dir / "review-packets/generalist-a.json").exists()


def test_prepare_review_set_artifacts_rejects_stale_embedded_file_snapshot(tmp_path) -> None:
    import json

    root = tmp_path / "root"
    root.mkdir()
    contract_path, shared_packet_path, preparation_path, run_dir = _write_minimal_preparation_fixture(root)
    shared_packet = json.loads(shared_packet_path.read_text(encoding="utf-8"))
    shared_packet["files"] = [
        {
            "path": "AGENTS.md",
            "size_bytes": 4,
            "content": "stale",
        }
    ]
    shared_packet_path.write_text(json.dumps(shared_packet, indent=2) + "\n", encoding="utf-8")
    _git_commit_all(root)
    (root / "src/new.py").write_text("print('new')\n", encoding="utf-8")

    result = run(
        "scripts/reviewers/prepare_review_set_artifacts.py",
        "--root",
        str(root),
        "--contract",
        str(contract_path.relative_to(root)),
        "--shared-packet",
        str(shared_packet_path.relative_to(root)),
        "--preparation-output",
        str(preparation_path.relative_to(root)),
        "--include",
        "src/new.py",
        "--include",
        "AGENTS.md",
        env=clean_env(),
    )

    assert result.returncode != 0
    assert "embedded file snapshot is stale for AGENTS.md" in (result.stdout + result.stderr)
    assert not (run_dir / "review-packets/generalist-a.json").exists()


def test_prepare_review_set_artifacts_generates_packets_prompts_and_evidence(tmp_path) -> None:
    import json

    import jsonschema
    import yaml

    root = tmp_path / "root"
    root.mkdir()
    contract_path, shared_packet_path, preparation_path, run_dir = _write_minimal_preparation_fixture(root)
    _git_commit_all(root)
    (root / "src/new.py").write_text("print('new')\n", encoding="utf-8")

    result = run(
        "scripts/reviewers/prepare_review_set_artifacts.py",
        "--root",
        str(root),
        "--contract",
        str(contract_path.relative_to(root)),
        "--shared-packet",
        str(shared_packet_path.relative_to(root)),
        "--preparation-output",
        str(preparation_path.relative_to(root)),
        "--include",
        "src/new.py",
        "--include",
        "AGENTS.md",
        env=clean_env(),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (run_dir / "review-packets/generalist-a.json").exists()
    assert (run_dir / "review-packets/generalist-b.json").exists()
    assert (run_dir / "review-prompts/generalist-a.md").exists()
    assert (run_dir / "review-prompts/generalist-b.md").exists()
    assert preparation_path.exists()
    invocation_set_path = run_dir / "review-invocation-set.json"
    assert invocation_set_path.exists()

    preparation = json.loads(preparation_path.read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas/review-artifact-preparation.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(preparation)
    assert preparation["artifact_kind"] == "review_artifact_preparation"
    assert preparation["generated_artifacts"]["review_invocation_set"]["path"].endswith("review-invocation-set.json")
    assert {item["path"] for item in preparation["input_artifacts"]} >= {"src/new.py", "AGENTS.md"}
    invocation_set = json.loads(invocation_set_path.read_text(encoding="utf-8"))
    invocation_schema = json.loads((ROOT / "schemas/review-invocation-set.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(invocation_schema).validate(invocation_set)
    assert invocation_set["status"] == "predeclared"
    assert sorted(item["reviewer"] for item in invocation_set["reviewers"]) == [
        "generalist-a",
        "generalist-b",
    ]

    updated_contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    assert updated_contract["inputs"]["artifact_preparation_report"].endswith("prepared-review-artifacts.json")
    assert updated_contract["inputs"]["review_invocation_set"].endswith("review-invocation-set.json")
    assert updated_contract["inputs"]["evidence_report"].endswith("evidence-report.md")
    for packet in updated_contract["inputs"]["review_packets"]:
        assert packet["packet_hash"].startswith("sha256:")
    for prompt in updated_contract["rendered_prompts"]:
        assert prompt["prompt_hash"].startswith("sha256:")
    packet_schema = json.loads((ROOT / "schemas/review-packet.schema.json").read_text(encoding="utf-8"))
    packet_validator = jsonschema.Draft202012Validator(packet_schema)
    for packet_path in [
        run_dir / "review-packets/generalist-a.json",
        run_dir / "review-packets/generalist-b.json",
    ]:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet_validator.validate(packet)
        assert packet["context_policy"]["start_mode"] == "fresh_context"
        forbidden_text = " ".join(action.lower() for action in packet["forbidden_actions"])
        for phrase in ["modify files", "run tests", "produce patches", "execute scripts", "update evidence"]:
            assert phrase in forbidden_text


def test_prepare_review_set_artifacts_generates_plus_focused_baseline_shared_hashes(tmp_path) -> None:
    import json

    import yaml

    root = tmp_path / "root"
    root.mkdir()
    contract_path, shared_packet_path, preparation_path, run_dir = _write_minimal_preparation_fixture(root)
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    contract["identity"]["review_profile"] = "homogeneous-plus-focused"
    contract["identity"]["topology"] = "homogeneous-plus-focused"
    contract["identity"]["composition"] = "homogeneous-plus-focused"
    contract["prompt_policy"] = {
        "baseline_same_prompt": True,
        "baseline_same_packet": True,
        "baseline_same_rubric": True,
        "focused_reviewers_require_explicit_focus_zone": True,
        "focus_zones_may_overlap": True,
        "all_reviewers_must_report_p0_p1_outside_focus": True,
    }
    contract["inputs"]["review_packets"].append(
        {
            "reviewer": "adversarial-codex",
            "path": "Docs/agentsflow/runs/2026-06-21-prep/review-packets/adversarial-codex.json",
            "schema": "schemas/review-packet.schema.json",
            "packet_hash": "sha256:<pending>",
        }
    )
    contract["reviewer_set"].append(
        {
            "instance_id": "adversarial-codex",
            "role_id": "adversarial",
            "role_contract": "profiles/reviewer_roles/adversarial.yaml",
            "independent": True,
            "focus_zone": {
                "primary_focus": ["review evidence binding"],
                "may_report_outside_focus": True,
            },
        }
    )
    contract["reviewer_assignments"].append(
        {
            "reviewer": "adversarial-codex",
            "provider": "internal-agent",
            "model_family": "codex",
            "packet_path": "Docs/agentsflow/runs/2026-06-21-prep/review-packets/adversarial-codex.json",
            "report_path": "Docs/agentsflow/runs/2026-06-21-prep/reports/reviewer-report.adversarial-codex.json",
        }
    )
    contract["rendered_prompts"].append(
        {
            "reviewer": "adversarial-codex",
            "prompt_path": "Docs/agentsflow/runs/2026-06-21-prep/review-prompts/adversarial-codex.md",
            "prompt_hash": "sha256:<pending>",
            "packet_hash": "sha256:<pending>",
            "schema_hash": "sha256:<pending>",
            "rubric_hash": "sha256:<pending>",
            "role_contract_hash": "sha256:<pending>",
        }
    )
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    _git_commit_all(root)
    (root / "src/new.py").write_text("print('new')\n", encoding="utf-8")

    result = run(
        "scripts/reviewers/prepare_review_set_artifacts.py",
        "--root",
        str(root),
        "--contract",
        str(contract_path.relative_to(root)),
        "--shared-packet",
        str(shared_packet_path.relative_to(root)),
        "--preparation-output",
        str(preparation_path.relative_to(root)),
        "--include",
        "src/new.py",
        "--include",
        "AGENTS.md",
        env=clean_env(),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    updated_contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    packet_refs = {
        item["reviewer"]: item
        for item in updated_contract["inputs"]["review_packets"]
    }
    prompt_refs = {
        item["reviewer"]: item
        for item in updated_contract["rendered_prompts"]
    }
    baseline_packet_hashes = {
        packet_refs["generalist-a"]["shared_packet_content_hash"],
        packet_refs["generalist-b"]["shared_packet_content_hash"],
    }
    baseline_prompt_hashes = {
        prompt_refs["generalist-a"]["shared_prompt_content_hash"],
        prompt_refs["generalist-b"]["shared_prompt_content_hash"],
    }
    assert len(baseline_packet_hashes) == 1
    assert len(baseline_prompt_hashes) == 1
    assert "shared_packet_content_hash" not in packet_refs["adversarial-codex"]
    assert "shared_prompt_content_hash" not in prompt_refs["adversarial-codex"]
    invocation_set = json.loads((run_dir / "review-invocation-set.json").read_text(encoding="utf-8"))
    assert sorted(item["reviewer"] for item in invocation_set["reviewers"]) == [
        "adversarial-codex",
        "generalist-a",
        "generalist-b",
    ]
