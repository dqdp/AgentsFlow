from __future__ import annotations

import argparse
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
from .pr_merge_readiness import validate_pr_merge_readiness_report
from .required_files import REQUIRED_FILES
from .review import (
    validate_enabled_review_minimum,
    validate_evidence_probe_report_artifact,
    validate_required_review_gate_order,
    validate_review_fusion_validation_order,
    validate_review_manifest_collection,
    validate_review_packet_artifact,
    validate_review_prompt_contract_invariants,
    validate_review_prompt_contract_run_references,
    validate_review_prompt_contract_template,
    validate_phase_skills_declared,
    validate_review_artifact_preparation_artifact,
    validate_reviewer_invocation_artifact,
    validate_reviewer_report_artifact,
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


def validate_repository(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []

    for p in root.rglob('*.yaml'):
        errors.extend(validate_no_duplicate_yaml_keys(p))
        try:
            parse_yaml(p)
        except ValueError as exc:
            errors.append(str(exc))
    for p in root.rglob('*.yml'):
        errors.extend(validate_no_duplicate_yaml_keys(p))
        try:
            parse_yaml(p)
        except ValueError as exc:
            errors.append(str(exc))
    for p in root.rglob('*.json'):
        try:
            parse_json(p)
        except ValueError as exc:
            errors.append(str(exc))

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

    for binding in root.rglob('*.bindings.yaml'):
        errors.extend(validate_behavior_binding(binding))
        errors.extend(validate_behavior_binding_gate_refs(binding, set(gates.keys())))

    errors.extend(validate_review_manifest_collection(root))
    errors.extend(validate_review_prompt_contract_template(root))
    errors.extend(validate_review_packet_artifact(root, root / 'templates' / 'review-packet.json', False))
    errors.extend(validate_evidence_probe_report_artifact(root, root / 'templates' / 'evidence-probe-report.json'))
    errors.extend(
        validate_review_packet_artifact(
            root,
            root / 'examples' / 'external-reviewers' / 'claude-code' / 'review-packet.architecture.json',
            True,
        )
    )
    errors.extend(validate_reviewer_invocation_artifact(root, root / 'templates' / 'reviewer-invocation.json'))
    errors.extend(validate_review_artifact_preparation_artifact(root, root / 'templates' / 'review-artifact-preparation.json'))
    errors.extend(
        validate_reviewer_invocation_artifact(
            root,
            root / 'examples' / 'external-reviewers' / 'claude-code' / 'reviewer-invocation.claude-architecture.json',
        )
    )
    errors.extend(validate_workflow_run_artifact(root, root / 'templates' / 'workflow-run.yaml'))
    documentation_disposition_paths = {
        root / 'templates' / 'project-documentation-disposition.yaml',
        *root.glob('examples/**/project-documentation-disposition.yaml'),
        *root.glob('Docs/agentsflow/runs/**/project-documentation-disposition.yaml'),
        *root.glob('run-artifacts/agentsflow/runs/**/project-documentation-disposition.yaml'),
        *root.glob('examples/**/Docs/agentsflow/runs/**/project-documentation-disposition.yaml'),
    }
    for documentation_disposition in sorted(documentation_disposition_paths):
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
        'run-artifacts/agentsflow/runs/*/run.yaml',
        'examples/**/Docs/agentsflow/runs/*/run.yaml',
    ]
    for run_artifact in {
        path
        for pattern in run_artifact_patterns
        for path in root.glob(pattern)
    }:
        errors.extend(validate_workflow_run_artifact(root, run_artifact))
    review_prompt_contract_patterns = [
        'Docs/agentsflow/runs/*/review-prompt-contract.yaml',
        'run-artifacts/agentsflow/runs/*/review-prompt-contract.yaml',
        'examples/**/Docs/agentsflow/runs/*/review-prompt-contract.yaml',
    ]
    for prompt_contract in sorted({
        path
        for pattern in review_prompt_contract_patterns
        for path in root.glob(pattern)
    }):
        schema = parse_json(root / 'schemas' / 'review-prompt-contract.schema.json')
        data = parse_yaml(prompt_contract) or {}
        if not isinstance(data, dict):
            errors.append(f'{prompt_contract}: review prompt contract must be a mapping')
        else:
            errors.extend(validate_against_schema(prompt_contract, data, schema))
            errors.extend(validate_review_prompt_contract_invariants(root, prompt_contract, data, True))
            errors.extend(validate_review_prompt_contract_run_references(root, prompt_contract, data))
    review_packet_patterns = [
        'Docs/agentsflow/runs/*/review-packets/*.json',
        'run-artifacts/agentsflow/runs/*/review-packets/*.json',
        'examples/**/Docs/agentsflow/runs/*/review-packets/*.json',
    ]
    for review_packet in sorted({
        path
        for pattern in review_packet_patterns
        for path in root.glob(pattern)
    }):
        if review_packet.name in {'shared-content.json', 'shared-source.json'}:
            continue
        errors.extend(validate_review_packet_artifact(root, review_packet, True))
    for reviewer_report in root.glob('examples/**/Docs/agentsflow/runs/*/reviewer-report*.json'):
        errors.extend(validate_reviewer_report_artifact(root, reviewer_report))
    for probe_report in root.glob('examples/**/Docs/agentsflow/runs/*/evidence-probe-report*.json'):
        errors.extend(validate_evidence_probe_report_artifact(root, probe_report))

    for provider_config in list(root.rglob('external-review-provider.yaml')) + list(root.rglob('claude-code.yaml')):
        errors.extend(validate_external_review_provider(provider_config))

    for report_path in sorted(root.glob('examples/pr-merge-readiness/**/pr-merge-readiness-report.json')):
        errors.extend(validate_pr_merge_readiness_report(root, report_path))

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
    args = ap.parse_args()
    errors = validate_repository(Path(args.root))
    if errors:
        print('Repository validation failed:')
        for err in errors:
            print(f'- {err}')
        return 1
    print('Repository validation passed.')
    return 0
