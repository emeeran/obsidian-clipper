"""Desktop notification utilities."""

from __future__ import annotations

import logging
import sys

from .command import CommandError, run_command_safely

logger = logging.getLogger(__name__)


def notify(
    title: str,
    message: str,
    urgency: str = "normal",
    app_name: str = "Obsidian Clipper",
    icon: str | None = None,
) -> bool:
    """Send a desktop notification via notify-send.

    Falls back to the logger and stderr when notify-send is unavailable or exits
    non-zero, so a notification failure is never invisible on a hotkey-launched,
    detached process (where stdout goes nowhere).
    """
    try:
        cmd = ["notify-send", "-u", urgency, "-a", app_name]
        if icon:
            cmd.extend(["-i", icon])
        cmd.extend([title, message])
        run_command_safely(cmd, check=True)
        return True
    except (CommandError, OSError):
        # CommandError: notify-send exited non-zero (no D-Bus, headless, daemon down).
        # OSError / FileNotFoundError: notify-send not installed. Surface the message
        # via the logger (captured by LOG_FILE) and stderr so it isn't silently lost.
        logger.error("[%s] %s: %s", urgency.upper(), title, message)
        print(f"[{urgency.upper()}] {title}: {message}", file=sys.stderr)
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
