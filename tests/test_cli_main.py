"""Orchestration tests for the CLI main entry point.

These cover the main() control-flow paths that the existing unit tests left
thin: profile application, --dry-run, --daily, the obsidian:// URI fallback,
the fzf note picker, the no-display hint, and the URI length guard.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from obsidian_clipper.cli.main import _save_via_uri, _validate_session, main
from obsidian_clipper.workflow import CaptureSession


@pytest.fixture
def mocks():
    """Patch the heavy dependencies of main() and return them by name."""
    with (
        patch("obsidian_clipper.cli.main.validate_config") as validate,
        patch("obsidian_clipper.cli.main.get_config") as get_config,
        patch("obsidian_clipper.cli.main.ObsidianClient") as client_class,
        patch("obsidian_clipper.cli.main.prepare_capture_session") as prepare,
        patch("obsidian_clipper.cli.main.notify_success") as notify_success,
        patch("obsidian_clipper.cli.main.notify_error") as notify_error,
    ):
        config = MagicMock()
        config.default_note = "00-Inbox/Quick Captures.md"
        get_config.return_value = config

        client = MagicMock()
        client.check_connection.return_value = True
        client_class.return_value.__enter__.return_value = client

        yield {
            "validate": validate,
            "get_config": get_config,
            "client_class": client_class,
            "client": client,
            "config": config,
            "prepare": prepare,
            "notify_success": notify_success,
            "notify_error": notify_error,
        }


class TestDryRun:
    def test_dry_run_prints_markdown_and_exits_zero(self, mocks, capsys):
        mocks["prepare"].return_value = CaptureSession(text="Hello world")

        with patch("sys.argv", ["clipper", "--dry-run"]):
            assert main() == 0

        out = capsys.readouterr().out
        assert "Hello world" in out
        mocks["client"].create_note.assert_not_called()


class TestDailyNote:
    def test_daily_appends_to_periodic_note(self, mocks):
        mocks["prepare"].return_value = CaptureSession(text="Daily capture")
        mocks["client"].append_periodic_note.return_value = True

        with patch("sys.argv", ["clipper", "--daily"]):
            assert main() == 0

        mocks["client"].append_periodic_note.assert_called_once()
        assert mocks["client"].append_periodic_note.call_args[0][0] == "daily"
        mocks["notify_success"].assert_called_once()

    def test_daily_failure_notifies_error(self, mocks):
        mocks["prepare"].return_value = CaptureSession(text="Daily capture")
        mocks["client"].append_periodic_note.return_value = False

        with patch("sys.argv", ["clipper", "--daily"]):
            assert main() == 1

        mocks["notify_error"].assert_called_once()


class TestUriFallback:
    def test_uri_fallback_on_connection_failure(self, mocks):
        mocks["client"].check_connection.return_value = False
        mocks["prepare"].return_value = CaptureSession(text="Some text")

        with (
            patch("obsidian_clipper.cli.main._save_via_uri", return_value=True),
            patch("sys.argv", ["clipper"]),
        ):
            assert main() == 0

        mocks["notify_error"].assert_not_called()

    def test_no_content_skips_uri_fallback(self, mocks):
        mocks["client"].check_connection.return_value = False
        mocks["prepare"].return_value = CaptureSession()  # empty

        with (
            patch("obsidian_clipper.cli.main._save_via_uri", return_value=True),
            patch("sys.argv", ["clipper"]),
        ):
            assert main() == 1

        mocks["notify_error"].assert_called_once()


class TestFzfPicker:
    def test_pick_uses_selected_note(self, mocks):
        mocks["prepare"].return_value = CaptureSession(text="Picked content")
        mocks["client"].create_note.return_value = True

        with (
            patch("obsidian_clipper.cli.main._pick_note_with_fzf", return_value="00-Inbox/"),
            patch("sys.argv", ["clipper", "--pick"]),
        ):
            assert main() == 0

        mocks["client"].create_note.assert_called_once()

    def test_pick_cancelled_notifies_error(self, mocks):
        with (
            patch("obsidian_clipper.cli.main._pick_note_with_fzf", return_value=None),
            patch("sys.argv", ["clipper", "--pick"]),
        ):
            assert main() == 1

        mocks["notify_error"].assert_called_once()


class TestProfileApplication:
    def test_research_profile_appends_to_profile_note(self, mocks):
        mocks["prepare"].return_value = CaptureSession(text="Profile text")
        mocks["client"].ensure_note_exists.return_value = True
        mocks["client"].append_to_note.return_value = True
        profile = {
            "tags": "research,reading",
            "note": "00-Inbox/Research Note.md",
            "ocr": True,
            "append": True,
        }

        with (
            patch("obsidian_clipper.cli.main.get_profile", return_value=profile),
            patch("sys.argv", ["clipper", "--profile", "research"]),
        ):
            assert main() == 0

        # The research profile appends to its own note path.
        mocks["client"].append_to_note.assert_called_once()
        assert mocks["client"].append_to_note.call_args[0][0] == "00-Inbox/Research Note.md"

    def test_unknown_profile_returns_error(self, mocks, capsys):
        with (
            patch("obsidian_clipper.cli.main.get_profile", side_effect=ValueError("nope")),
            patch("sys.argv", ["clipper", "--profile", "bogus"]),
        ):
            assert main() == 1


class TestValidateSessionDisplayHint:
    def _args(self):
        args = MagicMock()
        args.screenshot = False
        args.ocr = True
        args.no_ocr = False
        return args

    def test_no_display_hint_appended_when_no_text(self):
        session = CaptureSession()  # no text
        with patch(
            "obsidian_clipper.capture.screenshot.detect_display_server", return_value="unknown"
        ):
            msg = _validate_session(session, self._args())
        assert "No text selected" in msg
        assert "No display server" in msg

    def test_no_hint_when_display_present(self):
        session = CaptureSession()
        with patch(
            "obsidian_clipper.capture.screenshot.detect_display_server", return_value="x11"
        ):
            msg = _validate_session(session, self._args())
        assert "No text selected" in msg
        assert "No display server" not in msg


class TestUriLengthGuard:
    def test_warns_when_content_exceeds_uri_limit(self, caplog):
        session = CaptureSession(text="x" * 5000)
        caplog.set_level(logging.WARNING)

        with patch("obsidian_clipper.cli.main.run_command_safely") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            _save_via_uri(session)

        assert any("URI length" in r.getMessage() for r in caplog.records)

    def test_no_warning_for_short_content(self, caplog):
        session = CaptureSession(text="short")
        caplog.set_level(logging.WARNING)

        with patch("obsidian_clipper.cli.main.run_command_safely") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            _save_via_uri(session)

        assert not any("URI length" in r.getMessage() for r in caplog.records)


class TestMainErrorHandling:
    """Covers the top-level exception handlers in main() (M16)."""

    def test_config_error_maps_to_exit_1(self, mocks):
        from obsidian_clipper.exceptions import ConfigurationError

        mocks["validate"].side_effect = ConfigurationError("bad config")

        with patch("sys.argv", ["clipper"]):
            assert main() == 1
        mocks["notify_error"].assert_called()

    def test_unexpected_error_maps_to_exit_1(self, mocks):
        mocks["prepare"].side_effect = RuntimeError("kaboom")

        with patch("sys.argv", ["clipper"]):
            assert main() == 1
        mocks["notify_error"].assert_called()

    def test_keyboard_interrupt_returns_130(self, mocks):
        mocks["prepare"].side_effect = KeyboardInterrupt

        with patch("sys.argv", ["clipper"]):
            assert main() == 130
