#!/usr/bin/env python3
"""Generate minimal review metrics from invocation evidence."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


PREFLIGHT_STATUSES = {
    "provider_preflight_blocked",
    "preflight_blocked",
    "config_blocker",
    "permission_blocker",
}
COMPLETED_STATUSES = {"completed", "report-present", "invoked"}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_time(value: object) -> dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def elapsed_ms(start: object, finish: object) -> int | None:
    started = parse_time(start)
    finished = parse_time(finish)
    if not started or not finished:
        return None
    delta = finished - started
    milliseconds = int(delta.total_seconds() * 1000)
    return max(0, milliseconds)


def is_completed(status: str) -> bool:
    return status.lower() in COMPLETED_STATUSES


def resolve_ref(ref: object, source_path: Path) -> Path | None:
    if not isinstance(ref, str) or not ref:
        return None
    path = Path(ref)
    if path.is_absolute():
        return path
    cwd_path = Path.cwd() / path
    if cwd_path.exists():
        return cwd_path
    return source_path.parent / path


def load_optional_json(ref: object, source_path: Path) -> dict[str, Any]:
    path = resolve_ref(ref, source_path)
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def is_preflight_blocker(entry: dict[str, Any]) -> bool:
    status = str(entry.get("status") or "").lower()
    failure_stage = str(entry.get("failure_stage") or "").lower()
    error = str(entry.get("error") or "").lower()
    return (
        status in PREFLIGHT_STATUSES
        or "preflight" in status
        or "config" in status and "block" in status
        or "permission" in status and "block" in status
        or "preflight" in failure_stage
        or "permission" in error and "provider" in error
    )


def provider_runtime_ms(entry: dict[str, Any]) -> int | None:
    value = entry.get("provider_runtime_ms")
    if isinstance(value, int) and value >= 0:
        return value
    timing = entry.get("timing")
    if isinstance(timing, dict):
        nested = timing.get("provider_runtime_ms")
        if isinstance(nested, int) and nested >= 0:
            return nested
    return None


def reviewer_elapsed_ms(entry: dict[str, Any]) -> int | None:
    for started_key, finished_key in [
        ("started_at", "finished_at"),
        ("dispatch_started_at", "dispatch_finished_at"),
    ]:
        elapsed = elapsed_ms(entry.get(started_key), entry.get(finished_key))
        if elapsed is not None:
            return elapsed
    return None


def numeric(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def integer(value: object) -> int | None:
    number = numeric(value)
    if number is None:
        return None
    return int(number)


def first_string(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def exit_code(entry: dict[str, Any], metadata: dict[str, Any]) -> int | None:
    for source in [entry, metadata]:
        value = source.get("exit_code")
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
    return None


def retry_count(entry: dict[str, Any], metadata: dict[str, Any]) -> int:
    for source in [entry, metadata]:
        value = source.get("retry_count")
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value >= 0:
            return value
    return 0


def normalization_status(entry: dict[str, Any], metadata: dict[str, Any], completed: bool) -> str:
    for source in [entry, metadata]:
        normalization = source.get("normalization")
        if isinstance(normalization, dict):
            status = normalization.get("status")
            if isinstance(status, str) and status:
                return status
        status = source.get("normalization_status")
        if isinstance(status, str) and status:
            return status
    if completed and entry.get("report_path"):
        return "passed"
    if is_preflight_blocker(entry):
        return "not_applicable_preflight_blocker"
    return "not_available"


def add_nested_usage(
    usage: object,
    token_totals: dict[str, int],
    cost_totals: dict[str, Any],
) -> None:
    if not isinstance(usage, dict):
        return
    tokens = usage.get("tokens")
    if isinstance(tokens, dict) and tokens.get("available") is True:
        input_tokens = integer(tokens.get("input"))
        output_tokens = integer(tokens.get("output"))
        total_tokens = integer(tokens.get("total"))
        if input_tokens is None or output_tokens is None or total_tokens is None:
            raise ValueError("provider_usage.tokens available=true requires input, output and total")
        token_totals["input"] += input_tokens
        token_totals["output"] += output_tokens
        token_totals["total"] += total_tokens
        token_totals["available"] = 1
    cost = usage.get("cost")
    if isinstance(cost, dict) and cost.get("available") is True:
        amount = numeric(cost.get("amount"))
        currency = cost.get("currency")
        if amount is None or not isinstance(currency, str) or not currency:
            raise ValueError("provider_usage.cost available=true requires amount and currency")
        cost_totals["amount"] += amount
        cost_totals["currency"] = currency
        cost_totals["available"] = True


def add_provider_model_usage(
    model_usage: object,
    token_totals: dict[str, int],
) -> None:
    if not isinstance(model_usage, dict):
        return
    saw_tokens = False
    input_total = 0
    output_total = 0
    for payload in model_usage.values():
        if not isinstance(payload, dict):
            continue
        input_tokens = integer(payload.get("inputTokens")) or 0
        cache_read = integer(payload.get("cacheReadInputTokens")) or 0
        cache_creation = integer(payload.get("cacheCreationInputTokens")) or 0
        output_tokens = integer(payload.get("outputTokens")) or 0
        if input_tokens or cache_read or cache_creation or output_tokens:
            saw_tokens = True
        input_total += input_tokens + cache_read + cache_creation
        output_total += output_tokens
    if saw_tokens:
        token_totals["input"] += input_total
        token_totals["output"] += output_total
        token_totals["total"] += input_total + output_total
        token_totals["available"] = 1


def add_provider_total_cost(source: dict[str, Any], cost_totals: dict[str, Any]) -> bool:
    amount = numeric(source.get("provider_total_cost_usd"))
    if amount is None:
        return False
    cost_totals["amount"] += amount
    cost_totals["currency"] = "USD"
    cost_totals["available"] = True
    return True


def collect_provider_usage(reviewers: list[dict[str, Any]]) -> dict[str, Any]:
    token_total = 0
    token_input = 0
    token_output = 0
    token_totals = {"input": 0, "output": 0, "total": 0, "available": 0}
    cost_totals: dict[str, Any] = {"amount": 0.0, "currency": None, "available": False}

    for entry in reviewers:
        metadata = entry.get("_invocation_metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        add_nested_usage(entry.get("provider_usage"), token_totals, cost_totals)
        if not add_provider_total_cost(entry, cost_totals):
            add_provider_total_cost(metadata, cost_totals)
        model_usage = entry.get("provider_model_usage")
        if not isinstance(model_usage, dict):
            model_usage = metadata.get("provider_model_usage")
        add_provider_model_usage(model_usage, token_totals)

    token_input = token_totals["input"]
    token_output = token_totals["output"]
    token_total = token_totals["total"]
    if token_totals["available"]:
        token_payload: dict[str, Any] = {
            "available": True,
            "input": token_input,
            "output": token_output,
            "total": token_total or token_input + token_output,
        }
    else:
        token_payload = {
            "available": False,
            "reason": "Provider did not report token usage.",
        }

    if cost_totals["available"]:
        cost_payload: dict[str, Any] = {
            "available": True,
            "amount": cost_totals["amount"],
        }
        if cost_totals["currency"]:
            cost_payload["currency"] = cost_totals["currency"]
    else:
        cost_payload = {
            "available": False,
            "reason": "Provider did not report cost usage.",
        }

    return {"tokens": token_payload, "cost": cost_payload}


def generate_metrics(
    invocation_set_path: Path,
    run_id: str,
    workflow: str,
    material_change_id: str | None,
) -> dict[str, Any]:
    invocation_set = load_json(invocation_set_path)
    reviewers = [
        item
        for item in invocation_set.get("reviewers", []) or []
        if isinstance(item, dict)
    ]
    reviewer_rows: list[dict[str, Any]] = []
    review_packets: set[str] = set()
    reviewer_reports: set[str] = set()
    invocation_metadata_paths: set[str] = set()
    summed_elapsed = 0
    summed_provider_runtime = 0
    preflight_blockers = 0
    completed = 0

    for entry in reviewers:
        status = str(entry.get("status") or "")
        metadata = load_optional_json(entry.get("invocation_metadata_path"), invocation_set_path)
        entry["_invocation_metadata"] = metadata
        elapsed = reviewer_elapsed_ms(entry)
        provider_runtime = provider_runtime_ms(entry)
        if provider_runtime is None and metadata:
            provider_runtime = elapsed_ms(metadata.get("started_at"), metadata.get("finished_at"))
        preflight_blocker = is_preflight_blocker(entry)
        if preflight_blocker:
            preflight_blockers += 1
        if is_completed(status):
            completed += 1
            if elapsed is not None:
                summed_elapsed += elapsed
        if provider_runtime is not None:
            summed_provider_runtime += provider_runtime
        packet_path = first_string(entry.get("packet_path"))
        report_path = first_string(entry.get("report_path"))
        invocation_metadata_path = first_string(entry.get("invocation_metadata_path"))
        if packet_path:
            review_packets.add(packet_path)
        if report_path:
            reviewer_reports.add(report_path)
        if invocation_metadata_path:
            invocation_metadata_paths.add(invocation_metadata_path)
        reviewer_started_at = first_string(entry.get("started_at"), entry.get("dispatch_started_at"), metadata.get("started_at"))
        reviewer_finished_at = first_string(
            entry.get("finished_at"),
            entry.get("dispatch_finished_at"),
            entry.get("checked_at"),
            metadata.get("finished_at"),
        )
        code = exit_code(entry, metadata)
        reviewer_rows.append(
            {
                "reviewer": str(entry.get("reviewer") or ""),
                "provider": str(entry.get("provider") or ""),
                "model_family": str(entry.get("model_family") or ""),
                "status": status,
                "completed": is_completed(status),
                "provider_preflight_blocker": preflight_blocker,
                "review_packet_path": packet_path,
                "started_at": reviewer_started_at,
                "finished_at": reviewer_finished_at,
                "elapsed_ms": elapsed,
                "reviewer_started_at": reviewer_started_at,
                "reviewer_finished_at": reviewer_finished_at,
                "reviewer_elapsed_ms": elapsed,
                "provider_runtime_ms": provider_runtime,
                "retry_count": retry_count(entry, metadata),
                "timed_out": status.lower() == "timed-out" or "timed out" in str(entry.get("error") or "").lower(),
                "nonzero_exit": code is not None and code != 0,
                "normalization_status": normalization_status(entry, metadata, is_completed(status)),
                "report_path": report_path,
                "invocation_metadata_path": invocation_metadata_path,
                "error": entry.get("error"),
            }
        )

    review_elapsed = elapsed_ms(invocation_set.get("started_at"), invocation_set.get("finished_at"))
    substantive_cycles = 1 if invocation_set.get("status") == "completed" else 0
    return {
        "version": 1,
        "artifact_kind": "review_metrics",
        "artifact_scope": "run",
        "run_id": run_id,
        "workflow": workflow,
        "material_change_id": material_change_id,
        "generated_at": now_utc(),
        "source_artifacts": {
            "review_invocation_set": str(invocation_set_path),
            "review_prompt_contract": invocation_set.get("review_prompt_contract"),
            "external_reviewer_preflight": invocation_set.get("external_reviewer_preflight"),
            "review_packets": sorted(review_packets),
            "reviewer_reports": sorted(reviewer_reports),
            "invocation_metadata": sorted(invocation_metadata_paths),
            "finding_validation_report": None,
            "review_cycle_report": None,
        },
        "planned_reviewer_slots": len(reviewers),
        "completed_reviewer_invocations": completed,
        "provider_preflight_blockers": preflight_blockers,
        "substantive_review_cycles": substantive_cycles,
        "timing": {
            "review_phase_started_at": invocation_set.get("started_at"),
            "review_phase_finished_at": invocation_set.get("finished_at"),
            "review_phase_elapsed_ms": review_elapsed,
            "cycle_started_at": invocation_set.get("started_at"),
            "cycle_finished_at": invocation_set.get("finished_at"),
            "cycle_elapsed_ms": review_elapsed,
            "summed_reviewer_elapsed_ms": summed_elapsed,
            "summed_provider_runtime_ms": summed_provider_runtime,
        },
        "reviewer_invocations": reviewer_rows,
        "provider_usage": collect_provider_usage(reviewers),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--review-invocation-set", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--material-change-id")
    args = parser.parse_args()

    metrics = generate_metrics(
        Path(args.review_invocation_set),
        args.run_id,
        args.workflow,
        args.material_change_id,
    )
    write_json(Path(args.output), metrics)
    print(f"Review metrics written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
