"""Text capture utilities."""

from __future__ import annotations

import json
import logging
import subprocess

logger = logging.getLogger(__name__)


def get_selected_text() -> str:
    """Grab currently highlighted text from primary selection.

    Tries X11 (xclip) first, then falls back to Wayland (wl-paste).
    Only returns primary selection - never falls back to clipboard.

    Returns:
        Selected text, or empty string if nothing selected or tools unavailable.
    """
    # Try xclip first (X11 primary selection)
    try:
        result = subprocess.run(
            ["xclip", "-o", "-selection", "primary"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        text = result.stdout.strip()
        if text:
            return text
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        pass

    # Fallback to wl-paste (Wayland primary selection)
    try:
        result = subprocess.run(
            ["wl-paste", "-p"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        text = result.stdout.strip()
        if text:
            return text
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
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
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        title = result.stdout.strip()
        if title:
            return title
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        pass

    # Try hyprctl (Hyprland)
    try:
        result = subprocess.run(
            ["hyprctl", "activewindow", "-j"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        data = json.loads(result.stdout)
        title = data.get("title", "").strip()
        if title:
            return title
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
        KeyError,
    ):
        pass

    # Try swaymsg (Sway)
    try:
        result = subprocess.run(
            ["swaymsg", "-t", "get_tree"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        data = json.loads(result.stdout)

        def _find_focused(node: dict) -> str:
            if node.get("focused"):
                return node.get("name", "")
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
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
    ):
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
        subprocess.run(
            ["xclip", "-selection", clipboard],
            input=text.encode(),
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Try wl-copy (Wayland)
    try:
        cmd = ["wl-copy"]
        if clipboard == "primary":
            cmd.append("--primary")
        subprocess.run(
            cmd,
            input=text.encode(),
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return False
