from __future__ import annotations

import json
from typing import Any

import yaml


def render_review_prompt(packet: dict[str, Any], role_contract: dict[str, Any]) -> str:
    return (
        "You are an AgentsFlow external read-only reviewer.\n"
        "Start from zero prior conversation context. Do not use or assume any forked orchestrator context. "
        "Review only the provided packet. Do not request repository access. Do not modify files. "
        "Do not run tests. Do not execute scripts. Do not produce patches. Do not update evidence. "
        "Return exactly one schema-valid reviewer-report JSON object and no markdown fence. "
        "Do not return prose outside JSON. If there are no findings, return an empty findings array "
        "and put residual uncertainty in summary or self_declared_limitations.\n\n"
        "Use this top-level JSON shape exactly: "
        '{"reviewer":{"id":"<reviewer_instance_id>","provider":"<provider>","role":"<reviewer_role>"},'
        '"review_context":{"run_id":"<run_id>","material_change_id":"<material_change_id>",'
        '"review_packet_path":"<review_packet_path>","reviewer_instance_id":"<reviewer_instance_id>"},'
        '"summary":"<summary>","findings":[],"requests_for_additional_verification":[],'
        '"self_declared_limitations":[]}. '
        "Each finding must include id, severity, title, evidence as an array of strings, and status "
        '"candidate-unvalidated".\n\n'
        "All findings must be candidate-unvalidated. Report missing mandatory evidence. "
        "Report plausible P0/P1 blockers even outside a focused role. "
        "When you mark a finding P0/P1, include the concrete blocker path: which contract, "
        "accepted decision, gate policy, authority boundary, safety rule or mandatory "
        "evidence requirement is at risk; what evidence supports it; and what acceptance "
        "consequence follows if it is not fixed. Risk-surface or Failure Path Matrix "
        "membership alone is not severity. "
        "The main/orchestrating agent validates relevance before findings affect workflow decisions.\n\n"
        "Your reviewer-report JSON must include review_context with run_id, material_change_id, "
        "review_packet_path and reviewer_instance_id copied from the review packet when present. "
        "Do not invent those values.\n\n"
        "Resolved reviewer role contract:\n"
        + yaml.safe_dump(role_contract, sort_keys=False)
        + "\n"
        "Review packet:\n"
        + json.dumps(packet, ensure_ascii=False, indent=2)
    )
