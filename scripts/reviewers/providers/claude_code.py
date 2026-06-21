"""Claude Code CLI adapter for AgentsFlow external reviewer provider.

This adapter intentionally supports only subscription-local Claude Code CLI mode.
API-key based Claude usage is forbidden for the v0.2 MVP and is checked by the
calling wrapper before this module is invoked.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MODEL = "opus"
DEFAULT_EFFORT = "max"


@dataclass
class ProviderResult:
    stdout: str
    stderr: str
    exit_code: int
    command_display: str


def build_command(config: dict, prompt: str) -> list[str]:
    execution = config.get("execution", {}) or {}
    command = str(execution.get("command", "claude"))
    if command != "claude":
        raise ValueError("Claude Code external reviewer command must be claude in v0.2")
    args = [command, "-p", prompt]

    output_format = execution.get("output_format", "json")
    if output_format != "json":
        raise ValueError("Claude Code external reviewer output_format must be json in v0.2")
    if output_format:
        args.extend(["--output-format", str(output_format)])

    permission_mode = execution.get("permission_mode", "plan")
    if permission_mode != "plan":
        raise ValueError("Claude Code external reviewer permission_mode must be plan in v0.2")
    if permission_mode:
        args.extend(["--permission-mode", str(permission_mode)])

    model = execution.get("model", DEFAULT_MODEL)
    if model:
        args.extend(["--model", str(model)])

    effort = execution.get("effort", DEFAULT_EFFORT)
    if effort:
        args.extend(["--effort", str(effort)])

    max_turns = execution.get("max_turns")
    if max_turns is not None:
        args.extend(["--max-turns", str(max_turns)])

    if execution.get("no_session_persistence", True):
        args.append("--no-session-persistence")

    # Do not use --bare in subscription-local mode by default. Bare mode may bypass
    # local OAuth/keychain discovery in some Claude Code setups and is therefore not
    # the safe default for the accepted MVP policy.
    if execution.get("use_bare_mode", False):
        raise ValueError("Claude Code external reviewer use_bare_mode must be false in v0.2")

    return args


def invoke(config: dict, prompt: str, cwd: Path | None = None) -> ProviderResult:
    execution = config.get("execution", {}) or {}
    timeout_seconds = int(execution.get("timeout_seconds", 900))
    cmd = build_command(config, prompt)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    display = " ".join([cmd[0], "-p", "<prompt>", *cmd[3:]])
    return ProviderResult(
        stdout=proc.stdout,
        stderr=proc.stderr,
        exit_code=proc.returncode,
        command_display=display,
    )
