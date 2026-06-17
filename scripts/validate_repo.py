#!/usr/bin/env python3
"""Validate basic AgentsFlow repository integrity.

v0.1.13 validates:
- YAML/JSON parseability;
- workflow references to skills/scripts/templates/packs/review topologies;
- upstream gate contract manifests and generic runner paths;
- behavior binding manifests;
- project-overlay example bindings.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

VALID_BINDING_CHECK_TYPES = {
    "test", "script", "bdd_runner", "eval", "trace_assertion", "log_assertion",
    "static_analysis", "dynamic_analysis", "benchmark", "security_scan",
    "manual_evidence", "external_tool",
}


def parse_yaml(path: Path) -> object:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"YAML parse error in {path}: {exc}") from exc


def parse_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"JSON parse error in {path}: {exc}") from exc


def collect_names(root: Path, base: str, manifest: str) -> set[str]:
    names: set[str] = set()
    d = root / base
    if not d.exists():
        return names
    for p in d.iterdir():
        if p.is_dir() and (p / manifest).exists():
            names.add(p.name)
    return names


def collect_script_names(root: Path) -> set[str]:
    names: set[str] = set()
    for p in (root / "scripts" / "contracts").glob("*.yaml"):
        data = parse_yaml(p) or {}
        if isinstance(data, dict):
            names.add(str(data.get("name", p.stem)))
        else:
            names.add(p.stem)
    return names


def collect_gate_manifests(root: Path) -> dict[str, Path]:
    gates: dict[str, Path] = {}
    for p in (root / "gates").glob("*.yaml"):
        data = parse_yaml(p) or {}
        if isinstance(data, dict):
            gid = str(data.get("id", p.stem))
            gates[gid] = p
    return gates


def validate_gate_manifest(root: Path, path: Path) -> list[str]:
    errors: list[str] = []
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"Gate {path} is not a mapping"]
    required = ["id", "name", "kind", "purpose", "runner", "inputs", "instruments", "outputs", "result_states", "pass_policy"]
    for key in required:
        if key not in data:
            errors.append(f"{path}: missing required gate field: {key}")
    if data.get("kind") != "gate":
        errors.append(f"{path}: kind must be 'gate'")
    runner = data.get("runner")
    if runner:
        runner_path = root / str(runner)
        if not runner_path.exists():
            errors.append(f"{path}: generic runner path does not exist: {runner}")
    if data.get("binding_level") and data.get("binding_level") != "upstream_gate_contract":
        errors.append(f"{path}: upstream gates should use binding_level=upstream_gate_contract")
    instruments = data.get("instruments", []) or []
    if not isinstance(instruments, list) or not instruments:
        errors.append(f"{path}: instruments must be a non-empty list")
    else:
        for idx, inst in enumerate(instruments):
            if not isinstance(inst, dict):
                errors.append(f"{path}: instrument #{idx} is not a mapping")
                continue
            if "id" not in inst or "type" not in inst:
                errors.append(f"{path}: instrument #{idx} must include id and type")
    pass_policy = data.get("pass_policy", {}) or {}
    if isinstance(pass_policy, dict):
        for key in ["fail_on", "inconclusive_on"]:
            if key not in pass_policy:
                errors.append(f"{path}: pass_policy missing {key}")
    else:
        errors.append(f"{path}: pass_policy must be a mapping")
    return errors


def validate_external_review_provider(path: Path) -> list[str]:
    errors: list[str] = []
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"{path}: external reviewer provider config is not a mapping"]
    if data.get("provider") != "claude-code":
        return errors
    billing = data.get("billing", {}) or {}
    if billing.get("expected_mode") != "subscription-local":
        errors.append(f"{path}: claude-code expected_mode must be subscription-local")
    if billing.get("forbid_api_key_usage") is not True:
        errors.append(f"{path}: claude-code must set forbid_api_key_usage: true")
    if "ANTHROPIC_API_KEY" not in set(billing.get("fail_if_env_present", []) or []):
        errors.append(f"{path}: claude-code must fail if ANTHROPIC_API_KEY is present")
    permissions = data.get("permissions", {}) or {}
    for key in ["write_files", "run_tests", "run_verification_instruments", "run_tools"]:
        if permissions.get(key) is not False:
            errors.append(f"{path}: claude-code permission {key} must be false")
    outputs = data.get("outputs", {}) or {}
    if outputs.get("reviewer_report_schema") != "schemas/reviewer-report.schema.json":
        errors.append(f"{path}: external provider must output schemas/reviewer-report.schema.json")
    return errors


def validate_behavior_binding(path: Path) -> list[str]:
    errors: list[str] = []
    data = parse_yaml(path) or {}
    if not isinstance(data, dict):
        return [f"{path}: behavior binding is not a mapping"]
    for key in ["version", "contract", "bindings"]:
        if key not in data:
            errors.append(f"{path}: missing required field {key}")
    bindings = data.get("bindings", []) or []
    if not isinstance(bindings, list):
        return errors + [f"{path}: bindings must be a list"]
    seen: set[str] = set()
    for idx, item in enumerate(bindings):
        if not isinstance(item, dict):
            errors.append(f"{path}: binding #{idx} must be a mapping")
            continue
        bid = str(item.get("id", f"#{idx}"))
        if bid in seen:
            errors.append(f"{path}: duplicate binding id {bid}")
        seen.add(bid)
        for key in ["id", "scenario", "required", "checks", "gates"]:
            if key not in item:
                errors.append(f"{path}: binding {bid} missing {key}")
        if item.get("required") is True and not item.get("checks"):
            errors.append(f"{path}: required binding {bid} has no checks")
        for check in item.get("checks", []) or []:
            if not isinstance(check, dict):
                errors.append(f"{path}: binding {bid} check must be a mapping")
                continue
            ctype = check.get("type")
            if ctype not in VALID_BINDING_CHECK_TYPES:
                errors.append(f"{path}: binding {bid} has unknown check type {ctype}")
            if ctype != "manual_evidence" and not (check.get("command") or check.get("target")):
                errors.append(f"{path}: binding {bid} check {check.get('id')} lacks command/target")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="repository root")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    errors: list[str] = []

    for p in root.rglob("*.yaml"):
        try:
            parse_yaml(p)
        except ValueError as exc:
            errors.append(str(exc))
    for p in root.rglob("*.yml"):
        try:
            parse_yaml(p)
        except ValueError as exc:
            errors.append(str(exc))
    for p in root.rglob("*.json"):
        try:
            parse_json(p)
        except ValueError as exc:
            errors.append(str(exc))

    skills = collect_names(root, "skills", "skill.yaml")
    packs = collect_names(root, "packs", "pack.yaml")
    scripts = collect_script_names(root)
    templates = {p.name for p in (root / "templates").glob("*") if p.is_file()}
    topologies = {p.stem for p in (root / "profiles" / "review_topologies").glob("*.yaml")}
    gates = collect_gate_manifests(root)

    for gate_path in gates.values():
        errors.extend(validate_gate_manifest(root, gate_path))

    for binding in root.rglob("*.bindings.yaml"):
        errors.extend(validate_behavior_binding(binding))

    for provider_config in list(root.rglob("external-review-provider.yaml")) + list(root.rglob("claude-code.yaml")):
        errors.extend(validate_external_review_provider(provider_config))

    required_files = [
        "schemas/behavior-binding.schema.json",
        "schemas/project-binding.schema.json",
        "schemas/workflow-binding.schema.json",
        "templates/behavior-bindings.yaml",
        "templates/project.yaml",
        "templates/workflow.binding.yaml",
        "templates/agentsflow.lock.yaml",
        "templates/project-intake.yaml",
        "templates/research-assignment.unknown-project.md",
        "templates/project-raw-scan.json",
        "templates/project-inventory.json",
        "templates/project-assessment.json",
        "templates/initialization-report.md",
        "templates/workflow-run.yaml",
        "schemas/project-intake.schema.json",
        "schemas/project-raw-scan.schema.json",
        "schemas/project-inventory.schema.json",
        "schemas/project-assessment.schema.json",
        "schemas/workflow-run.schema.json",
        "docs/project-application-model.md",
        "docs/project-initialization-model.md",
        "docs/legacy-agent-system-adoption-model.md",
        "docs/adr/ADR-0015-legacy-adoption-modes.md",
        "templates/legacy-adoption-decision.yaml",
        "templates/legacy-agent-system-inventory.json",
        "templates/agent-instruction-conflicts.md",
        "templates/agent-instruction-migration-plan.md",
        "templates/legacy-backup-manifest.yaml",
        "templates/active-instruction-map.yaml",
        "schemas/legacy-adoption-decision.schema.json",
        "schemas/legacy-agent-system-inventory.schema.json",
        "schemas/active-instruction-map.schema.json",

        "docs/external-reviewer-provider-model.md",
        "docs/adr/ADR-0016-external-reviewer-provider-interface.md",
        "templates/external-review-provider.yaml",
        "templates/review-packet.json",
        "templates/reviewer-invocation.json",
        "schemas/external-review-provider.schema.json",
        "schemas/review-packet.schema.json",
        "schemas/reviewer-invocation.schema.json",
        "schemas/reviewer-report.schema.json",
        "scripts/reviewers/run_external_reviewer.py",
        "scripts/reviewers/providers/claude_code.py",
        "scripts/contracts/run_external_reviewer.yaml",
        "examples/external-reviewers/claude-code/mock-raw-output.json",
        "docs/cmake-fetchcontent-application-pattern.md",
    ]
    for rel in required_files:
        if not (root / rel).exists():
            errors.append(f"missing required file: {rel}")

    for wf in (root / "workflows").glob("*/workflow.yaml"):
        data = parse_yaml(wf) or {}
        if not isinstance(data, dict):
            errors.append(f"Workflow {wf} is not a mapping")
            continue
        uses = data.get("uses", {}) or {}
        for s in uses.get("skills", []) or []:
            if s not in skills:
                errors.append(f"{wf}: missing skill reference: {s}")
        for s in uses.get("scripts", []) or []:
            if s not in scripts:
                errors.append(f"{wf}: missing script reference: {s}")
        for t in uses.get("templates", []) or []:
            if t not in templates:
                errors.append(f"{wf}: missing template reference: {t}")
        for pack in uses.get("packs", []) or []:
            if pack not in packs:
                errors.append(f"{wf}: missing pack reference: {pack}")
        review = data.get("review", {}) or {}
        topology = review.get("topology")
        if topology and topology not in topologies:
            errors.append(f"{wf}: unknown review topology: {topology}")
        for gid in review.get("gates", []) or []:
            if gid not in gates:
                errors.append(f"{wf}: missing gate manifest referenced by review.gates: {gid}")
        for phase in data.get("phases", []) or []:
            if not isinstance(phase, dict):
                continue
            gid = phase.get("gate")
            if gid and gid not in gates:
                errors.append(f"{wf}: phase {phase.get('id', phase.get('name'))} references missing gate: {gid}")
            if (phase.get("kind") in {"gate", "verification"} or str(phase.get("id", "")).endswith("_gate")) and not gid:
                errors.append(f"{wf}: gate/verification phase {phase.get('id', phase.get('name'))} must declare a gate manifest via 'gate:'")
            if phase.get("kind") == "review" and phase.get("scripts"):
                errors.append(f"{wf}: review phase {phase.get('id', phase.get('name'))} must not list scripts; use tool exceptions only if explicitly declared")

    if errors:
        print("Repository validation failed:")
        for err in errors:
            print(f"- {err}")
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
