"""CLI module for Obsidian Clipper."""

from .args import parse_args, setup_logging
from .main import main

__all__ = ["main", "parse_args", "setup_logging"]
