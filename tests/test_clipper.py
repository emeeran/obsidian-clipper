"""Tests for main clipper CLI module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from obsidian_clipper.capture import Citation, SourceType
from obsidian_clipper.cli.main import main, validate_config
from obsidian_clipper.cli.args import parse_args
from obsidian_clipper.exceptions import ConfigurationError
from obsidian_clipper.workflow import CaptureSession, prepare_capture_session


class TestCaptureSession:
    """Tests for CaptureSession dataclass."""

    def test_has_content_with_text(self):
        """Test has_content returns True when text exists."""
        session = CaptureSession(text="Some text")
        assert session.has_content() is True

    def test_has_content_with_screenshot(self):
        """Test has_content returns True when screenshot uploaded."""
        session = CaptureSession(screenshot_success=True)
        assert session.has_content() is True

    def test_has_content_with_screenshot_path(self):
        """Test has_content returns True when screenshot is captured pre-upload."""
        session = CaptureSession(screenshot_path=Path("/tmp/capture.png"))
        assert session.has_content() is True

    def test_has_content_with_ocr(self):
        """Test has_content returns True when OCR text exists."""
        session = CaptureSession(ocr_text="OCR text")
        assert session.has_content() is True

    def test_has_content_empty(self):
        """Test has_content returns False when empty."""
        session = CaptureSession()
        assert session.has_content() is False

    def test_to_markdown_basic(self):
        """Test basic markdown generation."""
        session = CaptureSession(
            timestamp="2024-01-15 10:30:00",
            text="Selected text",
        )

        md = session.to_markdown()

        assert "2024-01-15 10:30:00" in md
        assert "> Selected text" in md

    def test_to_markdown_with_citation(self):
        """Test markdown with citation."""
        session = CaptureSession(
            text="Quote",
            citation=Citation(
                title="Book.pdf",
                page="42",
                source="Evince",
                source_type=SourceType.PDF,
            ),
        )

        md = session.to_markdown()

        assert "> Quote" in md
        assert "Book.pdf" in md
        assert "p. 42" in md
        assert "Evince" in md

    def test_to_markdown_with_screenshot(self):
        """Test markdown with screenshot."""
        session = CaptureSession(
            screenshot_success=True,
            img_filename="capture_20240115.png",
        )

        md = session.to_markdown()

        assert "![[capture_20240115.png]]" in md

    def test_to_markdown_with_ocr(self):
        """Test markdown with OCR text."""
        session = CaptureSession(
            ocr_text="Extracted content",
        )

        md = session.to_markdown()

        # OCR text is now in blockquote format
        assert "> Extracted content" in md

    def test_get_preview_text(self):
        """Test preview from text."""
        session = CaptureSession(text="This is a long text that should be truncated")
        preview = session.get_preview(max_length=20)
        assert len(preview) == 23  # 20 + "..."
        assert preview.endswith("...")

    def test_get_preview_short_text(self):
        """Test preview with short text."""
        session = CaptureSession(text="Short")
        preview = session.get_preview()
        assert preview == "Short"

    def test_get_preview_ocr(self):
        """Test preview from OCR when no text."""
        session = CaptureSession(ocr_text="OCR content")
        preview = session.get_preview()
        assert preview == "OCR content"

    def test_get_preview_screenshot(self):
        """Test preview defaults to Screenshot."""
        session = CaptureSession()
        preview = session.get_preview()
        assert preview == "Screenshot"


class TestParseArgs:
    """Tests for argument parsing."""

    def test_default_args(self):
        """Test default argument values."""
        with patch("sys.argv", ["clipper"]):
            args = parse_args()
            assert args.screenshot is False
            assert args.ocr is True
            assert args.no_ocr is False
            assert args.note is None
            assert args.screenshot_tool == "auto"

    def test_screenshot_flag(self):
        """Test -s flag."""
        with patch("sys.argv", ["clipper", "-s"]):
            args = parse_args()
            assert args.screenshot is True

    def test_note_option(self):
        """Test -n option."""
        with patch("sys.argv", ["clipper", "-n", "Custom/Note.md"]):
            args = parse_args()
            assert args.note == "Custom/Note.md"

    def test_ocr_lang_option(self):
        """Test --ocr-lang option."""
        with patch("sys.argv", ["clipper", "--ocr-lang", "deu"]):
            args = parse_args()
            assert args.ocr_lang == "deu"

    def test_no_ocr_flag(self):
        """Test --no-ocr flag."""
        with patch("sys.argv", ["clipper", "-s", "--no-ocr"]):
            args = parse_args()
            assert args.no_ocr is True

    def test_verbose_flag(self):
        """Test -v flag."""
        with patch("sys.argv", ["clipper", "-v"]):
            args = parse_args()
            assert args.verbose is True

    def test_debug_flag(self):
        """Test --debug flag."""
        with patch("sys.argv", ["clipper", "--debug"]):
            args = parse_args()
            assert args.debug is True


class TestValidateConfig:
    """Tests for configuration validation."""

    @patch("obsidian_clipper.cli.main.get_config")
    def test_valid_config(self, mock_get_config):
        """Test validation passes with valid config."""
        mock_config = MagicMock()
        mock_config.validate.return_value = []
        mock_get_config.return_value = mock_config

        # Should not raise
        validate_config()

    @patch("obsidian_clipper.cli.main.get_config")
    def test_invalid_config(self, mock_get_config):
        """Test validation fails with invalid config."""
        mock_config = MagicMock()
        mock_config.validate.return_value = ["API key is required"]
        mock_get_config.return_value = mock_config

        with pytest.raises(ConfigurationError):
            validate_config()


class TestPrepareCaptureSession:
    """Tests for capture session preparation."""

    @patch("obsidian_clipper.workflow.capture.ScreenshotCapture")
    @patch("obsidian_clipper.workflow.capture.parse_citation_from_window_title")
    @patch("obsidian_clipper.workflow.capture.get_active_window_title")
    @patch("obsidian_clipper.workflow.capture.get_citation")
    def test_screenshot_mode_retries_citation_after_capture(
        self,
        mock_get_citation,
        mock_get_active_window_title,
        mock_parse_from_title,
        mock_capture_class,
    ):
        """Test screenshot mode retries citation when initial detection misses."""
        args = MagicMock()
        args.screenshot = True
        args.ocr = True
        args.no_ocr = False
        args.screenshot_tool = "auto"
        args.ocr_lang = None

        mock_get_active_window_title.return_value = "Transient overlay title"
        mock_parse_from_title.return_value = None
        mock_get_citation.return_value = Citation(
            title="Doc.pdf",
            page="12",
            source="Okular",
            source_type=SourceType.PDF,
        )

        mock_capture = MagicMock()
        mock_capture.capture.return_value = (Path("/tmp/capture.png"), "OCR text")
        mock_capture_class.return_value = mock_capture

        session = prepare_capture_session(args)

        assert session.citation is not None
        assert session.citation.page == "12"
        assert mock_get_citation.call_count == 1

    @patch("obsidian_clipper.workflow.capture.ScreenshotCapture")
    @patch("obsidian_clipper.workflow.capture.parse_citation_from_window_title")
    @patch("obsidian_clipper.workflow.capture.get_active_window_title")
    @patch("obsidian_clipper.workflow.capture.get_citation")
    def test_screenshot_mode_uses_pre_capture_window_title(
        self,
        mock_get_citation,
        mock_get_active_window_title,
        mock_parse_from_title,
        mock_capture_class,
    ):
        """Test screenshot mode captures citation from active window before flameshot."""
        args = MagicMock()
        args.screenshot = True
        args.ocr = True
        args.no_ocr = False
        args.screenshot_tool = "auto"
        args.ocr_lang = None

        mock_get_active_window_title.return_value = "CBT made simple — Page 44 — Okular"
        mock_parse_from_title.return_value = Citation(
            title="CBT made simple",
            page="44",
            source="Okular",
            source_type=SourceType.PDF,
        )

        mock_capture = MagicMock()
        mock_capture.capture.return_value = (Path("/tmp/capture.png"), "OCR text")
        mock_capture_class.return_value = mock_capture

        session = prepare_capture_session(args)

        assert session.citation is not None
        assert session.citation.page == "44"
        mock_get_citation.assert_not_called()

    @patch("obsidian_clipper.workflow.capture.ScreenshotCapture")
    @patch("obsidian_clipper.workflow.capture.parse_citation_from_window_title")
    @patch("obsidian_clipper.workflow.capture.get_active_window_title")
    @patch("obsidian_clipper.workflow.capture.get_citation")
    def test_screenshot_mode_uses_fallback_window_citation_when_none(
        self,
        mock_get_citation,
        mock_get_active_window_title,
        mock_parse_from_title,
        mock_capture_class,
    ):
        """Test screenshot mode creates unknown citation from window title fallback."""
        args = MagicMock()
        args.screenshot = True
        args.ocr = True
        args.no_ocr = False
        args.screenshot_tool = "auto"
        args.ocr_lang = None

        mock_get_active_window_title.side_effect = [
            "Interesting Article - Zen Browser",
            "Interesting Article - Zen Browser",
        ]
        mock_parse_from_title.return_value = None
        mock_get_citation.return_value = None

        mock_capture = MagicMock()
        mock_capture.capture.return_value = (Path("/tmp/capture.png"), "OCR text")
        mock_capture_class.return_value = mock_capture

        session = prepare_capture_session(args)

        assert session.citation is not None
        assert session.citation.title == "Interesting Article - Zen Browser"
        assert session.citation.source == "Window"
        assert session.citation.source_type == SourceType.UNKNOWN


class TestMain:
    """Tests for main function."""

    @patch("obsidian_clipper.cli.main.validate_config")
    @patch("obsidian_clipper.cli.main.ObsidianClient")
    @patch("obsidian_clipper.cli.main.get_config")
    @patch("obsidian_clipper.workflow.capture.get_selected_text")
    @patch("obsidian_clipper.cli.main.notify_success")
    def test_main_text_capture_success(
        self,
        mock_notify,
        mock_get_text,
        mock_get_config,
        mock_client_class,
        mock_validate,
    ):
        """Test successful text capture."""
        mock_get_text.return_value = "Test text"
        mock_config = MagicMock()
        mock_config.default_note = "Notes.md"
        mock_get_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client.check_connection.return_value = True
        mock_client.ensure_note_exists.return_value = True
        mock_client.append_to_note.return_value = True
        mock_client_class.return_value.__enter__.return_value = mock_client

        with patch("sys.argv", ["clipper"]):
            result = main()

        assert result == 0
        mock_notify.assert_called()

    @patch("obsidian_clipper.cli.main.validate_config")
    @patch("obsidian_clipper.cli.main.ObsidianClient")
    @patch("obsidian_clipper.cli.main.get_config")
    @patch("obsidian_clipper.cli.main.notify_error")
    def test_main_connection_failure(
        self,
        mock_notify_error,
        mock_get_config,
        mock_client_class,
        mock_validate,
    ):
        """Test connection failure handling."""
        mock_client = MagicMock()
        mock_client.check_connection.return_value = False
        mock_client_class.return_value.__enter__.return_value = mock_client

        with patch("sys.argv", ["clipper"]):
            result = main()

        assert result == 1
        mock_notify_error.assert_called()

    @patch("obsidian_clipper.cli.main.validate_config")
    @patch("obsidian_clipper.cli.main.ObsidianClient")
    @patch("obsidian_clipper.cli.main.get_config")
    @patch("obsidian_clipper.workflow.capture.get_selected_text")
    @patch("obsidian_clipper.cli.main.notify_error")
    def test_main_no_text(
        self,
        mock_notify_error,
        mock_get_text,
        mock_get_config,
        mock_client_class,
        mock_validate,
    ):
        """Test handling when no text selected."""
        mock_get_text.return_value = ""
        mock_client = MagicMock()
        mock_client.check_connection.return_value = True
        mock_client_class.return_value.__enter__.return_value = mock_client

        with patch("sys.argv", ["clipper"]):
            result = main()

        assert result == 1
        mock_notify_error.assert_called()

    @patch("obsidian_clipper.cli.main.validate_config")
    @patch("obsidian_clipper.cli.main.notify_error")
    def test_main_config_error(self, mock_notify_error, mock_validate):
        """Test configuration error handling."""
        mock_validate.side_effect = ConfigurationError("Invalid config")

        with patch("sys.argv", ["clipper"]):
            result = main()

        assert result == 1
        mock_notify_error.assert_called()

    @patch("obsidian_clipper.cli.main.validate_config")
    @patch("obsidian_clipper.cli.main.ObsidianClient")
    @patch("obsidian_clipper.cli.main.get_config")
    @patch("obsidian_clipper.cli.main.prepare_capture_session")
    @patch("obsidian_clipper.cli.main.notify_error")
    def test_main_pdf_citation_without_page_fails(
        self,
        mock_notify_error,
        mock_prepare,
        mock_get_config,
        mock_client_class,
        mock_validate,
    ):
        """Test capture fails when PDF citation has no page number."""
        mock_config = MagicMock()
        mock_config.default_note = "Notes.md"
        mock_get_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client.check_connection.return_value = True
        mock_client.ensure_note_exists.return_value = True
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_prepare.return_value = CaptureSession(
            text="Some selected text",
            citation=Citation(
                title="Book.pdf",
                page=None,
                source="Okular",
                source_type=SourceType.PDF,
            ),
        )

        with patch("sys.argv", ["clipper"]):
            result = main()

        assert result == 1
        mock_notify_error.assert_called()

    @patch("obsidian_clipper.cli.main.validate_config")
    @patch("obsidian_clipper.cli.main.ObsidianClient")
    @patch("obsidian_clipper.cli.main.get_config")
    @patch("obsidian_clipper.cli.main.prepare_capture_session")
    @patch("obsidian_clipper.cli.main.notify_error")
    def test_main_screenshot_ocr_empty_fails(
        self,
        mock_notify_error,
        mock_prepare,
        mock_get_config,
        mock_client_class,
        mock_validate,
    ):
        """Test screenshot mode fails when OCR is enabled but produces no text."""
        mock_config = MagicMock()
        mock_config.default_note = "Notes.md"
        mock_get_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client.check_connection.return_value = True
        mock_client.ensure_note_exists.return_value = True
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_prepare.return_value = CaptureSession(
            screenshot_path=Path("/tmp/capture.png"),
            ocr_text="",
        )

        with patch("sys.argv", ["clipper", "-s"]):
            result = main()

        assert result == 1
        mock_notify_error.assert_called()
