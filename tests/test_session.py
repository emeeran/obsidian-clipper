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
        # Filename includes preview (truncated to 40 + "...") + hash suffix
        name_part = filename.replace(".md", "")
        assert len(name_part) <= 50  # 40 + "..." + "_abcdef" (6-char hash)

    def test_ocr_text_used_when_no_text(self):
        session = CaptureSession(ocr_text="OCR result")
        result = session.get_note_filename()
        assert "OCR result" in result


class TestWorksCited:
    """Simple APA citation line rendered at the bottom of every note."""

    def test_citation_renders_apa_block(self):
        from obsidian_clipper.capture.citation import Citation, SourceType

        session = CaptureSession(
            text="captured body",
            timestamp="2026-10-11 10:00:00",
            citation=Citation(
                title="Some Page", source="Google Chrome", source_type=SourceType.BROWSER
            ),
        )
        md = session.to_markdown()
        assert "*Citation*: Some Page. (n.d.). Google Chrome. Retrieved October 11, 2026." in md
        assert md.index("*Citation*") > md.index("captured body")  # at the bottom

    def test_internal_source_labels_are_not_containers(self):
        from obsidian_clipper.capture.citation import Citation

        c = Citation(title="Doc", source="Window", page="42")
        assert c.format_apa() == "Doc. (n.d.). p. 42."

    def test_real_source_is_container(self):
        from obsidian_clipper.capture.citation import Citation

        c = Citation(title="Doc", source="Okular")
        assert c.format_apa() == "Doc. (n.d.). Okular."

    def test_no_citation_still_renders_date_only(self):
        session = CaptureSession(text="body", timestamp="2026-10-11 10:00:00")
        assert "*Citation*: Retrieved October 11, 2026." in session.to_markdown()


class TestReflowOcr:
    """OCR reflow: rejoin wraps, keep list items and paragraph breaks."""

    def test_rejoins_lowercase_wrap_across_blank_line(self):
        raw = "exit 0, note Landed\n\nin vault)"
        assert CaptureSession._reflow_ocr(raw) == "exit 0, note Landed in vault)"

    def test_dehyphenates_split_word(self):
        assert CaptureSession._reflow_ocr("docu-\nment root") == "document root"

    def test_keeps_bullet_items_separate(self):
        raw = "- first item here\n- second item"
        assert CaptureSession._reflow_ocr(raw) == raw

    def test_keeps_paragraph_break_before_capital(self):
        raw = "End of paragraph.\n\nNew paragraph starts"
        assert CaptureSession._reflow_ocr(raw) == "End of paragraph.\n\nNew paragraph starts"

    def test_collapses_spacing_runs(self):
        assert CaptureSession._reflow_ocr("a    spaced   line") == "a spaced line"

    def test_callout_uses_reflowed_text(self):
        session = CaptureSession(
            text="quoted", ocr_text="wrapped\n\ntext here"
        )
        md = session.to_markdown()
        assert "> wrapped text here" in md
