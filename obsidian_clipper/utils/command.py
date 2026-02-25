"""Safe command execution utilities."""

from __future__ import annotations

import logging
import shlex
import subprocess

logger = logging.getLogger(__name__)


class CommandError(Exception):
    """Raised when a command execution fails."""

    def __init__(self, message: str, returncode: int | None = None):
        super().__init__(message)
        self.returncode = returncode


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
        CommandError: If command fails and check=True.
        FileNotFoundError: If command not found.
        subprocess.TimeoutExpired: If command times out.
    """
    logger.debug(f"Running command: {shlex.join(command)}")

    result = subprocess.run(
        command,
        capture_output=capture_output,
        text=True,
        timeout=timeout,
        check=check,
        input=input_text,
    )

    if check and result.returncode != 0:
        raise CommandError(
            f"Command failed with code {result.returncode}: {result.stderr}",
            returncode=result.returncode,
        )

    return result


def run_command_with_fallback(
    primary: list[str],
    fallback: list[str],
    capture_output: bool = True,
    timeout: int | None = None,
) -> subprocess.CompletedProcess | None:
    """Run primary command, fall back to secondary if it fails.

    Args:
        primary: Primary command and arguments.
        fallback: Fallback command and arguments.
        capture_output: Whether to capture stdout/stderr.
        timeout: Timeout in seconds.

    Returns:
        CompletedProcess if successful, None if both fail.
    """
    try:
        return run_command_safely(
            primary, capture_output=capture_output, timeout=timeout, check=True
        )
    except (CommandError, FileNotFoundError, subprocess.TimeoutExpired):
        logger.debug(f"Primary command failed, trying fallback: {shlex.join(fallback)}")

    try:
        return run_command_safely(
            fallback, capture_output=capture_output, timeout=timeout, check=True
        )
    except (CommandError, FileNotFoundError, subprocess.TimeoutExpired):
        logger.debug("Fallback command also failed")
        return None
