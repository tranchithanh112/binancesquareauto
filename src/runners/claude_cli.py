"""
Headless Claude Code CLI wrapper. Calls `claude -p <prompt>` and returns
the model's text response. Used to rewrite articles fully automatically
(no interactive session needed).

Requires the `claude` CLI on PATH (Claude Code installed).
"""
from __future__ import annotations
import subprocess
import tempfile
from typing import Optional


def rewrite(prompt: str, *, timeout: int = 180) -> tuple[Optional[str], Optional[str]]:
    """Send prompt to Claude headlessly. Returns (output, error_msg).
    Runs from a tempdir so the session doesn't auto-load CLAUDE.md / project
    files that confuse the model into thinking the prompt is a template."""
    with tempfile.TemporaryDirectory(prefix="claude_rewrite_") as cwd:
        try:
            # Pass prompt via stdin to avoid Windows argv length / quoting issues.
            proc = subprocess.run(
                ["claude", "-p", "--output-format", "text"],
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                shell=True,
                cwd=cwd,
            )
        except subprocess.TimeoutExpired:
            return None, f"claude CLI timeout after {timeout}s"
        except FileNotFoundError:
            return None, "claude CLI not found on PATH"
    if proc.returncode != 0:
        return None, f"claude CLI exit {proc.returncode}: {proc.stderr[:500]}"
    out = (proc.stdout or "").strip()
    if not out:
        return None, "claude CLI returned empty output"
    return out, None
