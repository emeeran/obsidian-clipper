"""Tests for text capture utilities."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from obsidian_clipper.capture.text import (
    copy_to_clipboard,
    get_active_window_title,
    get_selected_text,
)
from obsidian_clipper.utils.command import CommandError


class TestGetSelectedText:
    """Tests for get_selected_text function."""

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_selected_text_xclip_success(self, mock_run):
        """Test successful text selection retrieval with xclip."""
        mock_result = MagicMock()
        mock_result.stdout = "Selected text content"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_selected_text()

        assert result == "Selected text content"

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_selected_text_empty(self, mock_run):
        """Test empty selection returns empty string."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_selected_text()

        assert result == ""

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_selected_text_whitespace_only(self, mock_run):
        """Test whitespace-only selection returns empty string."""
        mock_result = MagicMock()
        mock_result.stdout = "   \n\t  "
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_selected_text()

        assert result == ""

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_selected_text_multiline(self, mock_run):
        """Test multiline selection is preserved."""
        mock_result = MagicMock()
        mock_result.stdout = "Line 1\nLine 2\nLine 3"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_selected_text()

        assert result == "Line 1\nLine 2\nLine 3"

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_selected_text_xclip_fails_uses_wlpaste(self, mock_run):
        """Test fallback to wl-paste when xclip fails."""
        # First call (xclip) fails, second call (wl-paste) succeeds
        mock_wl = MagicMock()
        mock_wl.stdout = "Text from wl-paste"
        mock_wl.returncode = 0

        mock_run.side_effect = [CommandError("xclip failed"), mock_wl]

        result = get_selected_text()

        assert result == "Text from wl-paste"

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_selected_text_all_fail(self, mock_run):
        """Test when all clipboard tools fail."""
        mock_run.side_effect = [CommandError("xclip failed"), CommandError("wl-paste failed")]

        result = get_selected_text()

        assert result == ""

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_selected_text_unicode(self, mock_run):
        """Test Unicode content is handled correctly."""
        mock_result = MagicMock()
        mock_result.stdout = "Unicode: 你好世界 🌍 مرحبا"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_selected_text()

        assert result == "Unicode: 你好世界 🌍 مرحبا"

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_selected_text_clipboard_reads_clipboard_selection(self, mock_run):
        """Test selection='clipboard' targets the clipboard, not primary."""
        mock_result = MagicMock()
        mock_result.stdout = "Clipboard text"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_selected_text(selection="clipboard")

        assert result == "Clipboard text"
        cmd = mock_run.call_args[0][0]
        assert cmd == ["xclip", "-o", "-selection", "clipboard"]

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_selected_text_clipboard_wlpaste_omits_primary_flag(self, mock_run):
        """Test wl-paste fallback omits -p for clipboard selection."""
        mock_wl = MagicMock()
        mock_wl.stdout = "From clipboard"
        mock_wl.returncode = 0
        mock_run.side_effect = [CommandError("xclip failed"), mock_wl]

        result = get_selected_text(selection="clipboard")

        assert result == "From clipboard"
        wl_cmd = mock_run.call_args_list[1][0][0]
        assert wl_cmd == ["wl-paste"]


class TestGetActiveWindowTitle:
    """Tests for get_active_window_title function."""

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_active_window_title_success(self, mock_run):
        """Test getting window title with xdotool."""
        mock_result = MagicMock()
        mock_result.stdout = "Document.pdf — Page 10 — Okular"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_active_window_title()

        assert result == "Document.pdf — Page 10 — Okular"

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_active_window_title_empty(self, mock_run):
        """Test empty window title."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_active_window_title()

        assert result == ""

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_active_window_title_whitespace(self, mock_run):
        """Test whitespace-only title is stripped."""
        mock_result = MagicMock()
        mock_result.stdout = "   \n  "
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_active_window_title()

        assert result == ""

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_active_window_title_command_fails(self, mock_run):
        """Test when xdotool command fails."""
        mock_run.side_effect = CommandError("xdotool failed")

        result = get_active_window_title()

        assert result == ""

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_active_window_title_not_found(self, mock_run):
        """Test when xdotool is not installed."""
        mock_run.side_effect = FileNotFoundError("xdotool not found")

        result = get_active_window_title()

        assert result == ""

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_active_window_title_special_chars(self, mock_run):
        """Test window title with special characters."""
        mock_result = MagicMock()
        mock_result.stdout = "File (1) — App [v2.0] - Edition"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_active_window_title()

        assert result == "File (1) — App [v2.0] - Edition"

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_active_window_title_timeout(self, mock_run):
        """Test when xdotool times out."""
        mock_run.side_effect = subprocess.TimeoutExpired(["xdotool"], 5)

        result = get_active_window_title()

        assert result == ""

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_active_window_title_hyprctl_fallback(self, mock_run):
        """Test hyprctl fallback when xdotool returns empty."""

        xdotool_result = MagicMock()
        xdotool_result.stdout = "  "
        xdotool_result.returncode = 0

        hyprctl_result = MagicMock()
        hyprctl_result.stdout = '{"title": "Hyprland Window Title"}'
        hyprctl_result.returncode = 0

        mock_run.side_effect = [xdotool_result, hyprctl_result]

        result = get_active_window_title()

        assert result == "Hyprland Window Title"

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_active_window_title_hyprctl_xdotool_fails(self, mock_run):
        """Test hyprctl fallback when xdotool fails entirely."""
        hyprctl_result = MagicMock()
        hyprctl_result.stdout = '{"title": "My App"}'
        hyprctl_result.returncode = 0

        mock_run.side_effect = [CommandError("xdotool failed"), hyprctl_result]

        result = get_active_window_title()

        assert result == "My App"

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_active_window_title_swaymsg_fallback(self, mock_run):
        """Test swaymsg fallback when xdotool and hyprctl both fail."""
        sway_result = MagicMock()
        sway_result.stdout = '{"nodes": [{"focused": true, "name": "Sway Window"}]}'
        sway_result.returncode = 0

        mock_run.side_effect = [
            CommandError("xdotool failed"),
            CommandError("hyprctl failed"),
            sway_result,
        ]

        result = get_active_window_title()

        assert result == "Sway Window"

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_active_window_title_swaymsg_nested(self, mock_run):
        """Test swaymsg fallback with nested window tree."""
        sway_result = MagicMock()
        sway_result.stdout = (
            '{"nodes": [{"focused": false, "nodes": ['
            '{"focused": true, "name": "Nested Window"}]'
            "}]} "
        )
        sway_result.returncode = 0

        mock_run.side_effect = [
            CommandError("xdotool failed"),
            CommandError("hyprctl failed"),
            sway_result,
        ]

        result = get_active_window_title()

        assert result == "Nested Window"

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_active_window_title_swaymsg_floating(self, mock_run):
        """Test swaymsg fallback finds focused in floating_nodes."""
        sway_result = MagicMock()
        sway_result.stdout = (
            '{"nodes": [{"focused": false}], '
            '"floating_nodes": [{"focused": true, "name": "Floating Window"}]}'
        )
        sway_result.returncode = 0

        mock_run.side_effect = [
            CommandError("xdotool failed"),
            CommandError("hyprctl failed"),
            sway_result,
        ]

        result = get_active_window_title()

        assert result == "Floating Window"

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_get_active_window_title_hyprctl_bad_json(self, mock_run):
        """Test graceful handling of malformed hyprctl JSON."""
        bad_json_result = MagicMock()
        bad_json_result.stdout = "not json"
        bad_json_result.returncode = 0

        mock_run.side_effect = [
            CommandError("xdotool failed"),
            bad_json_result,
            CommandError("swaymsg failed"),
        ]

        result = get_active_window_title()

        assert result == ""


class TestCopyToClipboard:
    """Tests for copy_to_clipboard function."""

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_copy_with_xclip_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = copy_to_clipboard("Hello world")

        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "xclip"
        assert args[1] == "-selection"
        assert args[2] == "clipboard"

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_copy_falls_back_to_wl_copy(self, mock_run):
        mock_run.side_effect = [
            CommandError("xclip failed"),
            MagicMock(returncode=0),
        ]

        result = copy_to_clipboard("Hello")

        assert result is True
        assert mock_run.call_count == 2

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_copy_both_fail(self, mock_run):
        mock_run.side_effect = [
            CommandError("xclip failed"),
            CommandError("wl-copy failed"),
        ]

        result = copy_to_clipboard("Hello")

        assert result is False

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_copy_primary_selection(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = copy_to_clipboard("Hello", clipboard="primary")

        assert result is True
        args = mock_run.call_args[0][0]
        assert args[2] == "primary"

    @patch("obsidian_clipper.capture.text.run_command_safely")
    def test_copy_primary_wl_copy_flag(self, mock_run):
        mock_run.side_effect = [
            CommandError("xclip failed"),
            MagicMock(returncode=0),
        ]

        result = copy_to_clipboard("Hello", clipboard="primary")

        assert result is True
        # Second call should be wl-copy --primary
        wl_call = mock_run.call_args_list[1]
        assert "--primary" in wl_call[0][0]
