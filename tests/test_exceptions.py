"""Tests for custom exceptions."""

from __future__ import annotations

import pytest

from obsidian_clipper.exceptions import (
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


class TestClipperError:
    """Tests for ClipperError base class."""

    def test_message_only(self):
        """Test exception with message only."""
        err = ClipperError("Something went wrong")
        assert err.message == "Something went wrong"
        assert err.context == {}
        assert str(err) == "Something went wrong"

    def test_with_context(self):
        """Test exception with context dictionary."""
        err = ClipperError("Error occurred", context={"key": "value", "count": 42})
        assert err.message == "Error occurred"
        assert err.context == {"key": "value", "count": 42}
        assert "key='value'" in str(err)
        assert "count=42" in str(err)

    def test_empty_context(self):
        """Test exception with empty context dict."""
        err = ClipperError("Error", context={})
        assert err.context == {}
        assert str(err) == "Error"

    def test_none_context(self):
        """Test exception with None context."""
        err = ClipperError("Error", context=None)
        assert err.context == {}
        assert str(err) == "Error"

    def test_inherits_from_exception(self):
        """Test that ClipperError inherits from Exception."""
        err = ClipperError("Test")
        assert isinstance(err, Exception)


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_message_only(self):
        """Test with message only."""
        err = ConfigurationError("Config invalid")
        assert err.message == "Config invalid"
        assert err.missing_keys == []

    def test_with_missing_keys(self):
        """Test with missing keys list."""
        err = ConfigurationError(
            "Missing required config",
            missing_keys=["api_key", "vault_path"],
        )
        assert err.missing_keys == ["api_key", "vault_path"]

    def test_with_context(self):
        """Test with context dictionary."""
        err = ConfigurationError(
            "Config error",
            missing_keys=["api_key"],
            context={"file": "/path/to/config"},
        )
        assert err.missing_keys == ["api_key"]
        assert err.context == {"file": "/path/to/config"}

    def test_inherits_from_clipper_error(self):
        """Test that ConfigurationError inherits from ClipperError."""
        err = ConfigurationError("Test")
        assert isinstance(err, ClipperError)


class TestAPIConnectionError:
    """Tests for APIConnectionError."""

    def test_message_only(self):
        """Test with message only."""
        err = APIConnectionError("Failed to connect")
        assert err.message == "Failed to connect"
        assert err.url is None

    def test_with_url(self):
        """Test with URL parameter."""
        err = APIConnectionError("Connection failed", url="https://localhost:27123")
        assert err.url == "https://localhost:27123"
        assert err.context["url"] == "https://localhost:27123"

    def test_with_url_and_context(self):
        """Test URL is merged into context."""
        err = APIConnectionError(
            "Failed",
            url="https://localhost:27123",
            context={"timeout": 30},
        )
        assert err.url == "https://localhost:27123"
        assert err.context["url"] == "https://localhost:27123"
        assert err.context["timeout"] == 30


class TestAPIRequestError:
    """Tests for APIRequestError."""

    def test_message_only(self):
        """Test with message only."""
        err = APIRequestError("Request failed")
        assert err.message == "Request failed"
        assert err.status_code is None
        assert err.url is None
        assert err.response_body is None

    def test_with_status_code(self):
        """Test with status code."""
        err = APIRequestError("Not found", status_code=404)
        assert err.status_code == 404
        assert err.context["status_code"] == 404

    def test_with_url(self):
        """Test with URL."""
        err = APIRequestError("Error", url="https://api.example.com/vault/note")
        assert err.url == "https://api.example.com/vault/note"
        assert err.context["url"] == "https://api.example.com/vault/note"

    def test_with_response_body(self):
        """Test with response body."""
        long_body = "x" * 500
        err = APIRequestError("Error", response_body=long_body)
        assert err.response_body == long_body
        # Context should have truncated version
        assert len(err.context["response_body"]) == 200

    def test_with_all_params(self):
        """Test with all parameters."""
        err = APIRequestError(
            "Server error",
            status_code=500,
            url="https://localhost:27123/vault",
            response_body="Internal Server Error",
        )
        assert err.status_code == 500
        assert err.url == "https://localhost:27123/vault"
        assert err.response_body == "Internal Server Error"
        assert err.context["status_code"] == 500
        assert err.context["url"] == "https://localhost:27123/vault"


class TestCaptureError:
    """Tests for CaptureError."""

    def test_message_only(self):
        """Test with message only."""
        err = CaptureError("Capture failed")
        assert err.message == "Capture failed"

    def test_inherits_from_clipper_error(self):
        """Test that CaptureError inherits from ClipperError."""
        err = CaptureError("Test")
        assert isinstance(err, ClipperError)


class TestScreenshotError:
    """Tests for ScreenshotError."""

    def test_message_only(self):
        """Test with message only."""
        err = ScreenshotError("Screenshot failed")
        assert err.message == "Screenshot failed"
        assert err.tool is None
        assert err.file_path is None

    def test_with_tool(self):
        """Test with tool parameter."""
        err = ScreenshotError("Capture failed", tool="flameshot")
        assert err.tool == "flameshot"
        assert err.context["tool"] == "flameshot"

    def test_with_file_path(self):
        """Test with file path parameter."""
        err = ScreenshotError("Failed", file_path="/tmp/screenshot.png")
        assert err.file_path == "/tmp/screenshot.png"
        assert err.context["file_path"] == "/tmp/screenshot.png"

    def test_with_all_params(self):
        """Test with all parameters."""
        err = ScreenshotError(
            "Tool failed",
            tool="grim",
            file_path="/tmp/capture.png",
            context={"display": ":0"},
        )
        assert err.tool == "grim"
        assert err.file_path == "/tmp/capture.png"
        assert err.context["tool"] == "grim"
        assert err.context["file_path"] == "/tmp/capture.png"
        assert err.context["display"] == ":0"

    def test_inherits_from_capture_error(self):
        """Test that ScreenshotError inherits from CaptureError."""
        err = ScreenshotError("Test")
        assert isinstance(err, CaptureError)


class TestOCRError:
    """Tests for OCRError."""

    def test_message_only(self):
        """Test with message only."""
        err = OCRError("OCR failed")
        assert err.message == "OCR failed"
        assert err.file_path is None
        assert err.language is None

    def test_with_file_path(self):
        """Test with file path parameter."""
        err = OCRError("OCR error", file_path="/tmp/image.png")
        assert err.file_path == "/tmp/image.png"
        assert err.context["file_path"] == "/tmp/image.png"

    def test_with_language(self):
        """Test with language parameter."""
        err = OCRError("OCR error", language="eng")
        assert err.language == "eng"
        assert err.context["language"] == "eng"

    def test_with_all_params(self):
        """Test with all parameters."""
        err = OCRError(
            "OCR processing failed",
            file_path="/tmp/screenshot.png",
            language="deu",
            context={"tesseract_version": "5.3"},
        )
        assert err.file_path == "/tmp/screenshot.png"
        assert err.language == "deu"
        assert err.context["file_path"] == "/tmp/screenshot.png"
        assert err.context["language"] == "deu"
        assert err.context["tesseract_version"] == "5.3"

    def test_inherits_from_capture_error(self):
        """Test that OCRError inherits from CaptureError."""
        err = OCRError("Test")
        assert isinstance(err, CaptureError)


class TestTextCaptureError:
    """Tests for TextCaptureError."""

    def test_message_only(self):
        """Test with message only."""
        err = TextCaptureError("Text capture failed")
        assert err.message == "Text capture failed"

    def test_inherits_from_capture_error(self):
        """Test that TextCaptureError inherits from CaptureError."""
        err = TextCaptureError("Test")
        assert isinstance(err, CaptureError)


class TestPathSecurityError:
    """Tests for PathSecurityError."""

    def test_message_only(self):
        """Test with message only."""
        err = PathSecurityError("Invalid path")
        assert err.message == "Invalid path"
        assert err.path is None

    def test_with_path(self):
        """Test with path parameter."""
        err = PathSecurityError("Path traversal detected", path="../../../etc/passwd")
        assert err.path == "../../../etc/passwd"
        assert err.context["path"] == "../../../etc/passwd"

    def test_with_path_and_context(self):
        """Test with path and context."""
        err = PathSecurityError(
            "Security violation",
            path="/etc/shadow",
            context={"user": "admin"},
        )
        assert err.path == "/etc/shadow"
        assert err.context["path"] == "/etc/shadow"
        assert err.context["user"] == "admin"

    def test_inherits_from_clipper_error(self):
        """Test that PathSecurityError inherits from ClipperError."""
        err = PathSecurityError("Test")
        assert isinstance(err, ClipperError)


class TestExceptionRaising:
    """Test that exceptions can be raised and caught properly."""

    def test_raise_and_catch_clipper_error(self):
        """Test raising and catching ClipperError."""
        with pytest.raises(ClipperError) as exc_info:
            raise ClipperError("Test error")
        assert str(exc_info.value) == "Test error"

    def test_catch_subclass_as_base_class(self):
        """Test catching subclass as base class."""
        with pytest.raises(ClipperError) as exc_info:
            raise ConfigurationError("Missing config")
        assert isinstance(exc_info.value, ConfigurationError)

    def test_catch_capture_error_subclasses(self):
        """Test catching CaptureError subclasses."""
        with pytest.raises(CaptureError) as exc_info:
            raise ScreenshotError("Failed")
        assert isinstance(exc_info.value, ScreenshotError)

        with pytest.raises(CaptureError) as exc_info:
            raise OCRError("Failed")
        assert isinstance(exc_info.value, OCRError)

        with pytest.raises(CaptureError) as exc_info:
            raise TextCaptureError("Failed")
        assert isinstance(exc_info.value, TextCaptureError)
