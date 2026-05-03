"""Tests for utility modules."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from obsidian_clipper.utils import (
    CommandError,
    notify,
    notify_error,
    notify_success,
    notify_warning,
    run_command_safely,
)


class TestRunCommandSafely:
    """Tests for run_command_safely function."""

    @patch("obsidian_clipper.utils.command.subprocess.run")
    def test_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = "output"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = run_command_safely(["echo", "test"])
        assert result.stdout == "output"

    @patch("obsidian_clipper.utils.command.subprocess.run")
    def test_check_raises_on_error(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error"
        mock_run.return_value = mock_result

        with pytest.raises(CommandError) as exc_info:
            run_command_safely(["test"], check=True)
        assert exc_info.value.returncode == 1

    @patch("obsidian_clipper.utils.command.subprocess.run")
    def test_timeout_expired(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=1)

        with pytest.raises(subprocess.TimeoutExpired):
            run_command_safely(["test"], timeout=1)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            run_command_safely(["nonexistent_command_xyz"], check=True)


class TestNotifications:
    """Tests for notification functions."""

    @patch("obsidian_clipper.utils.notification.run_command_safely")
    def test_notify_success(self, mock_run):
        result = notify("Title", "Message")
        assert result is True
        mock_run.assert_called_once()

    @patch("obsidian_clipper.utils.notification.run_command_safely")
    def test_notify_fallback_to_print(self, mock_run, capsys):
        mock_run.side_effect = FileNotFoundError()
        result = notify("Title", "Message")

        assert result is False
        captured = capsys.readouterr()
        assert "[NORMAL]" in captured.out
        assert "Title" in captured.out

    @patch("obsidian_clipper.utils.notification.notify")
    def test_notify_success_helper(self, mock_notify):
        notify_success("Title", "Message")
        mock_notify.assert_called_once_with("Title", "Message", "normal", icon=None)

    @patch("obsidian_clipper.utils.notification.notify")
    def test_notify_error_helper(self, mock_notify):
        notify_error("Title", "Message")
        mock_notify.assert_called_once_with("Title", "Message", "critical")

    @patch("obsidian_clipper.utils.notification.notify")
    def test_notify_warning_helper(self, mock_notify):
        notify_warning("Title", "Message")
        mock_notify.assert_called_once_with("Title", "Message", "low")

    @patch("obsidian_clipper.utils.notification.run_command_safely")
    def test_notify_string_urgency(self, mock_run):
        result = notify("Title", "Message", urgency="critical")
        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "critical" in call_args
