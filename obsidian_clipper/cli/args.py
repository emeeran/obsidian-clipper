"""Command-line argument parsing and logging setup."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .._version import __version__
from ..utils.logging import setup_logging as setup_structured_logging


def setup_logging(verbose: bool = False, debug: bool = False) -> None:
    """Configure logging level based on verbosity.

    Supports both console and file logging with automatic rotation.
    Log file location can be set via LOG_FILE environment variable.
    """
    level = "WARNING"
    if debug:
        level = "DEBUG"
    elif verbose:
        level = "INFO"

    # Check for log file from environment or config
    log_file = os.environ.get("LOG_FILE")
    json_format = os.environ.get("LOG_FORMAT", "").lower() == "json"

    setup_structured_logging(
        level=level,
        log_file=Path(log_file) if log_file else None,
        json_format=json_format,
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="obsidian-clipper",
        description="Capture content to Obsidian via Local REST API.",
        epilog="""
Examples:
  %(prog)s                    # Capture selected text with citation
  %(prog)s -s                 # Capture text + screenshot + OCR + citation
  %(prog)s -n "Notes/Journal" # Use custom target note
  %(prog)s --ocr-lang deu     # Use German OCR language

Environment variables:
  LOG_FILE    Path to log file for persistent logging
  LOG_FORMAT  Set to 'json' for structured JSON logging
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-s",
        "--screenshot",
        action="store_true",
        help="Capture screenshot in addition to text",
    )
    parser.add_argument(
        "-o",
        "--ocr",
        action="store_true",
        default=True,
        help="Perform OCR on screenshot (enabled by default; use --no-ocr to disable)",
    )
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Disable OCR processing on screenshot",
    )
    parser.add_argument(
        "-n",
        "--note",
        default=None,
        help="Target note path (default: from config)",
    )
    parser.add_argument(
        "-t",
        "--tags",
        default=None,
        help="Comma-separated list of tags to add to the note",
    )
    parser.add_argument(
        "--template",
        default=None,
        help="Template string for note content",
    )
    parser.add_argument(
        "--ocr-lang",
        default=None,
        help="OCR language code (e.g., 'eng', 'deu', 'fra')",
    )
    parser.add_argument(
        "--image-format",
        choices=["png", "webp", "jpeg"],
        default="png",
        help="Image format for screenshots (default: png)",
    )
    parser.add_argument(
        "--image-quality",
        type=int,
        default=85,
        help="Image quality for compression (1-100, default: 85)",
    )
    parser.add_argument(
        "--config-ui",
        action="store_true",
        help="Launch the configuration TUI",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview capture as markdown without saving to Obsidian",
    )
    parser.add_argument(
        "-p",
        "--profile",
        default=None,
        help="Use a capture profile (e.g., 'research', 'quick', 'code')",
    )
    parser.add_argument(
        "--pick",
        action="store_true",
        help="Pick target note interactively via fzf or rofi",
    )
    parser.add_argument(
        "--vault",
        default=None,
        help="Use a named vault config (reads OBSIDIAN_<VAULT>_* env vars)",
    )
    parser.add_argument(
        "-a",
        "--append",
        action="store_true",
        help="Append to existing note instead of creating a new one",
    )
    parser.add_argument(
        "--annotate",
        action="store_true",
        help="Open screenshot for annotation before saving (requires flameshot)",
    )
    parser.add_argument(
        "--screenshot-tool",
        choices=["auto", "flameshot", "grim", "scrot"],
        default="auto",
        help="Screenshot tool to use (default: auto-detect)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Path to log file for persistent logging",
    )
    parser.add_argument(
        "--json-logs",
        action="store_true",
        help="Output logs in JSON format",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    # Handle log file from CLI args (overrides environment)
    if args.log_file:
        os.environ["LOG_FILE"] = str(args.log_file)
    if args.json_logs:
        os.environ["LOG_FORMAT"] = "json"

    return args
