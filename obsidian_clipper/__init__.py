"""Obsidian Clipper - Capture content to Obsidian via Local REST API.

A modular Python tool for capturing text, screenshots, and OCR content
directly to Obsidian notes using the Local REST API plugin.

Example usage:
    from obsidian_clipper import ObsidianClient, get_selected_text, get_citation

    client = ObsidianClient()
    text = get_selected_text()
    citation = get_citation()

    content = f"> {text}\\n{citation.format_markdown()}"
    client.append_to_note("Notes.md", content)
"""

from __future__ import annotations

__version__ = "2.0.0"
__author__ = "Obsidian Clipper Contributors"

from .capture import (
    Citation,
    ScreenshotCapture,
    SourceType,
    copy_to_clipboard,
    create_temp_screenshot,
    get_active_window_title,
    get_citation,
    get_selected_text,
    ocr_image,
    parse_browser_citation,
    parse_pdf_citation,
    take_screenshot,
)
from .config import Config, get_config, set_config
from .exceptions import (
    APIConnectionError,
    APIRequestError,
    CaptureError,
    ClipperError,
    ConfigurationError,
    OCRError,
    PathSecurityError,
    ScreenshotError,
    TextCaptureError,
)
from .obsidian import ObsidianClient, validate_path
from .utils import Urgency, notify, notify_error, notify_success

__all__ = [
    # Version
    "__version__",
    # Configuration
    "Config",
    "get_config",
    "set_config",
    # Exceptions
    "ClipperError",
    "ConfigurationError",
    "APIConnectionError",
    "APIRequestError",
    "CaptureError",
    "ScreenshotError",
    "OCRError",
    "TextCaptureError",
    "PathSecurityError",
    # API Client
    "ObsidianClient",
    "validate_path",
    # Capture utilities
    "get_selected_text",
    "get_active_window_title",
    "copy_to_clipboard",
    "take_screenshot",
    "ocr_image",
    "create_temp_screenshot",
    "ScreenshotCapture",
    # Citation
    "Citation",
    "SourceType",
    "get_citation",
    "parse_pdf_citation",
    "parse_browser_citation",
    # Notifications
    "notify",
    "notify_success",
    "notify_error",
    "Urgency",
]
