"""Structured logging utilities for production environments."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

# Sensitive keys to filter from logs
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "authorization",
        "auth",
        "credential",
        "private_key",
        "access_token",
        "refresh_token",
    }
)


def _redact_sensitive(value: Any, depth: int = 0) -> Any:
    """Recursively redact sensitive values from data structures.

    Args:
        value: Value to potentially redact.
        depth: Current recursion depth to prevent infinite loops.

    Returns:
        Redacted value with sensitive data masked.
    """
    if depth > 10:  # Prevent infinite recursion
        return "..."

    if isinstance(value, dict):
        return {
            k: (
                "***REDACTED***"
                if k.lower() in SENSITIVE_KEYS
                else _redact_sensitive(v, depth + 1)
            )
            for k, v in value.items()
        }
    elif isinstance(value, (list, tuple)):
        return type(value)(_redact_sensitive(item, depth + 1) for item in value)
    return value


class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging.

    Outputs log records as JSON objects suitable for log aggregation
    systems like Elasticsearch, Splunk, or CloudWatch.
    """

    def __init__(self, include_extra: bool = True) -> None:
        """Initialize JSON formatter.

        Args:
            include_extra: Whether to include extra fields from log records.
        """
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format.

        Returns:
            JSON-formatted log string.
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields (excluding standard LogRecord attributes)
        if self.include_extra:
            standard_attrs = {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "message",
                "asctime",
            }
            extra = {
                k: v
                for k, v in record.__dict__.items()
                if k not in standard_attrs and not k.startswith("_")
            }
            if extra:
                log_data["extra"] = _redact_sensitive(extra)

        return json.dumps(log_data, default=str, ensure_ascii=False)


class HumanFormatter(logging.Formatter):
    """Human-readable log formatter with colors for terminal output."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True) -> None:
        """Initialize human formatter.

        Args:
            use_colors: Whether to use ANSI colors in output.
        """
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.use_colors = use_colors and self._supports_color()

    @staticmethod
    def _supports_color() -> bool:
        """Check if terminal supports colors."""
        # Check for NO_COLOR environment variable
        if os.environ.get("NO_COLOR"):
            return False

        # Check if stdout is a terminal
        if not hasattr(sys.stdout, "isatty"):
            return False

        if not sys.stdout.isatty():
            return False

        # Check for TERM variable
        term = os.environ.get("TERM", "")
        return term != "dumb"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with optional colors.

        Args:
            record: Log record to format.

        Returns:
            Formatted log string.
        """
        if self.use_colors:
            color = self.COLORS.get(record.levelname, "")
            record.levelname = f"{color}{record.levelname:<8}{self.RESET}"

        return super().format(record)


def setup_logging(
    level: str | int = "INFO",
    log_file: Path | str | None = None,
    json_format: bool = False,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional path to log file for rotation.
        json_format: Use JSON format for structured logging.
        max_bytes: Maximum size of each log file before rotation.
        backup_count: Number of backup files to keep.
    """
    # Get root logger for the package
    logger = logging.getLogger("obsidian_clipper")

    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if json_format or os.environ.get("LOG_FORMAT", "").lower() == "json":
        console_handler.setFormatter(JsonFormatter())
    else:
        console_handler.setFormatter(HumanFormatter())

    logger.addHandler(console_handler)

    # File handler with rotation (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)

        # Always use JSON format for file logging (better for log aggregation)
        file_handler.setFormatter(JsonFormatter())

        logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(f"obsidian_clipper.{name}")


class LogContext:
    """Context manager for adding temporary context to log messages.

    Example:
        with LogContext(user_id="123", operation="capture"):
            logger.info("Processing capture")
    """

    _context: dict[str, Any] = {}

    def __init__(self, **kwargs: Any) -> None:
        """Initialize log context with key-value pairs.

        Args:
            **kwargs: Key-value pairs to add to logging context.
        """
        self._new_context = kwargs
        self._old_context: dict[str, Any] = {}

    def __enter__(self) -> LogContext:
        """Enter context, adding new fields."""
        self._old_context = LogContext._context.copy()
        LogContext._context.update(self._new_context)
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit context, restoring previous fields."""
        LogContext._context = self._old_context

    @classmethod
    def get_context(cls) -> dict[str, Any]:
        """Get current logging context."""
        return cls._context.copy()


class ContextFilter(logging.Filter):
    """Logging filter that adds context to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record.

        Args:
            record: Log record to augment.

        Returns:
            Always True (allows all records through).
        """
        for key, value in LogContext.get_context().items():
            setattr(record, key, value)
        return True
