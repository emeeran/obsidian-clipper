"""Screenshot and OCR capture utilities."""

from __future__ import annotations

import contextlib
import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path

from ..config import get_config
from ..exceptions import OCRError, ScreenshotError
from ..utils.command import run_command_safely

logger = logging.getLogger(__name__)


def take_screenshot(
    filepath: str | Path,
    tool: str = "auto",
) -> bool:
    """Capture screen area using available screenshot tools.

    Args:
        filepath: Path to save screenshot.
        tool: Screenshot tool to use ('flameshot', 'grim', 'auto').

    Returns:
        True if screenshot was captured successfully.

    Raises:
        ScreenshotError: If screenshot capture fails.
    """
    filepath = Path(filepath)
    filepath_str = str(filepath)

    if tool == "auto":
        # Try flameshot first (X11), then grim+slurp (Wayland)
        success = _capture_with_flameshot(filepath_str)
        if not success:
            success = _capture_with_grim(filepath_str)
        if not success:
            raise ScreenshotError("No compatible screenshot tool available")
    elif tool == "flameshot":
        if not _capture_with_flameshot(filepath_str):
            raise ScreenshotError("Flameshot capture failed")
    elif tool == "grim":
        if not _capture_with_grim(filepath_str):
            raise ScreenshotError("grim/slurp capture failed")
    else:
        raise ScreenshotError(f"Unknown screenshot tool: {tool}")

    return filepath.exists()


def _capture_with_flameshot(filepath: str) -> bool:
    """Capture screenshot using Flameshot (X11)."""
    try:
        if _capture_with_flameshot_raw(filepath):
            return True

        # Prefer auto-accept mode so area selection immediately writes file,
        # matching the expected hotkey workflow.
        cmd = ["flameshot", "gui", "-p", filepath, "--accept-on-select"]
        try:
            run_command_safely(
                cmd,
                timeout=60,  # Give user time to select area
                check=True,
            )
        except Exception:
            # Fallback for older Flameshot versions that don't support
            # --accept-on-select.
            run_command_safely(
                ["flameshot", "gui", "-p", filepath],
                timeout=60,
                check=True,
            )
        # Some Flameshot setups return before the file is fully materialized.
        # Wait briefly for file creation to avoid false negatives.
        wait_seconds = 3.0
        step_seconds = 0.1
        attempts = int(wait_seconds / step_seconds)

        for _ in range(attempts):
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                return True
            time.sleep(step_seconds)

        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            return True

        # Fallback: some Flameshot workflows place the image on clipboard
        # rather than writing directly to path.
        return _save_clipboard_image(filepath)
    except Exception:
        return False


def _capture_with_flameshot_raw(filepath: str) -> bool:
    """Capture screenshot using Flameshot raw PNG output."""
    try:
        result = subprocess.run(
            ["flameshot", "gui", "--raw", "--accept-on-select"],
            capture_output=True,
            timeout=60,
            check=False,
        )

        if result.returncode != 0 or not result.stdout:
            return False

        png_header = b"\x89PNG\r\n\x1a\n"
        if not result.stdout.startswith(png_header):
            return False

        with open(filepath, "wb") as output:
            output.write(result.stdout)

        return os.path.exists(filepath) and os.path.getsize(filepath) > 0
    except Exception:
        return False


def _save_clipboard_image(filepath: str) -> bool:
    """Try saving PNG image data from clipboard into filepath."""
    try:
        with open(filepath, "wb") as output:
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
                stdout=output,
                stderr=subprocess.PIPE,
                timeout=5,
                check=False,
            )

        return (
            result.returncode == 0
            and os.path.exists(filepath)
            and os.path.getsize(filepath) > 0
        )
    except Exception:
        return False


def _capture_with_grim(filepath: str) -> bool:
    """Capture screenshot using grim+slurp (Wayland).

    This uses slurp for area selection and grim for capture.
    """
    try:
        # First get the selection area from slurp
        slurp_result = subprocess.run(
            ["slurp"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if slurp_result.returncode != 0 or not slurp_result.stdout.strip():
            return False

        # Use the selection area with grim
        area = slurp_result.stdout.strip()
        grim_result = subprocess.run(
            ["grim", "-g", area, filepath],
            capture_output=True,
            timeout=10,
        )

        return grim_result.returncode == 0 and os.path.exists(filepath)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def ocr_image(
    img_path: str | Path,
    language: str | None = None,
    tessconfig: str | None = None,
) -> str:
    """Perform OCR on an image using Tesseract.

    Args:
        img_path: Path to the image file.
        language: Language code for OCR (e.g., 'eng', 'deu').
                  Defaults to config setting.
        tessconfig: Optional Tesseract configuration string.

    Returns:
        Extracted text, or empty string if OCR fails.

    Raises:
        OCRError: If OCR fails and image exists.
    """
    img_path = Path(img_path)

    if not img_path.exists():
        logger.warning(f"Image file not found: {img_path}")
        return ""

    config = get_config()
    lang = language or config.ocr_language

    try:
        cmd = ["tesseract", str(img_path), "stdout", "-l", lang]
        if tessconfig:
            cmd.append(tessconfig)

        result = run_command_safely(
            cmd,
            capture_output=True,
            timeout=30,
            check=True,
        )
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise OCRError(f"OCR processing failed: {e}") from e


def create_temp_screenshot(prefix: str = "obsidian_capture") -> Path:
    """Create a temporary file path for screenshots.

    Returns:
        Path to temporary file (file not created).
    """
    import datetime

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.png"
    return Path(tempfile.gettempdir()) / filename


class ScreenshotCapture:
    """High-level screenshot capture with OCR support."""

    def __init__(
        self,
        tool: str = "auto",
        ocr_language: str | None = None,
        perform_ocr: bool = True,
    ):
        self.tool = tool
        self.ocr_language = ocr_language
        self.perform_ocr = perform_ocr
        self._temp_file: Path | None = None

    def capture(self) -> tuple[Path | None, str]:
        """Capture screenshot and optionally perform OCR.

        Returns:
            Tuple of (screenshot_path, ocr_text).
            screenshot_path is None if capture failed.
            ocr_text is empty string if OCR not performed or failed.
        """
        self._temp_file = create_temp_screenshot()

        try:
            success = take_screenshot(self._temp_file, self.tool)
            if not success:
                return None, ""

            ocr_text = ""
            if self.perform_ocr:
                with contextlib.suppress(OCRError):
                    ocr_text = ocr_image(self._temp_file, self.ocr_language)

            return self._temp_file, ocr_text
        except ScreenshotError:
            return None, ""

    def cleanup(self) -> None:
        """Remove temporary screenshot file if it exists."""
        if self._temp_file and self._temp_file.exists():
            self._temp_file.unlink()
            self._temp_file = None
