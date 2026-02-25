"""Capture module for Obsidian Clipper."""

from .citation import (
    Citation,
    SourceType,
    get_citation,
    parse_browser_citation,
    parse_citation_from_window_title,
    parse_code_editor_citation,
    parse_epub_citation,
    parse_generic_citation,
    parse_pdf_citation,
)
from .screenshot import (
    ScreenshotCapture,
    create_temp_screenshot,
    ocr_image,
    take_screenshot,
)
from .text import copy_to_clipboard, get_active_window_title, get_selected_text

__all__ = [
    # Text capture
    "get_selected_text",
    "get_active_window_title",
    "copy_to_clipboard",
    # Screenshot capture
    "take_screenshot",
    "ocr_image",
    "create_temp_screenshot",
    "ScreenshotCapture",
    # Citation
    "Citation",
    "SourceType",
    "get_citation",
    "parse_citation_from_window_title",
    "parse_pdf_citation",
    "parse_epub_citation",
    "parse_generic_citation",
    "parse_browser_citation",
    "parse_code_editor_citation",
]
