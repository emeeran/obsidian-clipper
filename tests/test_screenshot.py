"""Tests for screenshot capture utilities."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from obsidian_clipper.capture.screenshot import (
    ScreenshotCapture,
    _capture_with_flameshot,
    _capture_with_grim,
    create_temp_screenshot,
    ocr_image,
    take_screenshot,
)
from obsidian_clipper.exceptions import OCRError, ScreenshotError


class TestTakeScreenshot:
    """Tests for take_screenshot function."""

    @patch("obsidian_clipper.capture.screenshot._capture_with_flameshot")
    def test_take_screenshot_auto_uses_flameshot_first(self, mock_flameshot):
        """Test auto mode tries flameshot first."""
        mock_flameshot.return_value = True

        result = take_screenshot("/tmp/test.png", tool="auto")

        assert result is True
        mock_flameshot.assert_called_once_with("/tmp/test.png")

    @patch("obsidian_clipper.capture.screenshot._capture_with_grim")
    @patch("obsidian_clipper.capture.screenshot._capture_with_flameshot")
    def test_take_screenshot_auto_falls_back_to_grim(self, mock_flameshot, mock_grim):
        """Test auto mode falls back to grim if flameshot fails."""
        mock_flameshot.return_value = False
        mock_grim.return_value = True

        result = take_screenshot("/tmp/test.png", tool="auto")

        assert result is True
        mock_flameshot.assert_called_once()
        mock_grim.assert_called_once()

    @patch("obsidian_clipper.capture.screenshot._capture_with_grim")
    @patch("obsidian_clipper.capture.screenshot._capture_with_flameshot")
    def test_take_screenshot_auto_all_fail_raises_error(
        self, mock_flameshot, mock_grim
    ):
        """Test auto mode raises error when all tools fail."""
        mock_flameshot.return_value = False
        mock_grim.return_value = False

        with pytest.raises(ScreenshotError, match="No compatible screenshot tool"):
            take_screenshot("/tmp/test.png", tool="auto")

    @patch("obsidian_clipper.capture.screenshot._capture_with_flameshot")
    def test_take_screenshot_flameshot_mode(self, mock_flameshot):
        """Test explicit flameshot mode."""
        mock_flameshot.return_value = True

        result = take_screenshot("/tmp/test.png", tool="flameshot")

        assert result is True

    @patch("obsidian_clipper.capture.screenshot._capture_with_flameshot")
    def test_take_screenshot_flameshot_fails_raises_error(self, mock_flameshot):
        """Test flameshot failure raises appropriate error."""
        mock_flameshot.return_value = False

        with pytest.raises(ScreenshotError, match="Flameshot capture failed"):
            take_screenshot("/tmp/test.png", tool="flameshot")

    @patch("obsidian_clipper.capture.screenshot._capture_with_grim")
    def test_take_screenshot_grim_mode(self, mock_grim):
        """Test explicit grim mode."""
        mock_grim.return_value = True

        result = take_screenshot("/tmp/test.png", tool="grim")

        assert result is True

    @patch("obsidian_clipper.capture.screenshot._capture_with_grim")
    def test_take_screenshot_grim_fails_raises_error(self, mock_grim):
        """Test grim failure raises appropriate error."""
        mock_grim.return_value = False

        with pytest.raises(ScreenshotError, match="grim/slurp capture failed"):
            take_screenshot("/tmp/test.png", tool="grim")

    def test_take_screenshot_unknown_tool_raises_error(self):
        """Test unknown tool raises error."""
        with pytest.raises(ScreenshotError, match="Unknown screenshot tool"):
            take_screenshot("/tmp/test.png", tool="unknown")


class TestCaptureWithFlameshot:
    """Tests for _capture_with_flameshot function."""

    @patch("obsidian_clipper.capture.screenshot._save_clipboard_image")
    @patch("obsidian_clipper.capture.screenshot.run_command_safely")
    @patch("obsidian_clipper.capture.screenshot.os.path.getsize")
    @patch("obsidian_clipper.capture.screenshot.os.path.exists")
    @patch("obsidian_clipper.capture.screenshot._capture_with_flameshot_raw")
    def test_flameshot_uses_raw_capture_first(
        self, mock_raw, mock_exists, mock_size, mock_run, mock_clipboard
    ):
        """Test flameshot tries raw capture first."""
        mock_raw.return_value = True

        result = _capture_with_flameshot("/tmp/test.png")

        assert result is True
        mock_raw.assert_called_once_with("/tmp/test.png")


class TestCaptureWithGrim:
    """Tests for _capture_with_grim function."""

    @patch("obsidian_clipper.capture.screenshot.subprocess.run")
    @patch("obsidian_clipper.capture.screenshot.os.path.exists")
    def test_grim_success(self, mock_exists, mock_run):
        """Test successful grim capture."""
        mock_slurp = MagicMock()
        mock_slurp.returncode = 0
        mock_slurp.stdout = "100,100 200x200"

        mock_grim = MagicMock()
        mock_grim.returncode = 0

        mock_run.side_effect = [mock_slurp, mock_grim]
        mock_exists.return_value = True

        result = _capture_with_grim("/tmp/test.png")

        assert result is True

    @patch("obsidian_clipper.capture.screenshot.subprocess.run")
    def test_grim_slurp_cancelled(self, mock_run):
        """Test grim when user cancels slurp selection."""
        mock_slurp = MagicMock()
        mock_slurp.returncode = 1
        mock_slurp.stdout = ""
        mock_run.return_value = mock_slurp

        result = _capture_with_grim("/tmp/test.png")

        assert result is False


class TestOcrImage:
    """Tests for ocr_image function."""

    @patch("obsidian_clipper.capture.screenshot.get_config")
    @patch("obsidian_clipper.capture.screenshot.run_command_safely")
    def test_ocr_image_success(self, mock_run, mock_get_config, tmp_path):
        """Test successful OCR."""
        # Create a dummy image file
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        mock_config = MagicMock()
        mock_config.ocr_language = "eng"
        mock_get_config.return_value = mock_config

        mock_result = MagicMock()
        mock_result.stdout = "Extracted text from image"
        mock_run.return_value = mock_result

        result = ocr_image(img_file)

        assert result == "Extracted text from image"

    @patch("obsidian_clipper.capture.screenshot.get_config")
    @patch("obsidian_clipper.capture.screenshot.run_command_safely")
    def test_ocr_image_with_custom_language(self, mock_run, mock_get_config, tmp_path):
        """Test OCR with custom language."""
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        mock_config = MagicMock()
        mock_config.ocr_language = "eng"
        mock_get_config.return_value = mock_config

        mock_result = MagicMock()
        mock_result.stdout = "Texte extrait"
        mock_run.return_value = mock_result

        result = ocr_image(img_file, language="fra")

        assert result == "Texte extrait"

    def test_ocr_image_file_not_found(self, tmp_path):
        """Test OCR with non-existent file returns empty string."""
        result = ocr_image(tmp_path / "nonexistent.png")

        assert result == ""

    @patch("obsidian_clipper.capture.screenshot.get_config")
    @patch("obsidian_clipper.capture.screenshot.run_command_safely")
    def test_ocr_image_failure_raises_error(self, mock_run, mock_get_config, tmp_path):
        """Test OCR failure raises OCRError."""
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        mock_config = MagicMock()
        mock_config.ocr_language = "eng"
        mock_get_config.return_value = mock_config

        mock_run.side_effect = Exception("OCR failed")

        with pytest.raises(OCRError, match="OCR processing failed"):
            ocr_image(img_file)


class TestScreenshotCapture:
    """Tests for ScreenshotCapture class."""

    @patch("obsidian_clipper.capture.screenshot.take_screenshot")
    @patch("obsidian_clipper.capture.screenshot.ocr_image")
    def test_capture_success_with_ocr(self, mock_ocr, mock_take):
        """Test successful capture with OCR."""
        mock_take.return_value = True
        mock_ocr.return_value = "OCR text"

        capture = ScreenshotCapture(perform_ocr=True)
        path, ocr_text = capture.capture()

        assert path is not None
        assert ocr_text == "OCR text"
        mock_ocr.assert_called_once()

    @patch("obsidian_clipper.capture.screenshot.take_screenshot")
    @patch("obsidian_clipper.capture.screenshot.ocr_image")
    def test_capture_success_without_ocr(self, mock_ocr, mock_take):
        """Test capture without OCR."""
        mock_take.return_value = True

        capture = ScreenshotCapture(perform_ocr=False)
        path, ocr_text = capture.capture()

        assert path is not None
        assert ocr_text == ""
        mock_ocr.assert_not_called()

    @patch("obsidian_clipper.capture.screenshot.take_screenshot")
    def test_capture_failure_returns_none(self, mock_take):
        """Test capture failure returns None."""
        mock_take.side_effect = ScreenshotError("Failed")

        capture = ScreenshotCapture()
        path, ocr_text = capture.capture()

        assert path is None
        assert ocr_text == ""

    @patch("obsidian_clipper.capture.screenshot.os.path.exists")
    def test_cleanup_removes_file(self, mock_exists, tmp_path):
        """Test cleanup removes temporary file."""
        temp_file = tmp_path / "test.png"
        temp_file.write_bytes(b"test")

        capture = ScreenshotCapture()
        capture._temp_file = temp_file
        mock_exists.return_value = True

        with patch.object(Path, "unlink") as mock_unlink:
            capture.cleanup()
            mock_unlink.assert_called_once()


class TestCreateTempScreenshot:
    """Tests for create_temp_screenshot function."""

    def test_creates_path_in_temp_dir(self):
        """Test that path is in temp directory."""
        path = create_temp_screenshot()

        assert "tmp" in str(path) or "TMP" in str(path).upper()

    def test_uses_custom_prefix(self):
        """Test custom prefix in filename."""
        path = create_temp_screenshot(prefix="custom_prefix")

        assert "custom_prefix" in path.name

    def test_filename_has_png_extension(self):
        """Test filename has .png extension."""
        path = create_temp_screenshot()

        assert path.suffix == ".png"
