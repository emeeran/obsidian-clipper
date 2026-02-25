"""Desktop notification utilities."""

from __future__ import annotations

import logging
import subprocess
from enum import Enum

from .command import run_command_safely

logger = logging.getLogger(__name__)


class Urgency(Enum):
    """Notification urgency levels."""

    LOW = "low"
    NORMAL = "normal"
    CRITICAL = "critical"


def notify(
    title: str,
    message: str,
    urgency: Urgency | str = Urgency.NORMAL,
    app_name: str = "Obsidian Clipper",
    icon: str | None = None,
) -> bool:
    """Send a desktop notification.

    Args:
        title: Notification title.
        message: Notification body.
        urgency: Urgency level (low, normal, critical).
        app_name: Application name for notification.
        icon: Optional icon name or path.

    Returns:
        True if notification was sent successfully.
    """
    if isinstance(urgency, str):
        urgency = Urgency(urgency.lower())

    try:
        cmd = ["notify-send", "-u", urgency.value, "-a", app_name]
        if icon:
            cmd.extend(["-i", icon])
        cmd.extend([title, message])

        run_command_safely(cmd, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to console output
        print(f"[{urgency.value.upper()}] {title}: {message}")
        return False


def notify_success(title: str, message: str) -> bool:
    """Send a success notification."""
    return notify(title, message, Urgency.NORMAL)


def notify_error(title: str, message: str) -> bool:
    """Send an error notification."""
    return notify(title, message, Urgency.CRITICAL)


def notify_warning(title: str, message: str) -> bool:
    """Send a warning notification."""
    return notify(title, message, Urgency.LOW)
