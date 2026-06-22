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


def build_command(config: dict, prompt_file: Path | str | None = None) -> list[str]:
    execution = config.get("execution", {}) or {}
    command = str(execution.get("command", "claude"))
    if command != "claude":
        raise ValueError("Claude Code external reviewer command must be claude in v0.2")
    args = [command, "-p"]
    if prompt_file is not None:
        prompt_path = Path(prompt_file)
        args.append(
            "Read the complete review prompt from this file and follow it exactly: "
            f"{prompt_path}"
        )
        args.extend(["--add-dir", str(prompt_path.parent)])

    output_format = execution.get("output_format", "json")
    if output_format != "json":
        raise ValueError("Claude Code external reviewer output_format must be json in v0.2")
    if output_format:
        args.extend(["--output-format", str(output_format)])

    permission_mode = execution.get("permission_mode", "default")
    if permission_mode != "default":
        raise ValueError("Claude Code external reviewer permission_mode must be default in v0.2")
    if permission_mode:
        args.extend(["--permission-mode", str(permission_mode)])

    args.extend(["--tools", str(execution.get("tools", ""))])

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
    prompt_transport = str(execution.get("prompt_transport", "stdin"))
    prompt_file: Path | None = None
    input_text: str | None = prompt
    if prompt_transport == "file":
        if cwd is None:
            raise ValueError("Claude Code file prompt transport requires a reviewer cwd")
        prompt_file = cwd / "agentsflow-review-prompt.md"
        prompt_file.write_text(prompt, encoding="utf-8")
        input_text = None
    elif prompt_transport != "stdin":
        raise ValueError("Claude Code prompt_transport must be stdin or file")
    cmd = build_command(config, prompt_file)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        input=input_text,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    display = " ".join([cmd[0], "-p", "<prompt-file>" if prompt_file else "<stdin>", *cmd[2:]])
    return ProviderResult(
        stdout=proc.stdout,
        stderr=proc.stderr,
        exit_code=proc.returncode,
        command_display=display,
    )
