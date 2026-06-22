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
        "Prioritize substantive findings over output serialization. Return schema-valid reviewer-report JSON "
        "when you can do so without losing clarity; otherwise return clear structured findings for "
        "orchestrator normalization before gate use.\n\n"
        "All findings must be candidate-unvalidated. Report missing mandatory evidence. "
        "Report plausible P0/P1 blockers even outside a focused role. "
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
