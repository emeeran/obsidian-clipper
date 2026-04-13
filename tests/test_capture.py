"""Tests for capture modules."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from obsidian_clipper.capture import (
    Citation,
    ScreenshotCapture,
    SourceType,
    get_active_window_title,
    get_citation,
    get_selected_text,
    ocr_image,
    parse_browser_citation,
    parse_citation_from_window_title,
    parse_code_editor_citation,
    parse_epub_citation,
    parse_generic_citation,
    parse_pdf_citation,
    take_screenshot,
)
from obsidian_clipper.exceptions import ScreenshotError


class TestTextCapture:
    """Tests for text capture functions."""

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_selected_text_success(self, mock_run):
        """Test successful text capture."""
        mock_result = MagicMock()
        mock_result.stdout = "  selected text  "
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_selected_text()
        assert result == "selected text"

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_selected_text_empty(self, mock_run):
        """Test when no text is selected."""
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, "xclip")
        result = get_selected_text()
        assert result == ""

    @patch("obsidian_clipper.capture.text.subprocess.run")
    def test_get_active_window_title_success(self, mock_run):
        """Test getting window title."""
        mock_result = MagicMock()
        mock_result.stdout = "Document.pdf — Page 42"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = get_active_window_title()
        assert result == "Document.pdf — Page 42"


class TestCitationParsing:
    """Tests for citation parsing functions."""

    def test_parse_pdf_citation_evince(self):
        """Test parsing Evince PDF citation."""
        citation = parse_pdf_citation("Research Paper.pdf — Page 42")
        assert citation is not None
        assert citation.title == "Research Paper.pdf"
        assert citation.page == "42"
        assert citation.source == "Evince"
        assert citation.source_type == SourceType.PDF

    def test_parse_pdf_citation_zathura(self):
        """Test parsing Zathura PDF citation."""
        citation = parse_pdf_citation("Notes.pdf (15/200)")
        assert citation is not None
        assert citation.title == "Notes.pdf"
        assert citation.page == "15"
        assert citation.source == "Zathura"

    def test_parse_pdf_citation_okular(self):
        """Test parsing Okular PDF citation."""
        citation = parse_pdf_citation("Doc.pdf : Page 7 - Okular")
        assert citation is not None
        assert citation.title == "Doc.pdf"
        assert citation.page == "7"
        assert citation.source == "Okular"

    def test_parse_pdf_citation_okular_title_page(self):
        """Test parsing Okular citation with title + page pattern."""
        citation = parse_pdf_citation("CBT made simple — Page 44 — Okular")
        assert citation is not None
        assert citation.title == "CBT made simple"
        assert citation.page == "44"
        assert citation.source == "Okular"

    def test_parse_pdf_citation_okular_title_ratio_page(self):
        """Test Okular title with ratio page format."""
        citation = parse_pdf_citation("CBT made simple — 44/320 — Okular")
        assert citation is not None
        assert citation.title == "CBT made simple"
        assert citation.page == "44"
        assert citation.source == "Okular"

    def test_parse_pdf_citation_generic(self):
        """Test generic PDF citation requires page number."""
        citation = parse_pdf_citation("SomeFile.pdf - Text Editor")
        assert citation is None

    def test_parse_pdf_citation_generic_with_page(self):
        """Test parsing generic PDF citation when page is available."""
        citation = parse_pdf_citation("SomeFile.pdf - p. 12 - Text Editor")
        assert citation is not None
        assert citation.title == "SomeFile.pdf"
        assert citation.page == "12"
        assert citation.source == "PDF Reader"

    def test_parse_epub_citation_with_page(self):
        """Test EPUB citation parsing with required page."""
        citation = parse_epub_citation("Book Title.epub — Page 9 — Foliate")
        assert citation is not None
        assert citation.title == "Book Title.epub"
        assert citation.page == "9"
        assert citation.source == "Foliate"
        assert citation.source_type == SourceType.EPUB

    def test_parse_epub_citation_without_page(self):
        """Test EPUB citation without page is rejected."""
        citation = parse_epub_citation("Book Title.epub — Foliate")
        assert citation is None

    def test_parse_epub_citation_with_ratio_page(self):
        """Test EPUB citation parsing with ratio page format."""
        citation = parse_epub_citation("Book Title.epub — 9/300 — Foliate")
        assert citation is not None
        assert citation.title == "Book Title.epub"
        assert citation.page == "9"

    def test_parse_pdf_citation_no_match(self):
        """Test when window title doesn't match PDF pattern."""
        citation = parse_pdf_citation("Web Browser - Google Chrome")
        assert citation is None

    def test_parse_browser_citation_chrome(self):
        """Test parsing Chrome browser citation."""
        citation = parse_browser_citation("Article Title - Google Chrome")
        assert citation is not None
        assert citation.title == "Article Title"
        assert citation.source == "Google Chrome"
        assert citation.source_type == SourceType.BROWSER

    def test_parse_browser_citation_firefox(self):
        """Test parsing Firefox browser citation."""
        citation = parse_browser_citation("Documentation — Mozilla Firefox")
        assert citation is not None
        assert citation.title == "Documentation"
        assert citation.source == "Mozilla Firefox"

    def test_parse_browser_citation_brave(self):
        """Test parsing Brave browser citation."""
        citation = parse_browser_citation("News Site - Brave")
        assert citation is not None
        assert citation.title == "News Site"
        assert citation.source == "Brave"

    def test_parse_browser_citation_no_match(self):
        """Test when window title doesn't match browser pattern."""
        citation = parse_browser_citation("Document.pdf — Page 42")
        assert citation is None

    def test_parse_code_editor_citation_vscode(self):
        """Test parsing VSCode citation."""
        citation = parse_code_editor_citation(
            "main.py - myproject - Visual Studio Code"
        )
        assert citation is not None
        assert citation.title == "main.py"
        assert citation.source == "VSCode"
        assert citation.extra.get("project") == "myproject"

    def test_citation_format_markdown(self):
        """Test markdown formatting of citations."""
        citation = Citation(
            title="Document.pdf",
            page="42",
            source="Evince",
            source_type=SourceType.PDF,
        )
        expected = " — *Document.pdf, p. 42* · Evince"
        assert citation.format_markdown() == expected

    def test_citation_format_markdown_minimal(self):
        """Test markdown formatting with minimal info."""
        citation = Citation(
            title="Article",
            source_type=SourceType.BROWSER,
        )
        expected = " — *Article*"
        assert citation.format_markdown() == expected

    def test_citation_format_markdown_empty(self):
        """Test markdown formatting with no info."""
        citation = Citation(title="")
        assert citation.format_markdown() == ""

    @patch("obsidian_clipper.capture.citation.get_active_window_title")
    def test_get_citation_pdf(self, mock_title):
        """Test auto-detection returns PDF citation."""
        mock_title.return_value = "Paper.pdf — Page 10"
        citation = get_citation()
        assert citation is not None
        assert citation.source_type == SourceType.PDF

    @patch("obsidian_clipper.capture.citation.get_active_window_title")
    def test_get_citation_browser(self, mock_title):
        """Test auto-detection returns browser citation."""
        mock_title.return_value = "Webpage - Chrome"
        citation = get_citation()
        assert citation is not None
        assert citation.source_type == SourceType.BROWSER

    def test_parse_citation_from_window_title_pdf(self):
        """Test direct parsing from a provided window title."""
        citation = parse_citation_from_window_title("Paper.pdf — Page 10")
        assert citation is not None
        assert citation.title == "Paper.pdf"
        assert citation.page == "10"
        assert citation.source_type == SourceType.PDF

    def test_parse_citation_from_window_title_raw_fallback(self):
        """Test raw-title fallback for unknown title formats."""
        citation = parse_citation_from_window_title("My Untitled Research Window")
        assert citation is not None
        assert citation.title == "My Untitled Research Window"
        assert citation.source_type == SourceType.UNKNOWN

    def test_parse_citation_from_window_title_pdf_context_without_page(self):
        """Test PDF contexts without page do not use raw fallback."""
        citation = parse_citation_from_window_title("Book.pdf — Okular")
        assert citation is None

    def test_parse_generic_citation_fallback(self):
        """Test generic fallback parsing for non-standard titles."""
        citation = parse_generic_citation("Interesting Article — Zen Browser")
        assert citation is not None
        assert citation.title == "Interesting Article"
        assert citation.source == "Zen Browser"
        assert citation.source_type == SourceType.UNKNOWN

    def test_parse_generic_citation_skips_pdf_reader_titles(self):
        """Test generic fallback does not bypass mandatory page rules."""
        citation = parse_generic_citation("Book Title — Okular")
        assert citation is None

    @patch("obsidian_clipper.utils.retry.time.sleep")
    @patch("obsidian_clipper.capture.citation.get_active_window_title")
    def test_get_citation_skips_transient_titles(self, mock_title, mock_sleep):
        """Test citation detection retries through transient tool window titles."""
        mock_title.side_effect = [
            "Flameshot",
            "GNOME Shell",
            "Paper.pdf — Page 10",
        ]

        citation = get_citation()

        assert citation is not None
        assert citation.title == "Paper.pdf"
        assert citation.page == "10"
        assert citation.source_type == SourceType.PDF


class TestScreenshot:
    """Tests for screenshot functions."""

    @patch("obsidian_clipper.capture.screenshot.os.path.getsize")
    @patch("obsidian_clipper.capture.screenshot.os.path.exists")
    @patch("obsidian_clipper.capture.screenshot.Path.exists")
    @patch("obsidian_clipper.capture.screenshot.run_command_safely")
    @patch("obsidian_clipper.capture.screenshot.subprocess.run")
    def test_take_screenshot_flameshot_failure(
        self,
        mock_subprocess,
        mock_run,
        mock_path_exists,
        mock_os_exists,
        mock_os_getsize,
    ):
        """Test flameshot failure raises error."""
        # Make all subprocess calls fail with realistic exception types
        # that the code actually catches (subprocess.SubprocessError, OSError, CommandError)
        from obsidian_clipper.utils.command import CommandError

        mock_subprocess.side_effect = subprocess.SubprocessError("Subprocess failed")
        mock_run.side_effect = CommandError("Command failed")
        mock_os_exists.return_value = False
        mock_os_getsize.return_value = 0

        with pytest.raises(ScreenshotError):
            take_screenshot("/tmp/test.png", tool="flameshot")

    @patch("obsidian_clipper.capture.screenshot.Path.exists")
    @patch("obsidian_clipper.capture.screenshot.run_command_safely")
    def test_ocr_image_success(self, mock_run, mock_exists):
        """Test successful OCR."""
        mock_exists.return_value = True
        mock_result = MagicMock()
        mock_result.stdout = "Extracted text"
        mock_run.return_value = mock_result

        result = ocr_image("/tmp/test.png")
        assert result == "Extracted text"

    def test_ocr_image_file_not_found(self, tmp_path):
        """Test OCR with missing file returns empty string."""
        result = ocr_image(tmp_path / "nonexistent.png")
        assert result == ""  # Returns empty string, not exception


class TestScreenshotCapture:
    """Tests for ScreenshotCapture class."""

    @patch("obsidian_clipper.capture.screenshot.take_screenshot")
    @patch("obsidian_clipper.capture.screenshot.ocr_image")
    def test_capture_success(self, mock_ocr, mock_take):
        """Test successful capture with OCR."""
        mock_take.return_value = True
        mock_ocr.return_value = "OCR text"

        capture = ScreenshotCapture(perform_ocr=True)
        path, ocr_text = capture.capture()

        assert path is not None
        assert ocr_text == "OCR text"

    @patch("obsidian_clipper.capture.screenshot.take_screenshot")
    def test_capture_failure(self, mock_take):
        """Test capture failure."""
        mock_take.side_effect = ScreenshotError("Failed")

        capture = ScreenshotCapture()
        path, ocr_text = capture.capture()

        assert path is None
        assert ocr_text == ""
