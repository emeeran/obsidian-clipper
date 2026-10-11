"""Tests for logging utilities."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from obsidian_clipper.utils.logging import _JsonFormatter, get_logger, setup_logging


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_configures_logger_with_console_handler(self):
        logger = logging.getLogger("obsidian_clipper")
        old_handlers = list(logger.handlers)
        try:
            setup_logging(level="INFO")
            assert logger.level == logging.INFO
            console_handlers = [
                h for h in logger.handlers if isinstance(h, logging.StreamHandler)
            ]
            assert len(console_handlers) >= 1
        finally:
            logger.handlers = old_handlers

    def test_file_handler_created(self, tmp_path: Path):
        logger = logging.getLogger("obsidian_clipper")
        old_handlers = list(logger.handlers)
        log_file = tmp_path / "test.log"
        try:
            setup_logging(level="INFO", log_file=log_file)
            assert log_file.parent.exists()
            assert len(logger.handlers) >= 2
        finally:
            logger.handlers = old_handlers

    def test_clears_existing_handlers(self):
        logger = logging.getLogger("obsidian_clipper")
        old_handlers = list(logger.handlers)
        try:
            logger.addHandler(logging.StreamHandler())
            setup_logging(level="INFO")
            assert len(logger.handlers) == 1
        finally:
            logger.handlers = old_handlers


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_named_logger(self):
        logger = get_logger("test_module")
        assert logger.name == "obsidian_clipper.test_module"


class TestJsonFormatter:
    """Tests for the structured JSON log formatter."""

    def test_formats_record_as_json(self):
        record = logging.LogRecord(
            "obsidian_clipper.x", logging.INFO, "file.py", 1, "hello %s", ("world",), None
        )
        payload = json.loads(_JsonFormatter().format(record))

        assert payload["msg"] == "hello world"
        assert payload["level"] == "INFO"
        assert payload["logger"] == "obsidian_clipper.x"

    def test_includes_exception_info(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = logging.LogRecord(
                "obsidian_clipper.x", logging.ERROR, "file.py", 1, "failed", (), sys.exc_info()
            )
        payload = json.loads(_JsonFormatter().format(record))

        assert "exc" in payload
        assert "ValueError" in payload["exc"]

    def test_setup_logging_json_uses_json_formatter(self):
        logger = logging.getLogger("obsidian_clipper")
        old_handlers = list(logger.handlers)
        try:
            setup_logging(level="INFO", json_format=True)
            assert any(isinstance(h.formatter, _JsonFormatter) for h in logger.handlers)
        finally:
            logger.handlers = old_handlers
