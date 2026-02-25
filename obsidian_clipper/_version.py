"""Version information for Obsidian Clipper.

Single source of truth for version information used by:
- pyproject.toml (via hatchling)
- CLI --version flag
- Package metadata
"""

__version__ = "1.0.1"
__author__ = "Meeran E Mandhini"
__license__ = "MIT"
__description__ = "Capture text, screenshots, and OCR content to Obsidian via Local REST API"


def get_version() -> str:
    """Get the current version string.

    Returns:
        Version string in semantic versioning format.
    """
    return __version__


def get_version_info() -> dict[str, str]:
    """Get detailed version information.

    Returns:
        Dictionary with version details.
    """
    return {
        "version": __version__,
        "author": __author__,
        "license": __license__,
        "description": __description__,
    }
