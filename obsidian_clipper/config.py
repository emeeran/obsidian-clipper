"""Configuration management for Obsidian Clipper.

Supports configuration via:
1. Environment variables (highest priority)
2. .env file
3. Default values
"""

from __future__ import annotations

import logging
import os
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

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
            env_file: Optional path to .env file. If None, looks for .env in:
                      1. Current directory
                      2. ~/.config/obsidian-clipper/.env
        """
        # Define standard config paths
        config_dir = Path.home() / ".config" / "obsidian-clipper"
        standard_env = config_dir / ".env"

        # Load .env file if available
        if HAS_DOTENV:
            # 1. Try provided path
            if env_file:
                load_dotenv(env_file)
            else:
                # 2. Try current directory
                load_dotenv()
                # 3. Try standard config path if current dir didn't have it
                if standard_env.exists():
                    load_dotenv(standard_env, override=False)

        # Override with environment variables
        self.api_key = os.getenv("OBSIDIAN_API_KEY", self.api_key)
        self.base_url = os.getenv("OBSIDIAN_BASE_URL", self.base_url)
        self.default_note = os.getenv("OBSIDIAN_DEFAULT_NOTE", self.default_note)
        self.attachment_dir = os.getenv("OBSIDIAN_ATTACHMENT_DIR", self.attachment_dir)
        self.verify_ssl = (
            os.getenv("OBSIDIAN_VERIFY_SSL").lower() == "true"
            if os.getenv("OBSIDIAN_VERIFY_SSL") is not None
            else self.verify_ssl
        )
        try:
            self.timeout = int(os.getenv("OBSIDIAN_TIMEOUT", str(self.timeout)))
        except (ValueError, TypeError):
            logger.warning("Invalid OBSIDIAN_TIMEOUT value, using default: %s", self.timeout)
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
                "API key is required. Set OBSIDIAN_API_KEY environment variable "
                "or run `obsidian-clipper --config-ui`."
            )
        elif len(self.api_key) < 10:
            errors.append(
                "API key appears too short. Check your Obsidian Local REST API settings."
            )

        if not self.base_url:
            errors.append(
                "Base URL is required. Set OBSIDIAN_BASE_URL environment variable."
            )
        elif not self.base_url.startswith(("http://", "https://")):
            errors.append(
                f"Base URL must start with http:// or https:// (got: {self.base_url}). "
                "Typical value: http://127.0.0.1:27124"
            )

        if not self.default_note:
            errors.append("Default note path is required.")

        if not isinstance(self.timeout, int) or self.timeout <= 0:
            errors.append(
                f"Timeout must be a positive integer (got: {self.timeout!r}). "
                "Set OBSIDIAN_TIMEOUT to a number like 10."
            )

        if not self.ocr_language:
            errors.append("OCR language is required (default: 'eng').")

        return errors

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0


# Global config instance with thread-safe access

_config: Config | None = None
_config_lock = threading.Lock()


def get_config(reload: bool = False) -> Config:
    """Get the global configuration instance.

    Args:
        reload: Force reload of configuration from environment.

    Returns:
        Config instance.
    """
    global _config
    if _config is None or reload:
        with _config_lock:
            # Double-check after acquiring lock
            if _config is None or reload:
                _config = Config()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance.

    Args:
        config: Config instance to use globally.
    """
    global _config
    with _config_lock:
        _config = config


# --- Capture Profiles ---

PROFILES: dict[str, dict[str, str | bool | int]] = {
    "research": {
        "tags": "research,reading",
        "note": "00-Inbox/Research Note.md",
        "ocr": True,
        "append": True,
    },
    "quick": {
        "tags": "quick-capture",
        "note": "00-Inbox/",
        "ocr": False,
    },
    "code": {
        "tags": "code,snippet",
        "note": "Code Snippets/",
        "ocr": False,
    },
    "web": {
        "tags": "web,article",
        "note": "Web Clippings/",
        "ocr": True,
    },
}


def get_profile(name: str) -> dict[str, str | bool | int]:
    """Get a capture profile by name.

    Profiles can be overridden via OBSIDIAN_PROFILE_<NAME>_<KEY>
    environment variables, e.g. OBSIDIAN_PROFILE_RESEARCH_TAGS=research,papers.

    Args:
        name: Profile name (e.g., 'research', 'quick').

    Returns:
        Profile dict with keys like 'tags', 'note', 'ocr'.

    Raises:
        ValueError: If profile name is not found.
    """
    profile = PROFILES.get(name)
    if profile is None:
        available = ", ".join(sorted(PROFILES))
        raise ValueError(f"Unknown profile '{name}'. Available: {available}")

    # Allow env overrides: OBSIDIAN_PROFILE_<NAME>_<KEY>
    env_prefix = f"OBSIDIAN_PROFILE_{name.upper()}_"
    overrides: dict[str, str | bool | int] = {}
    for key, value in os.environ.items():
        if key.startswith(env_prefix):
            field = key[len(env_prefix) :].lower()
            if value.lower() in ("true", "false"):
                overrides[field] = value.lower() == "true"
            else:
                overrides[field] = value

    return {**profile, **overrides}


def get_vault_config(vault_name: str) -> Config:
    """Get a Config instance for a named vault.

    Reads OBSIDIAN_<VAULTNAME>_API_KEY, OBSIDIAN_<VAULTNAME>_BASE_URL, etc.
    Falls back to default OBSIDIAN_* vars for any unset fields.

    Args:
        vault_name: Vault identifier (e.g., 'work', 'personal').

    Returns:
        Config instance with vault-specific values.
    """
    prefix = f"OBSIDIAN_{vault_name.upper()}_"

    def _env(suffix: str, fallback: str) -> str:
        return os.environ.get(f"{prefix}{suffix}", os.environ.get(f"OBSIDIAN_{suffix}", fallback))

    config = Config.__new__(Config)
    config._loaded = False
    config._headers = {}
    config.api_key = _env("API_KEY", "")
    config.base_url = _env("BASE_URL", "https://127.0.0.1:27124")
    config.default_note = _env("DEFAULT_NOTE", "00-Inbox/Quick Captures.md")
    config.attachment_dir = _env("ATTACHMENT_DIR", "Attachments/")

    verify_val = os.environ.get(f"{prefix}VERIFY_SSL", os.environ.get("OBSIDIAN_VERIFY_SSL"))
    config.verify_ssl = verify_val.lower() == "true" if verify_val is not None else True

    timeout_val = os.environ.get(f"{prefix}TIMEOUT", os.environ.get("OBSIDIAN_TIMEOUT", "10"))
    try:
        config.timeout = int(timeout_val)
    except (ValueError, TypeError):
        config.timeout = 10

    ocr_val = os.environ.get(f"{prefix}OCR_LANGUAGE", os.environ.get("OBSIDIAN_OCR_LANGUAGE", "eng"))
    config.ocr_language = Config._normalize_ocr_language(ocr_val)

    config._loaded = True
    return config
