"""Main CLI entry point for Obsidian Clipper.

This module provides backward compatibility by re-exporting from
the new modular structure. New code should import directly from:
- obsidian_clipper.cli for CLI functions
- obsidian_clipper.workflow for workflow functions
"""

from __future__ import annotations

# Re-export for backward compatibility
from .cli import main, parse_args, setup_logging
from .cli.main import validate_config
from .workflow import CaptureSession, prepare_capture_session, process_and_save_content

__all__ = [
    "CaptureSession",
    "main",
    "parse_args",
    "prepare_capture_session",
    "process_and_save_content",
    "setup_logging",
    "validate_config",
]
