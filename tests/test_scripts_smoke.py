from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=ROOT, text=True, capture_output=True)


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


def test_project_binding_validation_passes() -> None:
    result = run("scripts/validate_project_binding.py", "--project", "examples/project-overlay", "--agentsflow-root", ".")
    assert result.returncode == 0, result.stdout + result.stderr



def test_project_intake_validation_passes() -> None:
    result = run("scripts/validate_project_intake.py", "--intake", "examples/project-initialization/project-intake.yaml")
    assert result.returncode == 0, result.stdout + result.stderr


def test_project_inventory_validation_passes() -> None:
    result = run("scripts/validate_project_inventory.py", "--inventory", "examples/project-initialization/project-inventory.json")
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
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert out.exists()


def test_external_reviewer_wrapper_rejects_api_key(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "forbidden")
    out = tmp_path / "reviewer-report.json"
    result = run(
        "scripts/reviewers/run_external_reviewer.py",
        "--provider", "claude-code",
        "--config", "examples/external-reviewers/claude-code/claude-code.yaml",
        "--input", "examples/external-reviewers/claude-code/review-packet.architecture.json",
        "--mock-response", "examples/external-reviewers/claude-code/mock-raw-output.json",
        "--output", str(out),
    )
    assert result.returncode != 0
    assert "ANTHROPIC_API_KEY" in (result.stdout + result.stderr)
