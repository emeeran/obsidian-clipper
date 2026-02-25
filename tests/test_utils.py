"""Tests for utility modules."""

from __future__ import annotations

import subprocess
import time
from unittest.mock import MagicMock, patch

import pytest

from obsidian_clipper.utils import (
    CommandError,
    Urgency,
    notify,
    notify_error,
    notify_success,
    run_command_safely,
    run_command_with_fallback,
)
from obsidian_clipper.utils.retry import CircuitBreaker


class TestRunCommandSafely:
    """Tests for run_command_safely function."""

    @patch("obsidian_clipper.utils.command.subprocess.run")
    def test_success(self, mock_run):
        """Test successful command execution."""
        mock_result = MagicMock()
        mock_result.stdout = "output"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = run_command_safely(["echo", "test"])
        assert result.stdout == "output"

    @patch("obsidian_clipper.utils.command.subprocess.run")
    def test_check_raises_on_error(self, mock_run):
        """Test check=True raises on non-zero exit."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error"
        mock_run.return_value = mock_result

        with pytest.raises(CommandError) as exc_info:
            run_command_safely(["test"], check=True)
        assert exc_info.value.returncode == 1

    @patch("obsidian_clipper.utils.command.subprocess.run")
    def test_timeout_expired(self, mock_run):
        """Test timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=1)

        with pytest.raises(subprocess.TimeoutExpired):
            run_command_safely(["test"], timeout=1)

    def test_file_not_found(self):
        """Test FileNotFoundError for missing command."""
        with pytest.raises(FileNotFoundError):
            run_command_safely(["nonexistent_command_xyz"], check=True)


class TestRunWithFallback:
    """Tests for run_command_with_fallback function."""

    @patch("obsidian_clipper.utils.command.run_command_safely")
    def test_primary_success(self, mock_run):
        """Test primary command succeeds."""
        mock_result = MagicMock()
        mock_run.return_value = mock_result

        result = run_command_with_fallback(
            primary=["cmd1"],
            fallback=["cmd2"],
        )

        assert result == mock_result
        # Should only call once
        assert mock_run.call_count == 1

    @patch("obsidian_clipper.utils.command.run_command_safely")
    def test_fallback_used(self, mock_run):
        """Test fallback is used when primary fails."""
        mock_result = MagicMock()

        # First call fails, second succeeds
        mock_run.side_effect = [
            FileNotFoundError(),
            mock_result,
        ]

        result = run_command_with_fallback(
            primary=["cmd1"],
            fallback=["cmd2"],
        )

        assert result == mock_result
        assert mock_run.call_count == 2

    @patch("obsidian_clipper.utils.command.run_command_safely")
    def test_both_fail(self, mock_run):
        """Test returns None when both commands fail."""
        mock_run.side_effect = [
            FileNotFoundError(),
            FileNotFoundError(),
        ]

        result = run_command_with_fallback(
            primary=["cmd1"],
            fallback=["cmd2"],
        )

        assert result is None


class TestNotifications:
    """Tests for notification functions."""

    @patch("obsidian_clipper.utils.notification.run_command_safely")
    def test_notify_success(self, mock_run):
        """Test successful notification."""
        result = notify("Title", "Message")
        assert result is True
        mock_run.assert_called_once()

    @patch("obsidian_clipper.utils.notification.run_command_safely")
    def test_notify_fallback_to_print(self, mock_run, capsys):
        """Test notification falls back to print."""
        mock_run.side_effect = FileNotFoundError()
        result = notify("Title", "Message")

        assert result is False
        captured = capsys.readouterr()
        assert "[NORMAL]" in captured.out
        assert "Title" in captured.out

    def test_urgency_enum(self):
        """Test Urgency enum values."""
        assert Urgency.LOW.value == "low"
        assert Urgency.NORMAL.value == "normal"
        assert Urgency.CRITICAL.value == "critical"

    @patch("obsidian_clipper.utils.notification.notify")
    def test_notify_success_helper(self, mock_notify):
        """Test notify_success helper."""
        notify_success("Title", "Message")
        mock_notify.assert_called_once_with("Title", "Message", Urgency.NORMAL)

    @patch("obsidian_clipper.utils.notification.notify")
    def test_notify_error_helper(self, mock_notify):
        """Test notify_error helper."""
        notify_error("Title", "Message")
        mock_notify.assert_called_once_with("Title", "Message", Urgency.CRITICAL)


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_initial_state_allows_attempts(self):
        """Test circuit is closed initially."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
        assert cb.should_attempt() is True

    def test_allows_attempts_below_threshold(self):
        """Test circuit stays closed below failure threshold."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
        cb.record_failure()
        cb.record_failure()
        assert cb.should_attempt() is True

    def test_opens_at_threshold(self):
        """Test circuit opens when failure threshold is reached."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.should_attempt() is False

    def test_success_clears_failures(self):
        """Test success resets the circuit breaker."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.should_attempt() is True
        # Can record failures again after success
        cb.record_failure()
        assert cb.should_attempt() is True

    def test_recovers_after_timeout(self):
        """Test circuit recovers after recovery timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.should_attempt() is False

        # Wait for recovery timeout
        time.sleep(0.15)
        assert cb.should_attempt() is True

    def test_failure_threshold_respects_maxlen(self):
        """Test failure times deque respects maxlen."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
        # Record more than threshold
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        # Should still be open (deque keeps last 3)
        assert cb.should_attempt() is False

    def test_partial_recovery_stays_open(self):
        """Test circuit stays open if timeout not reached."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)
        cb.record_failure()
        cb.record_failure()
        # Small sleep, not enough for recovery
        time.sleep(0.05)
        assert cb.should_attempt() is False

    def test_custom_threshold_and_timeout(self):
        """Test custom threshold and timeout values."""
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 30.0

    def test_multiple_success_calls_safe(self):
        """Test calling success multiple times is safe."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60.0)
        cb.record_success()
        cb.record_success()
        cb.record_success()
        assert cb.should_attempt() is True
