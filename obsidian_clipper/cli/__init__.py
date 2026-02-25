"""CLI module for Obsidian Clipper."""

from .args import parse_args, setup_logging

# Import main lazily to avoid module name collision with cli.main module
def __getattr__(name: str):
    if name == "main":
        from .main import main

        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["main", "parse_args", "setup_logging"]
