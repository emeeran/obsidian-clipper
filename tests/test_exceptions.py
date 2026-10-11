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
)


class TestClipperError:
    """Tests for ClipperError base class."""

    def test_message_only(self):
        err = ClipperError("Something went wrong")
        assert err.message == "Something went wrong"
        assert err.context == {}
        assert str(err) == "Something went wrong"

    def test_with_context(self):
        err = ClipperError("Error occurred", context={"key": "value", "count": 42})
        assert "key='value'" in str(err)
        assert "count=42" in str(err)

    def test_empty_context(self):
        assert str(ClipperError("Error", context={})) == "Error"

    def test_none_context(self):
        assert str(ClipperError("Error", context=None)) == "Error"

    def test_inherits_from_exception(self):
        assert isinstance(ClipperError("Test"), Exception)


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_with_missing_keys(self):
        err = ConfigurationError("Missing config", missing_keys=["api_key", "vault_path"])
        assert err.missing_keys == ["api_key", "vault_path"]

    def test_with_context(self):
        err = ConfigurationError("Config error", missing_keys=["api_key"],
                                 context={"file": "/path/to/config"})
        assert err.context == {"file": "/path/to/config"}

    def test_inherits_from_clipper_error(self):
        assert isinstance(ConfigurationError("Test"), ClipperError)


class TestAPIConnectionError:
    """Tests for APIConnectionError."""

    def test_with_url(self):
        err = APIConnectionError("Connection failed", url="https://localhost:27123")
        assert err.url == "https://localhost:27123"
        assert err.context["url"] == "https://localhost:27123"

    def test_url_and_context(self):
        err = APIConnectionError("Failed", url="https://localhost:27123",
                                 context={"timeout": 30})
        assert err.context["timeout"] == 30


class TestAPIRequestError:
    """Tests for APIRequestError."""

    def test_with_status_code(self):
        err = APIRequestError("Not found", status_code=404)
        assert err.status_code == 404
        assert err.context["status_code"] == 404

    def test_with_response_body_truncation(self):
        err = APIRequestError("Error", response_body="x" * 500)
        assert err.response_body == "x" * 500
        assert len(err.context["response_body"]) == 200

    def test_with_all_params(self):
        err = APIRequestError("Server error", status_code=500,
                              url="https://localhost:27123/vault",
                              response_body="Internal Server Error")
        assert err.status_code == 500
        assert err.url == "https://localhost:27123/vault"


class TestCaptureError:
    """Tests for CaptureError."""

    def test_inherits_from_clipper_error(self):
        assert isinstance(CaptureError("Test"), ClipperError)


class TestScreenshotError:
    """Tests for ScreenshotError."""

    def test_with_tool_and_path(self):
        err = ScreenshotError("Tool failed", tool="grim", file_path="/tmp/capture.png",
                              context={"display": ":0"})
        assert err.tool == "grim"
        assert err.file_path == "/tmp/capture.png"
        assert err.context["display"] == ":0"

    def test_inherits_from_clipper_error(self):
        assert isinstance(ScreenshotError("Test"), ClipperError)


class TestOCRError:
    """Tests for OCRError."""

    def test_with_all_params(self):
        err = OCRError("OCR failed", file_path="/tmp/image.png", language="deu",
                        context={"tesseract_version": "5.3"})
        assert err.file_path == "/tmp/image.png"
        assert err.language == "deu"
        assert err.context["tesseract_version"] == "5.3"

    def test_inherits_from_clipper_error(self):
        assert isinstance(OCRError("Test"), ClipperError)


class TestPathSecurityError:
    """Tests for PathSecurityError."""

    def test_with_path(self):
        err = PathSecurityError("Path traversal detected", path="../../../etc/passwd")
        assert err.path == "../../../etc/passwd"
        assert err.context["path"] == "../../../etc/passwd"

    def test_inherits_from_clipper_error(self):
        assert isinstance(PathSecurityError("Test"), ClipperError)


class TestExceptionRaising:
    """Test that exceptions can be raised and caught properly."""

    def test_catch_subclass_as_base_class(self):
        with pytest.raises(ClipperError) as exc_info:
            raise ConfigurationError("Missing config")
        assert isinstance(exc_info.value, ConfigurationError)

    def test_catch_screenshot_and_ocr_as_clipper_error(self):
        with pytest.raises(ClipperError) as exc_info:
            raise ScreenshotError("Failed")
        assert isinstance(exc_info.value, ScreenshotError)

        with pytest.raises(ClipperError) as exc_info:
            raise OCRError("Failed")
        assert isinstance(exc_info.value, OCRError)
