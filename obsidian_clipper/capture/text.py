"""Text capture utilities."""

from __future__ import annotations

import json
import logging
import subprocess

from ..utils.command import CommandError, run_command_safely

logger = logging.getLogger(__name__)


def get_selected_text(selection: str = "primary") -> str:
    """Grab currently highlighted text from primary selection or clipboard.

    Tries X11 (xclip) first, then falls back to Wayland (wl-paste). By default
    reads the primary selection; pass ``selection="clipboard"`` to read the
    clipboard instead — useful on Wayland, where many apps never populate the
    primary selection.

    Args:
        selection: Which selection to read — "primary" (default) or "clipboard".

    Returns:
        Selected text, or empty string if nothing selected or tools unavailable.
    """
    # Try xclip first (X11). xclip uses the same names for both selections.
    try:
        result = run_command_safely(
            ["xclip", "-o", "-selection", selection],
            timeout=5,
            check=True,
        )
        text = result.stdout.strip()
        if text:
            return text
    except FileNotFoundError:
        logger.debug("xclip not found (install: sudo apt install xclip)")
    except (CommandError, subprocess.TimeoutExpired):
        pass

    # Fallback to wl-paste (Wayland)
    try:
        cmd = ["wl-paste"]
        if selection == "primary":
            cmd.append("-p")
        result = run_command_safely(cmd, timeout=5, check=True)
        text = result.stdout.strip()
        if text:
            return text
    except FileNotFoundError:
        logger.debug("wl-paste not found (install: sudo apt install wl-clipboard)")
    except (CommandError, subprocess.TimeoutExpired):
        pass

    return ""


def get_active_window_title() -> str:
    """Get the title of the currently active window.

    Tries xdotool (X11), then falls back to Wayland tools (hyprctl, swaymsg).

    Returns:
        Window title, or empty string if unavailable.
    """
    # Try xdotool (X11)
    try:
        result = run_command_safely(
            ["xdotool", "getactivewindow", "getwindowname"],
            timeout=5,
            check=True,
        )
        title = result.stdout.strip()
        if title:
            return title
    except FileNotFoundError:
        logger.debug("xdotool not found (install: sudo apt install xdotool)")
    except (CommandError, subprocess.TimeoutExpired):
        pass

    # Try hyprctl (Hyprland)
    try:
        result = run_command_safely(
            ["hyprctl", "activewindow", "-j"],
            timeout=5,
            check=True,
        )
        data = json.loads(result.stdout)
        title = str(data.get("title", "")).strip()
        if title:
            return title
    except FileNotFoundError:
        logger.debug("hyprctl not found (install Hyprland window manager)")
    except (CommandError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
        pass

    # Try swaymsg (Sway)
    try:
        result = run_command_safely(
            ["swaymsg", "-t", "get_tree"],
            timeout=5,
            check=True,
        )
        data = json.loads(result.stdout)

        def _find_focused(node: dict) -> str:
            if node.get("focused"):
                return str(node.get("name", ""))
            for child in node.get("nodes", []):
                title = _find_focused(child)
                if title:
                    return title
            for child in node.get("floating_nodes", []):
                title = _find_focused(child)
                if title:
                    return title
            return ""

        title = _find_focused(data).strip()
        if title:
            return title
    except FileNotFoundError:
        logger.debug("swaymsg not found (install: sudo apt install sway)")
    except (CommandError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass

    return ""


def copy_to_clipboard(text: str, clipboard: str = "clipboard") -> bool:
    """Copy text to system clipboard.

    Args:
        text: Text to copy.
        clipboard: Which clipboard to use ('clipboard', 'primary', 'secondary').

    Returns:
        True if successful.
    """
    # Try xclip first
    try:
        run_command_safely(
            ["xclip", "-selection", clipboard],
            input_text=text,
            check=True,
        )
        return True
    except (CommandError, FileNotFoundError):
        pass

    # Try wl-copy (Wayland)
    try:
        cmd = ["wl-copy"]
        if clipboard == "primary":
            cmd.append("--primary")
        run_command_safely(cmd, input_text=text, check=True)
        return True
    except (CommandError, FileNotFoundError):
        pass

    return False
