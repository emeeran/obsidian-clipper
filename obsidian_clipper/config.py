"""Configuration management for Obsidian Clipper.

Supports configuration via:
1. Environment variables (highest priority)
2. .env file
3. Default values
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


@dataclass
class Config:
    """Configuration settings for Obsidian Clipper.

    Attributes:
        api_key: Obsidian Local REST API key
        base_url: Base URL for the Obsidian Local REST API
        default_note: Default note path for captures (relative to vault root)
        attachment_dir: Directory for attachments (relative to vault root)
        verify_ssl: Whether to verify SSL certificates
        timeout: API request timeout in seconds
        ocr_language: Default language for OCR
    """

    api_key: str = ""
    base_url: str = "https://127.0.0.1:27124"
    default_note: str = "00-Inbox/Quick Captures.md"
    attachment_dir: str = "Attachments/"
    verify_ssl: bool = True
    timeout: int = 10
    ocr_language: str = "eng"

    # Internal cache
    _headers: dict = field(default_factory=dict, repr=False)
    _loaded: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        """Load configuration from environment after initialization."""
        if not self._loaded:
            self.load()

    def load(self, env_file: str | Path | None = None) -> None:
        """Load configuration from environment variables and .env file.

        Args:
            env_file: Optional path to .env file. If None, looks for .env in
                      current directory and parent directories.
        """
        # Load .env file if available
        if HAS_DOTENV:
            if env_file:
                load_dotenv(env_file)
            else:
                load_dotenv()

        # Override with environment variables
        self.api_key = os.getenv("OBSIDIAN_API_KEY", self.api_key)
        self.base_url = os.getenv("OBSIDIAN_BASE_URL", self.base_url)
        self.default_note = os.getenv("OBSIDIAN_DEFAULT_NOTE", self.default_note)
        self.attachment_dir = os.getenv("OBSIDIAN_ATTACHMENT_DIR", self.attachment_dir)
        self.verify_ssl = (
            os.getenv("OBSIDIAN_VERIFY_SSL", str(self.verify_ssl)).lower() == "true"
        )
        self.timeout = int(os.getenv("OBSIDIAN_TIMEOUT", str(self.timeout)))
        raw_ocr_language = os.getenv("OBSIDIAN_OCR_LANGUAGE", self.ocr_language)
        self.ocr_language = self._normalize_ocr_language(raw_ocr_language)

        self._loaded = True
        self._headers = {}

    @staticmethod
    def _normalize_ocr_language(value: str) -> str:
        """Normalize OCR language string for Tesseract.

        Supports comma/space/plus separated values and returns Tesseract-compatible
        format using `+` as separator, e.g. `eng, tam` -> `eng+tam`.
        """
        if not value:
            return "eng"

        tokens = [
            token.strip() for token in re.split(r"[,+\s]+", value) if token.strip()
        ]
        if not tokens:
            return "eng"

        return "+".join(tokens)

    @property
    def headers(self) -> dict[str, str]:
        """Return headers for API requests."""
        if not self._headers:
            self._headers = {"Authorization": f"Bearer {self.api_key}"}
        return self._headers

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors.

        Returns:
            List of error messages. Empty list if valid.
        """
        errors = []

        if not self.api_key:
            errors.append(
                "API key is required. Set OBSIDIAN_API_KEY environment variable."
            )

        if not self.base_url:
            errors.append(
                "Base URL is required. Set OBSIDIAN_BASE_URL environment variable."
            )

        if not self.default_note:
            errors.append("Default note path is required.")

        if self.timeout <= 0:
            errors.append("Timeout must be a positive integer.")

        return errors

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0


# Global config instance
_config: Config | None = None


def get_config(reload: bool = False) -> Config:
    """Get the global configuration instance.

    Args:
        reload: Force reload of configuration from environment.

    Returns:
        Config instance.
    """
    global _config
    if _config is None or reload:
        _config = Config()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance.

    Args:
        config: Config instance to use globally.
    """
    global _config
    _config = config
