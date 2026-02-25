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
        help="Perform OCR on screenshot (default: True)",
    )
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Skip OCR processing on screenshot",
    )
    parser.add_argument(
        "-n",
        "--note",
        default=None,
        help="Target note path (default: from config)",
    )
    parser.add_argument(
        "--ocr-lang",
        default=None,
        help="OCR language code (e.g., 'eng', 'deu', 'fra')",
    )
    parser.add_argument(
        "--screenshot-tool",
        choices=["auto", "flameshot", "grim"],
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
