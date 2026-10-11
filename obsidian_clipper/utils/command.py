"""Safe command execution utilities."""

from __future__ import annotations

import logging
import shlex
import subprocess
from typing import Any, Literal, overload

logger = logging.getLogger(__name__)


class CommandError(Exception):
    """Raised when a command execution fails."""

    def __init__(self, message: str, returncode: int | None = None):
        super().__init__(message)
        self.returncode = returncode


@overload
def run_command_safely(
    command: list[str],
    capture_output: bool = True,
    timeout: int | None = None,
    check: bool = False,
    input_text: str | None = None,
    *,
    text: Literal[True] = True,
) -> subprocess.CompletedProcess[str]: ...


@overload
def run_command_safely(
    command: list[str],
    capture_output: bool = True,
    timeout: int | None = None,
    check: bool = False,
    input_text: str | None = None,
    *,
    text: Literal[False],
) -> subprocess.CompletedProcess[bytes]: ...


def run_command_safely(
    command: list[str],
    capture_output: bool = True,
    timeout: int | None = None,
    check: bool = False,
    input_text: str | None = None,
    text: bool = True,
) -> Any:
    """Run a command safely without shell injection risk.

    Args:
        command: Command and arguments as a list (never passed through a shell).
        capture_output: If True, capture stdout/stderr.
        timeout: Optional timeout in seconds.
        check: If True, raise CommandError on non-zero exit code.
        input_text: Optional stdin input (str when text=True, bytes when False).
        text: If True (default), decode stdout/stderr as text; if False, return
            raw bytes — e.g. for binary image data.

    Returns:
        A CompletedProcess whose stdout/stderr are str (text=True) or bytes.
    """
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
