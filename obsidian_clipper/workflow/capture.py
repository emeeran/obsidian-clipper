"""Capture workflow functions."""

from __future__ import annotations

import argparse
import logging

from ..capture import (
    Citation,
    ScreenshotCapture,
    SourceType,
    get_active_window_title,
    get_citation,
    get_selected_text,
    parse_citation_from_window_title,
)
from ..exceptions import ScreenshotError
from ..obsidian import ObsidianClient
from .session import CaptureSession

logger = logging.getLogger(__name__)


def _get_fallback_citation(pre_capture_title: str) -> Citation | None:
    """Get fallback citation from window title.

    Args:
        pre_capture_title: Window title captured before screenshot.

    Returns:
        Citation if valid fallback, None otherwise.
    """
    fallback_title = pre_capture_title.strip() or get_active_window_title().strip()

    if not fallback_title:
        return None

    # Always use window title as fallback, even for PDF/EPUB readers
    return Citation(
        title=fallback_title,
        source="Window",
        source_type=SourceType.UNKNOWN,
    )


def _capture_screenshot_session(
    session: CaptureSession,
    args: argparse.Namespace,
) -> None:
    """Handle screenshot capture with citation.

    Args:
        session: Capture session to update.
        args: Command-line arguments.
    """
    pre_capture_window_title = ""

    # Capture pre-screenshot window title for citation (always)
    pre_capture_window_title = get_active_window_title()
    session.citation = parse_citation_from_window_title(pre_capture_window_title)

    # Perform screenshot capture
    perform_ocr = args.ocr and not args.no_ocr
    capture = ScreenshotCapture(
        tool=args.screenshot_tool,
        ocr_language=args.ocr_lang,
        perform_ocr=perform_ocr,
    )

    try:
        screenshot_path, ocr_text = capture.capture()
        if screenshot_path:
            session.screenshot_path = screenshot_path
            session.ocr_text = ocr_text
            session.img_filename = screenshot_path.name

        # Retry citation after screenshot if still missing
        if session.citation is None:
            session.citation = get_citation()

        # Use fallback window citation if still no citation
        if session.citation is None:
            session.citation = _get_fallback_citation(pre_capture_window_title)

    except ScreenshotError as e:
        logger.warning(f"Screenshot capture failed: {e}")


def prepare_capture_session(args: argparse.Namespace) -> CaptureSession:
    """Prepare a capture session by collecting content.

    Args:
        args: Parsed command-line arguments.

    Returns:
        CaptureSession with captured content.
    """
    session = CaptureSession()

    # In screenshot mode, skip text capture so Flameshot opens immediately
    # Text will come from OCR instead
    if not args.screenshot:
        session.text = get_selected_text()

    # Always capture citation
    # In screenshot mode, citation is handled with pre-capture active window
    # title to avoid focus loss during the screenshot tool lifecycle.
    if not args.screenshot:
        session.citation = get_citation()

    # Capture screenshot if requested
    if args.screenshot:
        _capture_screenshot_session(session, args)

    return session


def process_and_save_content(
    session: CaptureSession,
    client: ObsidianClient,
    note_path: str,
) -> bool:
    """Process captured content and save to Obsidian.

    Args:
        session: Capture session with content.
        client: Obsidian API client.
        note_path: Target note path.

    Returns:
        True if successful.
    """
    # Upload screenshot if captured
    if session.screenshot_path and session.img_filename:
        if client.upload_image(session.screenshot_path, session.img_filename):
            session.screenshot_success = True

        # Cleanup temp file
        if session.screenshot_path.exists():
            session.screenshot_path.unlink()

    # Append content to note
    content = session.to_markdown()
    logger.debug("Session markdown content:\n%s", content)

    return client.append_to_note(note_path, content)
