"""Logging utilities for Obsidian Clipper."""

from __future__ import annotations

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ANSI color codes
_COLORS = {
    "DEBUG": "\033[36m",     # Cyan
    "INFO": "\033[32m",      # Green
    "WARNING": "\033[33m",   # Yellow
    "ERROR": "\033[31m",     # Red
    "CRITICAL": "\033[1;31m",  # Bold Red
}
_RESET = "\033[0m"


class _ColoredFormatter(logging.Formatter):
    """Simple colored formatter for console output."""

    def __init__(self, fmt: str, use_colors: bool = True):
        super().__init__(fmt)
        self.use_colors = use_colors and sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        if self.use_colors:
            color = _COLORS.get(record.levelname, "")
            saved = record.levelname
            record.levelname = f"{color}{record.levelname:<8}{_RESET}"
            try:
                return super().format(record)
            finally:
                record.levelname = saved
        return super().format(record)


class _JsonFormatter(logging.Formatter):
    """Minimal JSON formatter for structured/parseable logs.

    Emits one JSON object per line: ts, level, logger, msg (+ exc on errors).
    Uses only the stdlib so no extra dependency is required.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(
    level: str | int = "INFO",
    log_file: Path | str | None = None,
    json_format: bool = False,
) -> None:
    """Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional path to log file with rotation.
        json_format: If True, emit structured JSON log lines.
    """
    logger = logging.getLogger("obsidian_clipper")
    logger.setLevel(level if isinstance(level, int) else getattr(logging, level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    if json_format:
        console_formatter: logging.Formatter = _JsonFormatter()
        file_formatter: logging.Formatter = console_formatter
    else:
        console_formatter = _ColoredFormatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )

    # Console handler
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(console_formatter)
    logger.addHandler(console)

    # Optional file handler with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path, maxBytes=5 * 1024 * 1024, backupCount=3
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger under the obsidian_clipper namespace."""
    return logging.getLogger(f"obsidian_clipper.{name}")
