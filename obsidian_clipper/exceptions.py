"""Custom exceptions for Obsidian Clipper."""

from __future__ import annotations

from typing import Any


class ClipperError(Exception):
    """Base exception for Obsidian Clipper errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        if self.context:
            context_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message


class ConfigurationError(ClipperError):
    """Raised when configuration is invalid or missing."""

    pass


class APIConnectionError(ClipperError):
    """Raised when unable to connect to Obsidian Local REST API."""

    pass


class APIRequestError(ClipperError):
    """Raised when an API request fails."""

    pass


class CaptureError(ClipperError):
    """Raised when content capture fails."""

    pass


class ScreenshotError(CaptureError):
    """Raised when screenshot capture fails."""

    pass


class OCRError(CaptureError):
    """Raised when OCR processing fails."""

    pass


class PathSecurityError(ClipperError):
    """Raised when a path fails security validation."""

    pass
