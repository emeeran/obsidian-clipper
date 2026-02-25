"""Command-line argument parsing and logging setup."""

from __future__ import annotations

import argparse
import logging


def setup_logging(verbose: bool = False, debug: bool = False) -> None:
    """Configure logging level based on verbosity."""
    level = logging.WARNING
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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
        "--version",
        action="version",
        version="%(prog)s 2.0.0",
    )

    return parser.parse_args()
