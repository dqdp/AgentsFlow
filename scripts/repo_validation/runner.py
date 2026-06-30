from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .behavior_bindings import validate_behavior_binding, validate_behavior_binding_gate_refs
from .collect import (
    collect_active_review_topologies,
    collect_gate_manifests,
    collect_names,
    collect_script_names,
    collect_yaml_manifest_names,
)
from .common import (
    parse_json,
    parse_yaml,
    validate_against_schema,
    validate_no_duplicate_yaml_keys,
    workflow_schema,
)
from .external_reviewers import validate_external_review_provider
from .gates import validate_gate_manifest
from .project_initialization import (
    validate_project_assessment_synthesis_artifact,
    validate_project_initialization_expert_assessment_contract,
    validate_project_documentation_disposition_artifact,
    validate_project_initialization_human_interaction,
    validate_project_initialization_intent_mode_policy,
    validate_project_initialization_operating_decisions,
    validate_project_onboarding_assessment_skill_contract,
)
from .project_overlay import validate_project_overlay_example
from .portable_paths import validate_portable_structured_paths
from .pr_merge_readiness import validate_pr_merge_readiness_report
from .required_files import REQUIRED_FILES
from .review import (
    validate_enabled_review_minimum,
    validate_evidence_probe_report_artifact,
    validate_required_review_gate_order,
    validate_review_fusion_validation_order,
    validate_review_manifest_collection,
    validate_review_packet_artifact,
    validate_phase_skills_declared,
    validate_reviewer_report_artifact,
    validate_standard_review_control_glue_guardrail,
    validate_supported_review_topologies,
    validate_upstream_review_cycle_policy,
    validate_v02_review_control_materiality_policy,
    validate_v02_review_control_phase_policy,
)
from .workflow_runs import validate_workflow_run_artifact
from .workflows import (
    validate_big_feature_plan_gate_policy,
    validate_phase_scripts_declared,
    validate_test_framed_implementation,
    validate_workflow_default_strictness,
)


def _tracked_files(root: Path) -> set[Path]:
    if not (root / '.git').exists():
        return set()
    result = subprocess.run(
        ['git', 'ls-files'],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return set()
    return {(root / line).resolve() for line in result.stdout.splitlines() if line}


def _tracked_file_refs(root: Path) -> tuple[list[Path], list[str]]:
    if not (root / ".git").exists():
        return [], ["tracked-only validation requires a git worktree"]
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        text=False,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        return [], [f"git ls-files failed: {stderr or result.returncode}"]
    refs = [
        Path(raw.decode("utf-8"))
        for raw in result.stdout.split(b"\0")
        if raw
    ]
    return refs, []


def _is_agentsflow_local_run_artifact(rel: Path) -> bool:
    return rel.parts[:1] == ("run-artifacts",)


def _is_agentsflow_local_run_artifact_path(root: Path, path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return _is_agentsflow_local_run_artifact(rel)


def _validate_no_tracked_agentsflow_run_artifacts(refs: list[Path]) -> list[str]:
    return [
        (
            f"tracked local run artifact is not allowed: {rel.as_posix()} "
            "(promote curated examples under examples/ instead)"
        )
        for rel in refs
        if _is_agentsflow_local_run_artifact(rel)
    ]


def _copy_tracked_snapshot(root: Path, target: Path, refs: list[Path]) -> list[str]:
    errors: list[str] = []
    for rel in refs:
        if rel.is_absolute() or ".." in rel.parts:
            errors.append(f"invalid tracked path: {rel}")
            continue
        src = root / rel
        dst = target / rel
        if not src.exists() and not src.is_symlink():
            errors.append(f"tracked file missing from working tree: {rel.as_posix()}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            os.symlink(os.readlink(src), dst)
        else:
            shutil.copy2(src, dst)
    return errors


def validate_tracked_repository(root: Path) -> list[str]:
    root = root.resolve()
    refs, errors = _tracked_file_refs(root)
    if errors:
        return errors
    run_artifact_errors = _validate_no_tracked_agentsflow_run_artifacts(refs)
    if run_artifact_errors:
        return run_artifact_errors
    with tempfile.TemporaryDirectory(prefix="agentsflow-tracked-validation-") as tmp:
        snapshot = Path(tmp) / "repo"
        snapshot.mkdir()
        copy_errors = _copy_tracked_snapshot(root, snapshot, refs)
        if copy_errors:
            return copy_errors
        return validate_repository(snapshot)


def _tracked_or_all(paths: set[Path], tracked_files: set[Path]) -> set[Path]:
    if not tracked_files:
        return paths
    return {path for path in paths if path.resolve() in tracked_files}


def _resolve_cli_path(root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (root / path).resolve()


def validate_repository(
    root: Path,
    pr_merge_readiness_reports: tuple[Path, ...] = (),
) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    tracked_files = _tracked_files(root)
    if tracked_files:
        tracked_refs = [
            path.relative_to(root)
            for path in tracked_files
            if path.is_relative_to(root)
        ]
        errors.extend(_validate_no_tracked_agentsflow_run_artifacts(tracked_refs))

    yaml_paths = [
        p for p in root.rglob('*.yaml')
        if not _is_agentsflow_local_run_artifact_path(root, p)
    ]
    yml_paths = [
        p for p in root.rglob('*.yml')
        if not _is_agentsflow_local_run_artifact_path(root, p)
    ]
    json_paths = [
        p for p in root.rglob('*.json')
        if not _is_agentsflow_local_run_artifact_path(root, p)
    ]

    for p in yaml_paths:
        errors.extend(validate_no_duplicate_yaml_keys(p))
        try:
            parse_yaml(p)
        except ValueError as exc:
            errors.append(str(exc))
    for p in yml_paths:
        errors.extend(validate_no_duplicate_yaml_keys(p))
        try:
            parse_yaml(p)
        except ValueError as exc:
            errors.append(str(exc))
    for p in json_paths:
        try:
            parse_json(p)
        except ValueError as exc:
            errors.append(str(exc))
    errors.extend(validate_portable_structured_paths(root))

    skills = collect_names(root, 'skills', 'skill.yaml')
    skill_manifests = {
        path.parent.name: parse_yaml(path) or {}
        for path in (root / 'skills').glob('*/skill.yaml')
    }
    packs = collect_names(root, 'packs', 'pack.yaml')
    scripts = collect_script_names(root)
    templates = {p.name for p in (root / 'templates').glob('*') if p.is_file()}
    topologies = collect_active_review_topologies(root)
    reviewer_role_names = collect_yaml_manifest_names(root, 'profiles/reviewer_roles')
    gates = collect_gate_manifests(root)
    wf_schema = workflow_schema(root)
    project_schema = parse_json(root / 'schemas' / 'project-binding.schema.json')
    workflow_binding_schema = parse_json(root / 'schemas' / 'workflow-binding.schema.json')

    for gate_path in gates.values():
        errors.extend(validate_gate_manifest(root, gate_path))

    for binding in [
        p for p in root.rglob('*.bindings.yaml')
        if not _is_agentsflow_local_run_artifact_path(root, p)
    ]:
        errors.extend(validate_behavior_binding(binding))
        errors.extend(validate_behavior_binding_gate_refs(binding, set(gates.keys())))

    errors.extend(validate_review_manifest_collection(root))
    errors.extend(validate_review_packet_artifact(root, root / 'templates' / 'review-packet.json', False))
    errors.extend(validate_evidence_probe_report_artifact(root, root / 'templates' / 'evidence-probe-report.json'))
    errors.extend(validate_workflow_run_artifact(root, root / 'templates' / 'workflow-run.yaml'))
    documentation_disposition_paths = {
        root / 'templates' / 'project-documentation-disposition.yaml',
        *root.glob('examples/**/project-documentation-disposition.yaml'),
        *root.glob('Docs/agentsflow/runs/**/project-documentation-disposition.yaml'),
        *root.glob('examples/**/Docs/agentsflow/runs/**/project-documentation-disposition.yaml'),
    }
    for documentation_disposition in sorted(_tracked_or_all(documentation_disposition_paths, tracked_files)):
        errors.extend(validate_project_documentation_disposition_artifact(root, documentation_disposition))
    errors.extend(validate_project_onboarding_assessment_skill_contract(root))
    errors.extend(
        validate_project_assessment_synthesis_artifact(
            root,
            root / 'examples' / 'project-initialization' / 'project-assessment.json',
        )
    )
    run_artifact_patterns = [
        'Docs/agentsflow/runs/*/run.yaml',
        'examples/**/Docs/agentsflow/runs/*/run.yaml',
    ]
    for run_artifact in _tracked_or_all({
        path
        for pattern in run_artifact_patterns
        for path in root.glob(pattern)
    }, tracked_files):
        errors.extend(validate_workflow_run_artifact(root, run_artifact))
    review_packet_patterns = [
        'Docs/agentsflow/runs/*/review-packets/*.json',
        'examples/**/Docs/agentsflow/runs/*/review-packets/*.json',
    ]
    for review_packet in sorted(_tracked_or_all({
        path
        for pattern in review_packet_patterns
        for path in root.glob(pattern)
    }, tracked_files)):
        if review_packet.name in {'shared-content.json', 'shared-source.json'}:
            continue
        errors.extend(
            validate_review_packet_artifact(
                root,
                review_packet,
                True,
                require_green_verification_gate=True,
            )
        )
    for reviewer_report in root.glob('examples/**/Docs/agentsflow/runs/*/reviewer-report*.json'):
        errors.extend(validate_reviewer_report_artifact(root, reviewer_report))
    for probe_report in root.glob('examples/**/Docs/agentsflow/runs/*/evidence-probe-report*.json'):
        errors.extend(validate_evidence_probe_report_artifact(root, probe_report))

    provider_configs = [
        p for p in list(root.rglob('external-review-provider.yaml')) + list(root.rglob('claude-code.yaml'))
        if not _is_agentsflow_local_run_artifact_path(root, p)
    ]
    for provider_config in provider_configs:
        errors.extend(validate_external_review_provider(provider_config))

    for report_path in sorted(root.glob('examples/pr-merge-readiness/**/pr-merge-readiness-report.json')):
        errors.extend(validate_pr_merge_readiness_report(root, report_path))
    for report_path in pr_merge_readiness_reports:
        resolved_report_path = _resolve_cli_path(root, report_path)
        if not resolved_report_path.is_file():
            errors.append(f"missing pr-merge-readiness report: {report_path}")
            continue
        errors.extend(validate_pr_merge_readiness_report(root, resolved_report_path))

    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            errors.append(f'missing required file: {rel}')
    if not (root / 'docs' / 'enforcement-boundary.md').exists():
        errors.append('missing required file: docs/enforcement-boundary.md')

    for project_rel in [
        'examples/project-overlay',
        'examples/e2e/minimal-python-project',
    ]:
        errors.extend(
            validate_project_overlay_example(
                root,
                project_rel,
                project_schema,
                workflow_binding_schema,
                reviewer_role_names,
            )
        )

    for wf in (root / 'workflows').glob('*/workflow.yaml'):
        data = parse_yaml(wf) or {}
        if not isinstance(data, dict):
            errors.append(f'Workflow {wf} is not a mapping')
            continue
        errors.extend(validate_against_schema(wf, data, wf_schema))
        errors.extend(validate_workflow_default_strictness(wf, data))
        errors.extend(validate_test_framed_implementation(wf, data))
        errors.extend(validate_project_initialization_operating_decisions(wf, data))
        errors.extend(validate_project_initialization_human_interaction(wf, data))
        errors.extend(validate_project_initialization_expert_assessment_contract(wf, data))
        errors.extend(validate_project_initialization_intent_mode_policy(wf, data))
        errors.extend(validate_big_feature_plan_gate_policy(wf, data))
        errors.extend(validate_supported_review_topologies(wf, data))
        errors.extend(validate_upstream_review_cycle_policy(wf, data))
        errors.extend(validate_v02_review_control_phase_policy(wf, data))
        errors.extend(validate_standard_review_control_glue_guardrail(wf, data))
        errors.extend(validate_required_review_gate_order(wf, data))
        errors.extend(validate_review_fusion_validation_order(wf, data))
        errors.extend(validate_v02_review_control_materiality_policy(wf, data))
        errors.extend(validate_phase_skills_declared(wf, data, skill_manifests))
        errors.extend(validate_phase_scripts_declared(wf, data))
        uses = data.get('uses', {}) or {}
        for s in uses.get('skills', []) or []:
            if s not in skills:
                errors.append(f'{wf}: missing skill reference: {s}')
            else:
                compatible = skill_manifests.get(s, {}).get('compatible_workflows') or []
                if compatible and data.get('name') not in compatible:
                    errors.append(
                        f'{wf}: skill {s} compatible_workflows missing {data.get("name")}'
                    )
        for s in uses.get('scripts', []) or []:
            if s not in scripts:
                errors.append(f'{wf}: missing script reference: {s}')
        for t in uses.get('templates', []) or []:
            if t not in templates:
                errors.append(f'{wf}: missing template reference: {t}')
        for pack in uses.get('packs', []) or []:
            if pack not in packs:
                errors.append(f'{wf}: missing pack reference: {pack}')
        review = data.get('review', {}) or {}
        topology = review.get('topology')
        if topology and topology not in topologies:
            errors.append(f'{wf}: unknown review topology: {topology}')
        errors.extend(validate_enabled_review_minimum(wf, review, 'review', reviewer_role_names))
        for gid in review.get('gates', []) or []:
            if gid not in gates:
                errors.append(f'{wf}: missing gate manifest referenced by review.gates: {gid}')
        for phase in data.get('phases', []) or []:
            if not isinstance(phase, dict):
                continue
            gid = phase.get('gate')
            if gid and gid not in gates:
                errors.append(f'{wf}: phase {phase.get("id", phase.get("name"))} references missing gate: {gid}')
            if (phase.get('kind') in {'gate', 'verification'} or str(phase.get('id', '')).endswith('_gate')) and not gid:
                errors.append(f'{wf}: gate/verification phase {phase.get("id", phase.get("name"))} must declare a gate manifest via \'gate:\'')
            if phase.get('kind') == 'review' and phase.get('scripts'):
                errors.append(f'{wf}: review phase {phase.get("id", phase.get("name"))} must not list scripts; use tool exceptions only if explicitly declared')

    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.', help='repository root')
    ap.add_argument(
        '--tracked-only',
        action='store_true',
        help='validate a temporary snapshot containing only files listed by git ls-files',
    )
    ap.add_argument(
        '--pr-merge-readiness-report',
        action='append',
        default=[],
        type=Path,
        help='validate a concrete pr-merge-readiness-report.json artifact',
    )
    args = ap.parse_args()
    root = Path(args.root)
    if args.tracked_only and args.pr_merge_readiness_report:
        print('Repository validation failed:')
        print('- --tracked-only cannot be combined with --pr-merge-readiness-report')
        return 1
    errors = (
        validate_tracked_repository(root)
        if args.tracked_only
        else validate_repository(root, tuple(args.pr_merge_readiness_report))
    )
    if errors:
        print('Repository validation failed:')
        for err in errors:
            print(f'- {err}')
        return 1
    print('Repository validation passed.')
    return 0
