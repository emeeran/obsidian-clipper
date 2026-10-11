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
from ..utils.command import CommandError, run_command_safely

logger = logging.getLogger(__name__)


def _wait_for_file(filepath: str | Path, timeout: float = 3.0) -> bool:
    """Wait for file to exist with exponential backoff.

    Args:
        filepath: Path to wait for.
        timeout: Maximum time to wait in seconds.

    Returns:
        True if file exists and has content, False otherwise.
    """
    filepath = Path(filepath)
    start_time = time.time()
    poll_interval = 0.05  # Start with 50ms
    max_interval = 0.5  # Max 500ms between polls

    while time.time() - start_time < timeout:
        try:
            if filepath.stat().st_size > 0:
                return True
        except FileNotFoundError:
            pass
        time.sleep(poll_interval)
        poll_interval = min(poll_interval * 1.5, max_interval)

    try:
        return filepath.stat().st_size > 0
    except FileNotFoundError:
        return False


def detect_display_server() -> str:
    """Detect the current display server type.

    Returns:
        'x11', 'wayland', or 'unknown'.
    """
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type == "x11":
        return "x11"
    if session_type == "wayland":
        return "wayland"
    # Fallback heuristics
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return "unknown"


def take_screenshot(
    filepath: str | Path,
    tool: str = "auto",
    annotate: bool = False,
) -> bool:
    """Capture screen area using available screenshot tools.

    Args:
        filepath: Path to save screenshot.
        tool: Screenshot tool to use ('flameshot', 'grim', 'scrot', 'auto').
        annotate: Open screenshot in annotation editor before saving.

    Returns:
        True if screenshot was captured successfully.

    Raises:
        ScreenshotError: If screenshot capture fails.
    """
    filepath = Path(filepath)
    filepath_str = str(filepath)

    if tool == "auto":
        display = detect_display_server()
        # Try the native tool first based on detected display server
        if display == "wayland":
            success = _capture_with_grim(filepath_str)
            if not success:
                success = _capture_with_flameshot(filepath_str)
        else:
            # X11 or unknown — try flameshot first, then scrot
            success = _capture_with_flameshot(filepath_str)
            if not success:
                success = _capture_with_grim(filepath_str)
            if not success:
                success = _capture_with_scrot(filepath_str)
        if not success:
            raise ScreenshotError(
                f"No compatible screenshot tool available (detected: {display}). "
                "Install one of: flameshot (X11), grim+slurp (Wayland), scrot"
            )
    elif tool == "flameshot":
        if not _capture_with_flameshot(filepath_str, annotate=annotate):
            raise ScreenshotError(
                "Flameshot capture failed. "
                "Install: sudo apt install flameshot"
            )
    elif tool == "grim":
        if not _capture_with_grim(filepath_str):
            raise ScreenshotError(
                "grim/slurp capture failed. "
                "Install: sudo apt install grim slurp (Wayland only)"
            )
    else:
        raise ScreenshotError(f"Unknown screenshot tool: {tool}")

    return filepath.exists()


def _capture_with_flameshot(filepath: str, annotate: bool = False) -> bool:
    """Capture screenshot using Flameshot (X11).

    Args:
        filepath: Path to save screenshot.
        annotate: Skip raw capture and go straight to GUI for annotation.
    """
    try:
        # When annotating, skip the fast raw path and go straight to GUI
        if not annotate and _capture_with_flameshot_raw(filepath):
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
        except (CommandError, subprocess.SubprocessError, OSError):
            # Fallback for older Flameshot versions that don't support
            # --accept-on-select.
            run_command_safely(
                ["flameshot", "gui", "-p", filepath],
                timeout=60,
                check=True,
            )
        # Some Flameshot setups return before the file is fully materialized.
        # Wait with exponential backoff for file creation to avoid false negatives.
        if _wait_for_file(filepath, timeout=3.0):
            return True

        # Fallback: some Flameshot workflows place the image on clipboard
        # rather than writing directly to path.
        return _save_clipboard_image(filepath)
    except (CommandError, subprocess.SubprocessError, OSError):
        return False


def _capture_with_flameshot_raw(filepath: str) -> bool:
    """Capture screenshot using Flameshot raw PNG output."""
    try:
        result = run_command_safely(
            ["flameshot", "gui", "--raw", "--accept-on-select"],
            timeout=60,
            text=False,
        )

        if result.returncode != 0 or not result.stdout:
            return False

        png_header = b"\x89PNG\r\n\x1a\n"
        if not result.stdout.startswith(png_header):
            return False

        with open(filepath, "wb") as output:
            output.write(result.stdout)

        return os.path.exists(filepath) and os.path.getsize(filepath) > 0
    except (subprocess.SubprocessError, OSError):
        return False


def _save_clipboard_image(filepath: str) -> bool:
    """Try saving PNG image data from clipboard into filepath."""
    try:
        result = run_command_safely(
            ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
            timeout=5,
            text=False,
        )

        if result.returncode != 0 or not result.stdout:
            # Clean up empty/failed file to avoid leaving garbage on disk
            with contextlib.suppress(OSError):
                os.unlink(filepath)
            return False

        with open(filepath, "wb") as output:
            output.write(result.stdout)

        if os.path.getsize(filepath) == 0:
            with contextlib.suppress(OSError):
                os.unlink(filepath)
            return False

        return True
    except (subprocess.SubprocessError, OSError):
        # Clean up on exception too
        with contextlib.suppress(OSError):
            os.unlink(filepath)
        return False


def _capture_with_grim(filepath: str) -> bool:
    """Capture screenshot using grim+slurp (Wayland).

    This uses slurp for area selection and grim for capture.
    """
    try:
        # First get the selection area from slurp
        slurp_result = run_command_safely(
            ["slurp"],
            timeout=60,
        )

        if slurp_result.returncode != 0 or not slurp_result.stdout.strip():
            return False

        # Use the selection area with grim
        area = slurp_result.stdout.strip()
        grim_result = run_command_safely(
            ["grim", "-g", area, filepath],
            timeout=10,
        )

        return grim_result.returncode == 0 and os.path.exists(filepath)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _capture_with_scrot(filepath: str) -> bool:
    """Capture screenshot using scrot (X11 fallback).

    scrot is a simple, widely-available X11 screenshot tool that supports
    interactive area selection with -s.
    """
    try:
        result = run_command_safely(
            ["scrot", "-s", filepath],
            timeout=60,
        )
        return result.returncode == 0 and os.path.exists(filepath)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _preprocess_for_ocr(img_path: Path) -> Path:
    """Preprocess image for better OCR accuracy.

    Converts to grayscale and increases contrast. Saves the enhanced
    image to a temp path and returns it. Falls back to the original
    if Pillow is unavailable or processing fails.

    Args:
        img_path: Path to the original image.

    Returns:
        Path to the preprocessed image (or original on failure).
    """
    try:
        from PIL import Image, ImageEnhance, ImageFilter
    except ImportError:
        return img_path

    try:
        with Image.open(img_path) as img:
            # Convert to grayscale for cleaner OCR
            if img.mode != "L":
                img = img.convert("L")  # type: ignore[assignment]

            # Increase contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)  # type: ignore[assignment]

            # Slight sharpening
            img = img.filter(ImageFilter.SHARPEN)  # type: ignore[assignment]

            # Save to temp file
            out_path = img_path.with_suffix(".ocr.png")
            img.save(out_path, "PNG")
            return out_path
    except Exception as e:
        logger.debug("Image preprocessing failed, using original: %s", e)
        return img_path


def _tsv_to_text_conf(tsv: str) -> tuple[str, float]:
    """Parse tesseract TSV output into (text, mean word confidence).

    Words (TSV level 5) are grouped by block/paragraph/line, preserving
    tesseract's layout order; a blank line separates layout blocks.
    Low-confidence (-1) and empty words are dropped from both the text
    and the confidence mean.
    """
    line_words: dict[tuple[str, str, str], list[str]] = {}
    order: list[tuple[str, tuple[str, str, str]]] = []
    confs: list[float] = []
    for row in tsv.splitlines()[1:]:
        cols = row.split("\t")
        if len(cols) < 12 or cols[0] != "5":
            continue
        try:
            conf = float(cols[10])
        except ValueError:
            continue
        text = cols[11].strip()
        if not text or conf < 0:
            continue
        key = (cols[2], cols[3], cols[4])
        if key not in line_words:
            order.append((cols[2], key))
        line_words[key] = line_words.get(key, []) + [text]
        confs.append(conf)

    if not order:
        return "", 0.0

    out: list[str] = []
    prev_block: str | None = None
    for block, key in order:
        if prev_block is not None and block != prev_block:
            out.append("")
        out.append(" ".join(line_words[key]))
        prev_block = block
    return "\n".join(out), sum(confs) / len(confs)


def _tesseract_tsv(ocr_path: Path, lang: str, psm: int, tessconfig: str | None) -> str:
    """Run tesseract once with TSV output for the given page segmentation mode."""
    cmd = ["tesseract", str(ocr_path), "stdout", "-l", lang, "--psm", str(psm)]
    if tessconfig:
        cmd.append(tessconfig)
    cmd.append("tsv")  # config file must come last: switches output to TSV
    result = run_command_safely(cmd, capture_output=True, timeout=30, check=True)
    return str(result.stdout)


def ocr_image(
    img_path: str | Path,
    language: str | None = None,
    tessconfig: str | None = None,
) -> str:
    """Perform layout-aware OCR on an image using Tesseract.

    Runs TSV segmentation for each candidate PSM (3: automatic layout,
    6: uniform block — better for terminals/columnar screenshots) and keeps
    the text with the higher mean word confidence. OBSIDIAN_OCR_PSM pins a
    single mode.

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
        logger.warning("Image file not found: %s", img_path)
        return ""

    config = get_config()
    lang = language or config.ocr_language

    # Preprocess image for better OCR results
    ocr_path = _preprocess_for_ocr(img_path)

    try:
        candidates = [config.ocr_psm] if config.ocr_psm else [3, 6]
        best_text, best_conf = "", -1.0
        for psm in candidates:
            text, conf = _tsv_to_text_conf(_tesseract_tsv(ocr_path, lang, psm, tessconfig))
            logger.debug("OCR psm %d: conf %.1f, %d chars", psm, conf, len(text))
            if conf > best_conf:
                best_text, best_conf = text, conf
        return best_text
    except FileNotFoundError:
        raise OCRError(
            "Tesseract not found. Install: sudo apt install tesseract-ocr"
        ) from None
    except Exception as e:
        logger.error("OCR failed: %s", e)
        raise OCRError(f"OCR processing failed: {e}") from e
    finally:
        # Always remove the preprocessed image so it doesn't accumulate in /tmp.
        if ocr_path != img_path:
            ocr_path.unlink(missing_ok=True)


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
    """High-level screenshot capture with OCR support.

    Can be used as a context manager to ensure cleanup:

        with ScreenshotCapture() as capture:
            path, text = capture.capture()
            # ... use path and text
        # Temp file automatically cleaned up
    """

    def __init__(
        self,
        tool: str = "auto",
        ocr_language: str | None = None,
        perform_ocr: bool = True,
        annotate: bool = False,
    ):
        self.tool = tool
        self.ocr_language = ocr_language
        self.perform_ocr = perform_ocr
        self.annotate = annotate
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
            success = take_screenshot(self._temp_file, self.tool, annotate=self.annotate)
            if not success:
                return None, ""

            ocr_text = ""
            if self.perform_ocr:
                try:
                    ocr_text = ocr_image(self._temp_file, self.ocr_language)
                except OCRError as e:
                    # OCR is best-effort: keep the screenshot, log why text is missing.
                    logger.warning("OCR failed for screenshot: %s", e)
                    ocr_text = ""

            return self._temp_file, ocr_text
        except ScreenshotError:
            self.cleanup()
            return None, ""

    def cleanup(self) -> None:
        """Remove temporary screenshot file if it exists."""
        if self._temp_file and self._temp_file.exists():
            self._temp_file.unlink()
            self._temp_file = None

    def __enter__(self) -> ScreenshotCapture:
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context manager, ensuring cleanup."""
        self.cleanup()
