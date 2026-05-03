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
    text: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a command safely without shell injection risk."""
    logger.debug("Running command: %s", shlex.join(command))

    result = subprocess.run(
        command,
        capture_output=capture_output,
        text=text,
        timeout=timeout,
        check=False,
        input=input_text,
    )

    if check and result.returncode != 0:
        raise CommandError(
            f"Command failed with code {result.returncode}: {result.stderr}",
            returncode=result.returncode,
        )

    return result
