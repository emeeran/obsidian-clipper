"""Capture workflow functions."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

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


def _optimize_screenshot(
    image_path: Path,
    img_format: str = "png",
    quality: int = 85,
) -> Path:
    """Optimize screenshot image using Pillow."""
    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow not installed. Skipping image optimization.")
        return image_path

    try:
        with Image.open(image_path) as img:
            out_path = image_path.with_suffix(f".{img_format.lower()}")
            save_kwargs = {}
            if img_format.lower() in ("jpeg", "jpg", "webp"):
                save_kwargs["quality"] = quality
                if img.mode == "RGBA":
                    img = img.convert("RGB")
            img.save(out_path, format=img_format, **save_kwargs)
            if out_path != image_path:
                image_path.unlink()
            return out_path
    except Exception as e:
        logger.warning(f"Image optimization failed: {e}")
        return image_path


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
        annotate=getattr(args, "annotate", False),
    )

    try:
        screenshot_path, ocr_text = capture.capture()
        if screenshot_path:
            # Optimize image
            screenshot_path = _optimize_screenshot(
                screenshot_path,
                img_format=args.image_format,
                quality=args.image_quality,
            )
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

    if args.tags:
        session.tags = [t.strip() for t in args.tags.split(",")]
    session.template = args.template

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
    target_dir: str = "",
    append: bool = False,
) -> bool:
    """Process captured content and save to Obsidian.

    Args:
        session: Capture session with content.
        client: Obsidian API client.
        target_dir: Target directory for new notes (e.g., "00-Inbox/").
        append: If True, append to target_dir (treated as note path) instead of creating a new note.

    Returns:
        True if successful.
    """
    # Upload screenshot if captured
    if session.screenshot_path and session.img_filename:
        try:
            if client.upload_image(session.screenshot_path, session.img_filename):
                session.screenshot_success = True
        finally:
            # Cleanup temp file regardless of upload success
            if session.screenshot_path.exists():
                session.screenshot_path.unlink()

    content = session.to_markdown(include_frontmatter=not append)

    if append:
        # target_dir is the note path to append to
        logger.debug("Appending to note: %s", target_dir)
        # Ensure the note exists first
        if not client.ensure_note_exists(target_dir):
            logger.error("Failed to ensure note exists: %s", target_dir)
            return False
        return client.append_to_note(target_dir, "\n" + content)
    else:
        # Generate unique note path and create new note
        note_path = session.get_note_filename(target_dir)
        logger.debug("Creating note: %s", note_path)
        logger.debug("Session markdown content:\n%s", content)
        return client.create_note(note_path, content)
