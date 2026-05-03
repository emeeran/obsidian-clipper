"""Tests for logging utilities."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from obsidian_clipper.utils.logging import (
    ContextFilter,
    HumanFormatter,
    JsonFormatter,
    LogContext,
    _redact_sensitive,
    get_logger,
    setup_logging,
)


class TestRedactSensitive:
    """Tests for _redact_sensitive function."""

    def test_redacts_api_key(self):
        result = _redact_sensitive({"api_key": "secret123"})
        assert result["api_key"] == "***REDACTED***"

    def test_redacts_password(self):
        result = _redact_sensitive({"password": "mypass"})
        assert result["password"] == "***REDACTED***"

    def test_redacts_authorization(self):
        result = _redact_sensitive({"authorization": "Bearer token"})
        assert result["authorization"] == "***REDACTED***"

    def test_redacts_case_insensitive(self):
        result = _redact_sensitive({"API_KEY": "secret"})
        assert result["API_KEY"] == "***REDACTED***"

    def test_preserves_non_sensitive(self):
        data = {"username": "alice", "port": 8080}
        result = _redact_sensitive(data)
        assert result["username"] == "alice"
        assert result["port"] == 8080

    def test_redacts_nested(self):
        data = {"config": {"api_key": "secret", "name": "test"}}
        result = _redact_sensitive(data)
        assert result["config"]["api_key"] == "***REDACTED***"
        assert result["config"]["name"] == "test"

    def test_redacts_in_list(self):
        data = [{"api_key": "a"}, {"password": "b"}]
        result = _redact_sensitive(data)
        assert result[0]["api_key"] == "***REDACTED***"
        assert result[1]["password"] == "***REDACTED***"

    def test_depth_limit(self):
        nested = {"a": 1}
        for _ in range(12):
            nested = {"a": nested}
        result = _redact_sensitive(nested)
        # At depth > 10, recursion stops and returns "..."
        assert isinstance(result, dict)


class TestJsonFormatter:
    """Tests for JsonFormatter class."""

    def test_formats_as_json(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["message"] == "Test message"
        assert data["level"] == "INFO"
        assert data["logger"] == "test"

    def test_includes_exception_info(self):
        formatter = JsonFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Error",
                args=None,
                exc_info=exc_info,
            )
        output = formatter.format(record)
        data = json.loads(output)
        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["message"] == "test error"

    def test_includes_extra_fields(self):
        formatter = JsonFormatter(include_extra=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=None,
            exc_info=None,
        )
        record.custom_field = "custom_value"  # type: ignore[attr-defined]
        output = formatter.format(record)
        data = json.loads(output)
        assert data["extra"]["custom_field"] == "custom_value"

    def test_excludes_extra_when_disabled(self):
        formatter = JsonFormatter(include_extra=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=None,
            exc_info=None,
        )
        record.custom_field = "custom_value"  # type: ignore[attr-defined]
        output = formatter.format(record)
        data = json.loads(output)
        assert "extra" not in data

    def test_redacts_sensitive_extra_fields(self):
        formatter = JsonFormatter(include_extra=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=None,
            exc_info=None,
        )
        record.api_key = "super-secret-key"  # type: ignore[attr-defined]
        output = formatter.format(record)
        data = json.loads(output)
        assert data["extra"]["api_key"] == "***REDACTED***"


class TestHumanFormatter:
    """Tests for HumanFormatter class."""

    def test_formats_with_colors(self):
        formatter = HumanFormatter(use_colors=True)
        # Force color support on
        formatter.use_colors = True
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        assert "Test message" in output
        # Record should not be permanently mutated
        assert record.levelname == "INFO"

    def test_formats_without_colors(self):
        formatter = HumanFormatter(use_colors=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        assert "Test message" in output
        assert "\033[" not in output

    def test_does_not_mutate_record(self):
        """Verify ANSI codes don't leak to other handlers."""
        formatter = HumanFormatter(use_colors=True)
        formatter.use_colors = True
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=None,
            exc_info=None,
        )
        formatter.format(record)
        # After formatting, record.levelname must be the original value
        assert record.levelname == "WARNING"
        assert "\033[" not in record.levelname


class TestLogContext:
    """Tests for LogContext context manager."""

    def test_adds_context(self):
        with LogContext(user_id="123", operation="capture"):
            ctx = LogContext.get_context()
            assert ctx["user_id"] == "123"
            assert ctx["operation"] == "capture"

    def test_restores_context_on_exit(self):
        with LogContext(key="value"):
            pass
        ctx = LogContext.get_context()
        assert "key" not in ctx

    def test_nested_context(self):
        with LogContext(a="1"):
            ctx1 = LogContext.get_context()
            assert ctx1["a"] == "1"
            with LogContext(b="2"):
                ctx2 = LogContext.get_context()
                assert ctx2["a"] == "1"
                assert ctx2["b"] == "2"
            ctx3 = LogContext.get_context()
            assert ctx3["a"] == "1"
            assert "b" not in ctx3

    def test_get_context_returns_copy(self):
        with LogContext(x="y"):
            ctx = LogContext.get_context()
            ctx["z"] = "modified"
            assert "z" not in LogContext.get_context()


class TestContextFilter:
    """Tests for ContextFilter logging filter."""

    def test_adds_context_to_record(self):
        filt = ContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=None,
            exc_info=None,
        )
        with LogContext(request_id="abc"):
            result = filt.filter(record)
        assert result is True
        assert record.request_id == "abc"  # type: ignore[attr-defined]


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_configures_logger_with_console_handler(self):
        logger = logging.getLogger("obsidian_clipper")
        old_handlers = list(logger.handlers)
        try:
            setup_logging(level="INFO")
            assert logger.level == logging.INFO
            # Should have at least one handler (console)
            console_handlers = [
                h for h in logger.handlers if isinstance(h, logging.StreamHandler)
            ]
            assert len(console_handlers) >= 1
        finally:
            logger.handlers = old_handlers

    def test_configures_json_format(self, tmp_path: Path):
        logger = logging.getLogger("obsidian_clipper")
        old_handlers = list(logger.handlers)
        log_file = tmp_path / "test.log"
        try:
            setup_logging(level="DEBUG", log_file=log_file, json_format=True)
            assert any(
                isinstance(h, logging.StreamHandler) for h in logger.handlers
            )
        finally:
            logger.handlers = old_handlers

    def test_file_handler_created(self, tmp_path: Path):
        logger = logging.getLogger("obsidian_clipper")
        old_handlers = list(logger.handlers)
        log_file = tmp_path / "test.log"
        try:
            setup_logging(level="INFO", log_file=log_file)
            assert log_file.parent.exists()
            # Should have 2 handlers: console + file
            assert len(logger.handlers) >= 2
        finally:
            logger.handlers = old_handlers

    def test_clears_existing_handlers(self):
        logger = logging.getLogger("obsidian_clipper")
        old_handlers = list(logger.handlers)
        try:
            # Add a dummy handler
            logger.addHandler(logging.StreamHandler())
            setup_logging(level="INFO")
            # setup_logging clears all handlers then adds exactly 1 (console)
            assert len(logger.handlers) == 1
        finally:
            logger.handlers = old_handlers


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_named_logger(self):
        logger = get_logger("test_module")
        assert logger.name == "obsidian_clipper.test_module"
