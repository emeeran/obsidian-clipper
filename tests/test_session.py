"""Tests for CaptureSession."""

from __future__ import annotations

from obsidian_clipper.workflow.session import CaptureSession


class TestGetNoteFilename:
    """Tests for CaptureSession.get_note_filename."""

    def test_basic_filename(self):
        session = CaptureSession(text="My note content")
        result = session.get_note_filename()
        assert result.endswith(".md")
        assert "My note content" in result

    def test_with_directory(self):
        session = CaptureSession(text="Hello")
        result = session.get_note_filename(directory="00-Inbox")
        assert result.startswith("00-Inbox/")
        assert result.endswith(".md")

    def test_directory_trailing_slash(self):
        session = CaptureSession(text="Hello")
        result = session.get_note_filename(directory="00-Inbox/")
        assert result.startswith("00-Inbox/")
        assert result.count("00-Inbox/") == 1

    def test_empty_directory(self):
        session = CaptureSession(text="Hello")
        result = session.get_note_filename(directory="")
        assert "/" not in result
        assert result.endswith(".md")

    def test_sanitizes_special_chars(self):
        session = CaptureSession(text='Text with <">:\\|?* chars')
        result = session.get_note_filename()
        for char in '<>:"/\\|?*':
            assert char not in result

    def test_sanitizes_newlines(self):
        session = CaptureSession(text="Line1\nLine2\rLine3")
        result = session.get_note_filename()
        assert "\n" not in result
        assert "\r" not in result

    def test_normalizes_whitespace(self):
        session = CaptureSession(text="Multiple   spaces   here")
        result = session.get_note_filename()
        assert "   " not in result

    def test_preview_length_limit(self):
        session = CaptureSession(text="A" * 100)
        result = session.get_note_filename()
        filename = result.rsplit("/", 1)[-1] if "/" in result else result
        # Filename (without .md) should be truncated via get_preview(40)
        name_part = filename.replace(".md", "")
        assert len(name_part) <= 43  # 40 + "..."

    def test_ocr_text_used_when_no_text(self):
        session = CaptureSession(ocr_text="OCR result")
        result = session.get_note_filename()
        assert "OCR result" in result
