"""Desktop notification utilities."""

from __future__ import annotations

import logging
import subprocess

from .command import run_command_safely

logger = logging.getLogger(__name__)


def notify(
    title: str,
    message: str,
    urgency: str = "normal",
    app_name: str = "Obsidian Clipper",
    icon: str | None = None,
) -> bool:
    """Send a desktop notification via notify-send."""
    try:
        cmd = ["notify-send", "-u", urgency, "-a", app_name]
        if icon:
            cmd.extend(["-i", icon])
        cmd.extend([title, message])
        run_command_safely(cmd, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"[{urgency.upper()}] {title}: {message}")
        return False


def notify_success(title: str, message: str, icon: str | None = None) -> bool:
    """Send a success notification."""
    return notify(title, message, "normal", icon=icon)


def notify_error(title: str, message: str) -> bool:
    """Send an error notification."""
    return notify(title, message, "critical")


def notify_warning(title: str, message: str) -> bool:
    """Send a warning notification."""
    return notify(title, message, "low")
