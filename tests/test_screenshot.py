"""Tests for screenshot capture utilities."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from obsidian_clipper.capture.screenshot import (
    ScreenshotCapture,
    _capture_with_flameshot,
    _capture_with_flameshot_raw,
    _capture_with_grim,
    _save_clipboard_image,
    _wait_for_file,
    create_temp_screenshot,
    ocr_image,
    take_screenshot,
)
from obsidian_clipper.exceptions import OCRError, ScreenshotError
from obsidian_clipper.utils.command import CommandError


class TestWaitForFile:
    """Tests for _wait_for_file function."""

    def test_wait_for_file_exists_immediately(self, tmp_path):
        """Test returns True when file exists immediately."""
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        result = _wait_for_file(test_file, timeout=1.0)

        assert result is True

    def test_wait_for_file_not_exists(self, tmp_path):
        """Test returns False when file doesn't exist."""
        test_file = tmp_path / "nonexistent.png"

        result = _wait_for_file(test_file, timeout=0.1)

        assert result is False

    def test_wait_for_file_empty_file(self, tmp_path):
        """Test returns False for empty file."""
        test_file = tmp_path / "empty.png"
        test_file.write_bytes(b"")

        result = _wait_for_file(test_file, timeout=0.1)

        assert result is False

    def test_wait_for_file_appears_later(self, tmp_path):
        """Test waits for file to appear."""
        import threading
        import time

        test_file = tmp_path / "delayed.png"

        def create_file_later():
            time.sleep(0.1)
            test_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        thread = threading.Thread(target=create_file_later)
        thread.start()

        result = _wait_for_file(test_file, timeout=1.0)
        thread.join()

        assert result is True

    def test_wait_for_file_with_string_path(self, tmp_path):
        """Test works with string path."""
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        result = _wait_for_file(str(test_file), timeout=1.0)

        assert result is True


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

    @patch("obsidian_clipper.capture.screenshot._wait_for_file")
    @patch("obsidian_clipper.capture.screenshot.run_command_safely")
    @patch("obsidian_clipper.capture.screenshot._capture_with_flameshot_raw")
    def test_flameshot_gui_mode_success(self, mock_raw, mock_run, mock_wait):
        """Test flameshot GUI mode when raw capture fails."""
        mock_raw.return_value = False
        mock_wait.return_value = True

        result = _capture_with_flameshot("/tmp/test.png")

        assert result is True
        mock_run.assert_called_once()

    @patch("obsidian_clipper.capture.screenshot.run_command_safely")
    @patch("obsidian_clipper.capture.screenshot._capture_with_flameshot_raw")
    def test_flameshot_fallback_on_accept_on_select_error(self, mock_raw, mock_run):
        """Test flameshot falls back when --accept-on-select fails."""
        mock_raw.return_value = False
        # First call fails, second call succeeds
        mock_run.side_effect = [CommandError("failed"), None]

        _capture_with_flameshot("/tmp/test.png")

        assert mock_run.call_count == 2

    @patch("obsidian_clipper.capture.screenshot._save_clipboard_image")
    @patch("obsidian_clipper.capture.screenshot._wait_for_file")
    @patch("obsidian_clipper.capture.screenshot.run_command_safely")
    @patch("obsidian_clipper.capture.screenshot._capture_with_flameshot_raw")
    def test_flameshot_uses_clipboard_fallback(
        self, mock_raw, mock_run, mock_wait, mock_clipboard
    ):
        """Test flameshot uses clipboard fallback when file not created."""
        mock_raw.return_value = False
        mock_wait.return_value = False
        mock_clipboard.return_value = True

        result = _capture_with_flameshot("/tmp/test.png")

        assert result is True
        mock_clipboard.assert_called_once_with("/tmp/test.png")

    @patch("obsidian_clipper.capture.screenshot.run_command_safely")
    @patch("obsidian_clipper.capture.screenshot._capture_with_flameshot_raw")
    def test_flameshot_all_methods_fail(self, mock_raw, mock_run):
        """Test flameshot returns False when all methods fail."""
        mock_raw.return_value = False
        mock_run.side_effect = CommandError("failed")

        result = _capture_with_flameshot("/tmp/test.png")

        assert result is False


class TestCaptureWithFlameshotRaw:
    """Tests for _capture_with_flameshot_raw function."""

    @patch("obsidian_clipper.capture.screenshot.os.path.getsize")
    @patch("obsidian_clipper.capture.screenshot.os.path.exists")
    @patch("obsidian_clipper.capture.screenshot.subprocess.run")
    def test_raw_capture_success(self, mock_run, mock_exists, mock_getsize, tmp_path):
        """Test successful raw capture."""
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = png_data
        mock_run.return_value = mock_result
        mock_exists.return_value = True
        mock_getsize.return_value = len(png_data)

        output_file = tmp_path / "test.png"
        result = _capture_with_flameshot_raw(str(output_file))

        assert result is True

    @patch("obsidian_clipper.capture.screenshot.subprocess.run")
    def test_raw_capture_nonzero_returncode(self, mock_run):
        """Test raw capture with non-zero return code."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = b""
        mock_run.return_value = mock_result

        result = _capture_with_flameshot_raw("/tmp/test.png")

        assert result is False

    @patch("obsidian_clipper.capture.screenshot.subprocess.run")
    def test_raw_capture_empty_stdout(self, mock_run):
        """Test raw capture with empty stdout."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b""
        mock_run.return_value = mock_result

        result = _capture_with_flameshot_raw("/tmp/test.png")

        assert result is False

    @patch("obsidian_clipper.capture.screenshot.subprocess.run")
    def test_raw_capture_invalid_png_header(self, mock_run):
        """Test raw capture rejects non-PNG data."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b"NOT A PNG FILE"
        mock_run.return_value = mock_result

        result = _capture_with_flameshot_raw("/tmp/test.png")

        assert result is False

    @patch("obsidian_clipper.capture.screenshot.subprocess.run")
    def test_raw_capture_timeout(self, mock_run):
        """Test raw capture handles timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("flameshot", 60)

        result = _capture_with_flameshot_raw("/tmp/test.png")

        assert result is False

    @patch("obsidian_clipper.capture.screenshot.subprocess.run")
    def test_raw_capture_os_error(self, mock_run):
        """Test raw capture handles OS errors."""
        mock_run.side_effect = OSError("Command not found")

        result = _capture_with_flameshot_raw("/tmp/test.png")

        assert result is False


class TestSaveClipboardImage:
    """Tests for _save_clipboard_image function."""

    @patch("obsidian_clipper.capture.screenshot.os.path.getsize")
    @patch("obsidian_clipper.capture.screenshot.os.path.exists")
    @patch("obsidian_clipper.capture.screenshot.subprocess.run")
    def test_save_clipboard_success(self, mock_run, mock_exists, mock_getsize):
        """Test successful clipboard save."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        mock_exists.return_value = True
        mock_getsize.return_value = 100

        result = _save_clipboard_image("/tmp/test.png")

        assert result is True

    @patch("obsidian_clipper.capture.screenshot.subprocess.run")
    def test_save_clipboard_nonzero_returncode(self, mock_run):
        """Test clipboard save with non-zero return code."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        with patch(
            "obsidian_clipper.capture.screenshot.os.path.exists", return_value=False
        ):
            result = _save_clipboard_image("/tmp/test.png")

        assert result is False

    @patch("obsidian_clipper.capture.screenshot.subprocess.run")
    def test_save_clipboard_timeout(self, mock_run):
        """Test clipboard save handles timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("xclip", 5)

        result = _save_clipboard_image("/tmp/test.png")

        assert result is False

    @patch("obsidian_clipper.capture.screenshot.subprocess.run")
    def test_save_clipboard_os_error(self, mock_run):
        """Test clipboard save handles OS errors."""
        mock_run.side_effect = OSError("Command not found")

        result = _save_clipboard_image("/tmp/test.png")

        assert result is False


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

    @patch("obsidian_clipper.capture.screenshot.subprocess.run")
    def test_grim_timeout(self, mock_run):
        """Test grim handles timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("slurp", 60)

        result = _capture_with_grim("/tmp/test.png")

        assert result is False

    @patch("obsidian_clipper.capture.screenshot.subprocess.run")
    def test_grim_file_not_found(self, mock_run):
        """Test grim handles command not found."""
        mock_run.side_effect = FileNotFoundError("slurp not found")

        result = _capture_with_grim("/tmp/test.png")

        assert result is False

    @patch("obsidian_clipper.capture.screenshot.subprocess.run")
    @patch("obsidian_clipper.capture.screenshot.os.path.exists")
    def test_grim_fails_nonzero_returncode(self, mock_exists, mock_run):
        """Test grim returns False on non-zero grim returncode."""
        mock_slurp = MagicMock()
        mock_slurp.returncode = 0
        mock_slurp.stdout = "100,100 200x200"

        mock_grim = MagicMock()
        mock_grim.returncode = 1

        mock_run.side_effect = [mock_slurp, mock_grim]
        mock_exists.return_value = False

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

    @patch("obsidian_clipper.capture.screenshot.get_config")
    @patch("obsidian_clipper.capture.screenshot.run_command_safely")
    def test_ocr_image_with_tessconfig(self, mock_run, mock_get_config, tmp_path):
        """Test OCR with tessconfig parameter."""
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        mock_config = MagicMock()
        mock_config.ocr_language = "eng"
        mock_get_config.return_value = mock_config

        mock_result = MagicMock()
        mock_result.stdout = "Text with config"
        mock_run.return_value = mock_result

        result = ocr_image(img_file, tessconfig="--psm 6")

        assert result == "Text with config"
        # Verify tessconfig was appended to command
        call_args = mock_run.call_args[0][0]
        assert "--psm 6" in call_args


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

    @patch("obsidian_clipper.capture.screenshot.take_screenshot")
    def test_capture_returns_false_not_raises(self, mock_take):
        """Test capture handles take_screenshot returning False."""
        mock_take.return_value = False

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

    def test_cleanup_no_temp_file(self):
        """Test cleanup when no temp file exists."""
        capture = ScreenshotCapture()
        capture._temp_file = None

        # Should not raise
        capture.cleanup()

    def test_context_manager_enter_returns_self(self):
        """Test context manager __enter__ returns self."""
        capture = ScreenshotCapture()
        result = capture.__enter__()
        assert result is capture

    @patch("obsidian_clipper.capture.screenshot.ScreenshotCapture.cleanup")
    def test_context_manager_exit_calls_cleanup(self, mock_cleanup):
        """Test context manager __exit__ calls cleanup."""
        capture = ScreenshotCapture()

        capture.__exit__(None, None, None)

        mock_cleanup.assert_called_once()

    @patch("obsidian_clipper.capture.screenshot.take_screenshot")
    @patch("obsidian_clipper.capture.screenshot.ocr_image")
    def test_context_manager_full_usage(self, mock_ocr, mock_take):
        """Test using ScreenshotCapture as context manager."""
        mock_take.return_value = True
        mock_ocr.return_value = "OCR text"

        with ScreenshotCapture() as capture:
            path, ocr_text = capture.capture()
            assert path is not None
            assert ocr_text == "OCR text"


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
