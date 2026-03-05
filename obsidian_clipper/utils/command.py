"""Safe command execution utilities."""

from __future__ import annotations

import logging
import shlex
import subprocess

logger = logging.getLogger(__name__)


def run_command_safely(
    command: list[str],
    capture_output: bool = True,
    timeout: int | None = None,
    check: bool = False,
    input_text: str | None = None,
) -> subprocess.CompletedProcess:
    """Run a command safely without shell injection risk.

    Args:
        command: Command and arguments as a list.
        capture_output: Whether to capture stdout/stderr.
        timeout: Timeout in seconds.
        check: Raise exception on non-zero exit.
        input_text: Text to pass to stdin.

    Returns:
        CompletedProcess instance.

    Raises:
        subprocess.CalledProcessError: If command fails and check=True.
        FileNotFoundError: If command not found.
        subprocess.TimeoutExpired: If command times out.
    """
    logger.debug(f"Running command: {shlex.join(command)}")
    return subprocess.run(
        command,
        capture_output=capture_output,
        text=True,
        timeout=timeout,
        check=check,
        input=input_text,
    )
