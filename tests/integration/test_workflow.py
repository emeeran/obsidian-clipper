"""Integration tests for Obsidian Clipper workflow."""

from __future__ import annotations

from unittest.mock import patch

from obsidian_clipper.capture import Citation, SourceType
from obsidian_clipper.workflow import CaptureSession
from obsidian_clipper.workflow.capture import _get_fallback_citation


class TestWorkflowIntegration:
    """Integration tests for capture workflow."""

    def test_capture_session_text_only(self):
        """Test capture session with text only."""
        session = CaptureSession(text="Selected text content")

        assert session.has_content() is True
        assert "Selected text content" in session.to_markdown()
        assert session.get_preview() == "Selected text content"

    def test_capture_session_screenshot_only(self):
        """Test capture session with screenshot only."""
        session = CaptureSession(
            screenshot_success=True,
            img_filename="screenshot.png",
        )

        assert session.has_content() is True
        assert "![[screenshot.png]]" in session.to_markdown()
        assert session.get_preview() == "Screenshot"

    def test_capture_session_ocr_only(self):
        """Test capture session with OCR text only."""
        session = CaptureSession(ocr_text="Extracted OCR text")

        assert session.has_content() is True
        assert "Extracted OCR text" in session.to_markdown()
        assert session.get_preview() == "Extracted OCR text"

    def test_capture_session_full_workflow(self):
        """Test complete capture session with all content types."""
        session = CaptureSession(
            text="Selected text",
            ocr_text="OCR extracted text",
            citation=Citation(
                title="Document.pdf",
                page="42",
                source="Okular",
                source_type=SourceType.PDF,
            ),
            screenshot_success=True,
            img_filename="capture.png",
        )

        markdown = session.to_markdown()

        assert "Selected text" in markdown
        assert "OCR extracted text" in markdown
        assert "Document.pdf, p. 42" in markdown
        assert "![[capture.png]]" in markdown

    def test_capture_session_long_text_preview(self):
        """Test preview truncation for long text."""
        long_text = "A" * 100
        session = CaptureSession(text=long_text)

        preview = session.get_preview(max_length=50)

        assert len(preview) == 53  # 50 + "..."
        assert preview.endswith("...")


class TestGetFallbackCitation:
    """Tests for _get_fallback_citation helper."""

    @patch("obsidian_clipper.workflow.capture.get_active_window_title")
    def test_fallback_from_active_window(self, mock_title):
        """Test getting fallback citation from active window."""
        mock_title.return_value = "Interesting Article - Browser"

        citation = _get_fallback_citation("")

        assert citation is not None
        assert citation.title == "Interesting Article - Browser"
        assert citation.source == "Window"
        assert citation.source_type == SourceType.UNKNOWN

    @patch("obsidian_clipper.workflow.capture.get_active_window_title")
    def test_fallback_uses_pre_capture_if_available(self, mock_title):
        """Test uses pre-capture title if available."""
        citation = _get_fallback_citation("Pre-capture Window Title")

        assert citation is not None
        assert citation.title == "Pre-capture Window Title"
        mock_title.assert_not_called()

    @patch("obsidian_clipper.workflow.capture.get_active_window_title")
    def test_fallback_includes_pdf_readers(self, mock_title):
        """Test fallback now includes PDF reader windows."""
        mock_title.return_value = "Document.pdf — Okular"

        citation = _get_fallback_citation("")

        assert citation is not None
        assert citation.title == "Document.pdf — Okular"

    @patch("obsidian_clipper.workflow.capture.get_active_window_title")
    def test_fallback_includes_epub_readers(self, mock_title):
        """Test fallback now includes EPUB reader windows."""
        mock_title.return_value = "Book — Foliate"

        citation = _get_fallback_citation("")

        assert citation is not None
        assert citation.title == "Book — Foliate"


class TestMarkdownFormatting:
    """Tests for markdown output formatting."""

    def test_header_format(self):
        """Test header format in markdown output."""
        session = CaptureSession(text="Content")
        markdown = session.to_markdown()

        assert "### 📌" in markdown

    def test_blockquote_format(self):
        """Test blockquote format for content."""
        session = CaptureSession(text="Quoted text")
        markdown = session.to_markdown()

        assert "> Quoted text" in markdown

    def test_citation_format_italics(self):
        """Test citation is formatted in italics."""
        session = CaptureSession(
            text="Content",
            citation=Citation(
                title="Book Title",
                source_type=SourceType.UNKNOWN,
            ),
        )
        markdown = session.to_markdown()

        assert "*Book Title*" in markdown

    def test_citation_with_page(self):
        """Test citation with page number."""
        session = CaptureSession(
            text="Content",
            citation=Citation(
                title="Book Title",
                page="42",
                source_type=SourceType.PDF,
            ),
        )
        markdown = session.to_markdown()

        assert "*Book Title, p. 42*" in markdown

    def test_citation_source_excluded_for_generic(self):
        """Test generic sources are excluded from citation."""
        session = CaptureSession(
            text="Content",
            citation=Citation(
                title="Page Title",
                source="Browser",
                source_type=SourceType.BROWSER,
            ),
        )
        markdown = session.to_markdown()

        # "Browser" should not appear as source
        assert "· Browser" not in markdown

    def test_multiline_text_in_blockquote(self):
        """Test multiline text is properly blockquoted."""
        session = CaptureSession(text="Line 1\nLine 2\nLine 3")
        markdown = session.to_markdown()

        assert "> Line 1" in markdown
        assert "> Line 2" in markdown
        assert "> Line 3" in markdown

    def test_text_and_ocr_separated(self):
        """Test text and OCR are properly separated."""
        session = CaptureSession(
            text="Selected text",
            ocr_text="OCR text",
        )
        markdown = session.to_markdown()

        assert "> Selected text" in markdown
        assert "> OCR text" in markdown
