"""Tests for text capture utilities."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from obsidian_clipper.capture.text import get_active_window_title, get_selected_text


class TestGetSelectedText:
    """Tests for get_selected_text function."""

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_selected_text_xclip_success(self, mock_run):
        """Test successful text selection retrieval with xclip."""
        mock_result = MagicMock()
        mock_result.stdout = "Selected text content"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_selected_text()

        assert result == "Selected text content"

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_selected_text_empty(self, mock_run):
        """Test empty selection returns empty string."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_selected_text()

        assert result == ""

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_selected_text_whitespace_only(self, mock_run):
        """Test whitespace-only selection returns empty string."""
        mock_result = MagicMock()
        mock_result.stdout = "   \n\t  "
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_selected_text()

        assert result == ""

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_selected_text_multiline(self, mock_run):
        """Test multiline selection is preserved."""
        mock_result = MagicMock()
        mock_result.stdout = "Line 1\nLine 2\nLine 3"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_selected_text()

        assert result == "Line 1\nLine 2\nLine 3"

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_selected_text_xclip_fails_uses_wlpaste(self, mock_run):
        """Test fallback to wl-paste when xclip fails."""
        import subprocess

        # First call (xclip) fails
        mock_xclip = MagicMock()
        mock_xclip.side_effect = subprocess.CalledProcessError(1, [])

        # Second call (wl-paste) succeeds
        mock_wl = MagicMock()
        mock_wl.stdout = "Text from wl-paste"
        mock_wl.returncode = 0

        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["xclip"]),
            mock_wl,
        ]

        result = get_selected_text()

        assert result == "Text from wl-paste"

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_selected_text_all_fail(self, mock_run):
        """Test when all clipboard tools fail."""
        import subprocess

        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ["xclip"]),
            subprocess.CalledProcessError(1, ["wl-paste"]),
        ]

        result = get_selected_text()

        assert result == ""

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_selected_text_unicode(self, mock_run):
        """Test Unicode content is handled correctly."""
        mock_result = MagicMock()
        mock_result.stdout = "Unicode: 你好世界 🌍 مرحبا"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_selected_text()

        assert result == "Unicode: 你好世界 🌍 مرحبا"


class TestGetActiveWindowTitle:
    """Tests for get_active_window_title function."""

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_active_window_title_success(self, mock_run):
        """Test getting window title with xdotool."""
        mock_result = MagicMock()
        mock_result.stdout = "Document.pdf — Page 10 — Okular"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_active_window_title()

        assert result == "Document.pdf — Page 10 — Okular"

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_active_window_title_empty(self, mock_run):
        """Test empty window title."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_active_window_title()

        assert result == ""

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_active_window_title_whitespace(self, mock_run):
        """Test whitespace-only title is stripped."""
        mock_result = MagicMock()
        mock_result.stdout = "   \n  "
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_active_window_title()

        assert result == ""

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_active_window_title_command_fails(self, mock_run):
        """Test when xdotool command fails."""
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, ["xdotool"])

        result = get_active_window_title()

        assert result == ""

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_active_window_title_not_found(self, mock_run):
        """Test when xdotool is not installed."""
        mock_run.side_effect = FileNotFoundError("xdotool not found")

        result = get_active_window_title()

        assert result == ""

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_active_window_title_special_chars(self, mock_run):
        """Test window title with special characters."""
        mock_result = MagicMock()
        mock_result.stdout = "File (1) — App [v2.0] - Edition"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_active_window_title()

        assert result == "File (1) — App [v2.0] - Edition"

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_active_window_title_timeout(self, mock_run):
        """Test when xdotool times out."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(["xdotool"], 5)

        result = get_active_window_title()

        assert result == ""
