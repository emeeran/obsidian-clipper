"""Main CLI entry point."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from ..capture import SourceType
from ..config import get_config, get_profile, get_vault_config
from ..exceptions import (
    APIConnectionError,
    ClipperError,
    ConfigurationError,
)
from ..obsidian import ObsidianClient
from ..utils import notify_error, notify_success
from ..utils.command import run_command_safely
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
            "Run `obsidian-clipper --config-ui` for guided setup."
        )


def _pick_note_with_fzf(client: ObsidianClient) -> str | None:
    """Interactively pick a note using fzf or rofi.

    Queries the vault for .md files and presents them via an interactive picker.

    Args:
        client: Obsidian API client for listing notes.

    Returns:
        Selected note path, or None if cancelled or picker unavailable.
    """
    # Fetch vault file list via the API search endpoint
    try:
        response = client._request("GET", "/")
        if response.status_code != 200:
            logger.warning("Could not list vault files")
            return None
        files = response.json().get("files", [])
        md_files = [f for f in files if f.endswith(".md")]
    except Exception as e:
        logger.warning(f"Failed to list vault files: {e}")
        return None

    if not md_files:
        logger.warning("No markdown files found in vault")
        return None

    # Try fzf first, then rofi
    file_list = "\n".join(md_files)
    for picker_cmd in [["fzf", "--prompt", "Select note: "], ["rofi", "-dmenu", "-p", "Note"]]:
        try:
            result = run_command_safely(
                picker_cmd,
                input_text=file_list,
                timeout=60,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            continue

    return None


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
        return "No text selected. Highlight text before pressing the shortcut."

    return None


def _save_and_notify(
    session: CaptureSession,
    client: ObsidianClient,
    target_dir: str,
    append: bool = False,
) -> int:
    """Process and save content, then notify user.

    Args:
        session: Capture session with content.
        client: Obsidian API client.
        target_dir: Target directory for new notes.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    if not session.has_content():
        notify_error("Obsidian Capture Failed", "No content captured.")
        return 1

    if not process_and_save_content(session, client, target_dir, append=append):
        notify_error("Obsidian Capture Failed", "Failed to create note.")
        return 1

    # Build success message with content details
    preview = session.get_preview(60)
    parts: list[str] = [f'"{preview}"']
    if session.screenshot_success:
        parts.append("screenshot")
    if session.ocr_text:
        parts.append("OCR")
    if session.citation:
        parts.append(f"from {session.citation.source or session.citation.source_type.value}")

    msg = "Captured " + " + ".join(parts)
    notify_success("Obsidian Capture", msg)
    return 0


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    args = parse_args()
    setup_logging(verbose=args.verbose, debug=args.debug)

    # Apply capture profile if specified (doesn't override explicit CLI args)
    if args.profile:
        try:
            profile = get_profile(args.profile)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        if args.tags is None and "tags" in profile:
            args.tags = profile["tags"]
        if args.note is None and "note" in profile:
            args.note = profile["note"]
        if isinstance(profile.get("ocr"), bool) and not args.no_ocr:
            args.ocr = profile["ocr"]
        if isinstance(profile.get("append"), bool) and not args.append:
            args.append = profile["append"]

    # Launch TUI if requested
    if args.config_ui:
        from .tui import launch_config_ui

        launch_config_ui()
        return 0

    try:
        validate_config()

        # Load vault-specific config if requested
        if args.vault:
            config = get_vault_config(args.vault)
            errors = config.validate()
            if errors:
                raise ConfigurationError(
                    f"Vault '{args.vault}' config error: {'; '.join(errors)}"
                )
        else:
            config = get_config()

        # Dry-run: capture content, print markdown, exit
        if args.dry_run:
            session = prepare_capture_session(args)
            error = _validate_session(session, args)
            if error:
                print(f"Error: {error}", file=sys.stderr)
                return 1
            print(session.to_markdown())
            return 0

        # Use args.note as target directory, or default_note from config
        target_dir = args.note or config.default_note

        with ObsidianClient(config) as client:
            if not client.check_connection():
                notify_error(
                    "Obsidian Capture Failed",
                    f"Cannot connect to Obsidian at {config.base_url}.\n"
                    "Troubleshooting:\n"
                    "  1. Is Obsidian running?\n"
                    "  2. Is the 'Local REST API' plugin installed and enabled?\n"
                    "  3. Does the API key match? Run: obsidian-clipper --config-ui\n"
                    f"  4. Test manually: curl -H 'Authorization: Bearer ...' {config.base_url}/",
                )
                return 1

            # Interactive note picker overrides target_dir
            if args.pick:
                picked = _pick_note_with_fzf(client)
                if picked is None:
                    notify_error("Obsidian Capture", "Note picker cancelled or unavailable.")
                    return 1
                target_dir = picked

            # If target_dir ends with .md, extract the directory part (unless appending)
            if not args.append and target_dir.endswith(".md"):
                target_dir = str(Path(target_dir).parent)

            session = prepare_capture_session(args)

            error = _validate_session(session, args)
            if error:
                notify_error("Obsidian Capture Failed", error)
                return 1

            return _save_and_notify(session, client, target_dir, append=args.append)

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
