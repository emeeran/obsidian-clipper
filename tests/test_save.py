"""Tests for upload_screenshot and process_and_save_content (covers M15)."""

from __future__ import annotations

from unittest.mock import MagicMock

from obsidian_clipper.workflow import (
    CaptureSession,
    process_and_save_content,
    upload_screenshot,
)


class TestUploadScreenshot:
    def test_no_screenshot_returns_false(self):
        session = CaptureSession(text="hi")
        client = MagicMock()
        assert upload_screenshot(session, client) is False
        client.upload_image.assert_not_called()

    def test_successful_upload_sets_flag_and_cleans_temp(self, tmp_path):
        shot = tmp_path / "cap.png"
        shot.write_bytes(b"\x89PNG\r\n\x1a\n")
        session = CaptureSession(screenshot_path=shot, img_filename="cap.png")
        client = MagicMock()
        client.upload_image.return_value = True

        assert upload_screenshot(session, client) is True
        assert session.screenshot_success is True
        assert not shot.exists()  # temp file removed

    def test_failed_upload_still_cleans_temp(self, tmp_path):
        shot = tmp_path / "cap.png"
        shot.write_bytes(b"\x89PNG\r\n\x1a\n")
        session = CaptureSession(screenshot_path=shot, img_filename="cap.png")
        client = MagicMock()
        client.upload_image.return_value = False

        assert upload_screenshot(session, client) is False
        assert session.screenshot_success is False
        assert not shot.exists()  # cleanup is unconditional (never leaks)


class TestProcessAndSaveContent:
    def test_create_path_uploads_and_creates_note(self, tmp_path):
        shot = tmp_path / "cap.png"
        shot.write_bytes(b"\x89PNG\r\n\x1a\n")
        session = CaptureSession(
            text="hello", screenshot_path=shot, img_filename="cap.png"
        )
        client = MagicMock()
        client.upload_image.return_value = True
        client.create_note.return_value = True

        assert process_and_save_content(session, client, target_dir="Inbox/") is True

        client.upload_image.assert_called_once()
        client.create_note.assert_called_once()
        # New note is created under the target directory.
        assert client.create_note.call_args[0][0].startswith("Inbox/")

    def test_append_path_ensures_then_appends(self):
        session = CaptureSession(text="hello")
        client = MagicMock()
        client.ensure_note_exists.return_value = True
        client.append_to_note.return_value = True

        assert (
            process_and_save_content(
                session, client, target_dir="Notes/Journal.md", append=True
            )
            is True
        )
        client.ensure_note_exists.assert_called_once_with("Notes/Journal.md")
        client.append_to_note.assert_called_once()

    def test_append_returns_false_when_note_cannot_be_ensured(self):
        session = CaptureSession(text="hello")
        client = MagicMock()
        client.ensure_note_exists.return_value = False

        assert (
            process_and_save_content(
                session, client, target_dir="Notes/J.md", append=True
            )
            is False
        )
        client.append_to_note.assert_not_called()
