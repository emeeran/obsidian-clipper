"""Main CLI entry point."""

from __future__ import annotations

import argparse
import logging
import sys

from ..capture import SourceType
from ..config import get_config
from ..exceptions import (
    APIConnectionError,
    ClipperError,
    ConfigurationError,
)
from ..obsidian import ObsidianClient
from ..utils import notify_error, notify_success
from ..workflow import CaptureSession, prepare_capture_session, process_and_save_content
from .args import parse_args, setup_logging

logger = logging.getLogger(__name__)


def validate_config() -> None:
    """Validate configuration and raise on errors."""
    config = get_config()
    errors = config.validate()

    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        raise ConfigurationError(
            "Invalid configuration. Please set required environment variables.\n"
            "See .env.example for reference."
        )


def _validate_session(session: CaptureSession, args: argparse.Namespace) -> str | None:
    """Validate capture session.

    Args:
        session: Capture session to validate.
        args: Command-line arguments.

    Returns:
        Error message if validation fails, None if valid.
    """
    # PDF/EPUB citations require page number
    if (
        session.citation
        and session.citation.source_type in (SourceType.PDF, SourceType.EPUB)
        and not session.citation.page
    ):
        return "Page number is required for PDF/EPUB citations."

    # Screenshot mode with OCR requires OCR text
    if args.screenshot and args.ocr and not args.no_ocr and not session.ocr_text:
        return "OCR returned no text. Retake screenshot or use --no-ocr to save image only."

    # Non-screenshot mode requires text selection
    if not session.text and not args.screenshot:
        return "No text selected."

    return None


def _save_and_notify(
    session: CaptureSession,
    client: ObsidianClient,
    note_path: str,
) -> int:
    """Process and save content, then notify user.

    Args:
        session: Capture session with content.
        client: Obsidian API client.
        note_path: Target note path.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    if not session.has_content():
        notify_error("Obsidian Capture Failed", "No content captured.")
        return 1

    if not process_and_save_content(session, client, note_path):
        notify_error("Obsidian Capture Failed", "Failed to append content.")
        return 1

    # Build success message
    preview = session.get_preview()
    msg = f'Captured: "{preview}"'
    if session.screenshot_success:
        msg += " + screenshot"
    if session.ocr_text:
        msg += " + OCR"

    notify_success("Obsidian Capture", msg)
    return 0


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    args = parse_args()
    setup_logging(verbose=args.verbose, debug=args.debug)

    try:
        validate_config()

        config = get_config()
        note_path = args.note or config.default_note

        with ObsidianClient(config) as client:
            if not client.check_connection():
                notify_error(
                    "Obsidian Capture Failed",
                    "Cannot connect to Obsidian Local REST API.",
                )
                return 1

            if not client.ensure_note_exists(note_path):
                notify_error(
                    "Obsidian Capture Failed",
                    f"Could not access note: {note_path}",
                )
                return 1

            session = prepare_capture_session(args)

            error = _validate_session(session, args)
            if error:
                notify_error("Obsidian Capture Failed", error)
                return 1

            return _save_and_notify(session, client, note_path)

    except ConfigurationError as e:
        notify_error("Configuration Error", str(e))
        logger.error(f"Configuration error: {e}")
        return 1
    except APIConnectionError as e:
        notify_error("Connection Error", str(e))
        logger.error(f"Connection error: {e}")
        return 1
    except ClipperError as e:
        notify_error("Capture Error", str(e))
        logger.error(f"Capture error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except Exception as e:
        notify_error("Unexpected Error", str(e))
        logger.exception("Unexpected error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
