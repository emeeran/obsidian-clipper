"""Custom exceptions for Obsidian Clipper."""

from __future__ import annotations

from typing import Any


class ClipperError(Exception):
    """Base exception for Obsidian Clipper errors.

    Attributes:
        message: Error message.
        context: Additional context dictionary for debugging.
    """

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
    """Raised when configuration is invalid or missing.

    Attributes:
        missing_keys: List of missing configuration keys.
    """

    def __init__(
        self,
        message: str,
        missing_keys: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, context)
        self.missing_keys = missing_keys or []


class APIConnectionError(ClipperError):
    """Raised when unable to connect to Obsidian Local REST API.

    Attributes:
        url: URL that failed to connect.
    """

    def __init__(
        self,
        message: str,
        url: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        ctx = context or {}
        if url:
            ctx["url"] = url
        super().__init__(message, ctx)
        self.url = url


class APIRequestError(ClipperError):
    """Raised when an API request fails.

    Attributes:
        status_code: HTTP status code if available.
        url: URL that was requested.
        response_body: Response body for debugging.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        url: str | None = None,
        response_body: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        ctx = context or {}
        if status_code is not None:
            ctx["status_code"] = status_code
        if url:
            ctx["url"] = url
        if response_body:
            ctx["response_body"] = response_body[:200]  # Truncate for safety
        super().__init__(message, ctx)
        self.status_code = status_code
        self.url = url
        self.response_body = response_body


class CaptureError(ClipperError):
    """Raised when content capture fails."""

    pass


class ScreenshotError(CaptureError):
    """Raised when screenshot capture fails.

    Attributes:
        tool: Screenshot tool that was used.
        file_path: Path where screenshot was to be saved.
    """

    def __init__(
        self,
        message: str,
        tool: str | None = None,
        file_path: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        ctx = context or {}
        if tool:
            ctx["tool"] = tool
        if file_path:
            ctx["file_path"] = file_path
        super().__init__(message, ctx)
        self.tool = tool
        self.file_path = file_path


class OCRError(CaptureError):
    """Raised when OCR processing fails.

    Attributes:
        file_path: Path to image file.
        language: OCR language that was used.
    """

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        language: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        ctx = context or {}
        if file_path:
            ctx["file_path"] = file_path
        if language:
            ctx["language"] = language
        super().__init__(message, ctx)
        self.file_path = file_path
        self.language = language


class TextCaptureError(CaptureError):
    """Raised when text capture fails."""

    pass


class PathSecurityError(ClipperError):
    """Raised when a path fails security validation.

    Attributes:
        path: The problematic path.
    """

    def __init__(
        self,
        message: str,
        path: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        ctx = context or {}
        if path:
            ctx["path"] = path
        super().__init__(message, ctx)
        self.path = path
