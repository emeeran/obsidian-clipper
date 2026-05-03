"""Configuration management for Obsidian Clipper."""

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
except ImportError:
    load_dotenv = None  # type: ignore[assignment]


@dataclass
class Config:
    """Configuration settings for Obsidian Clipper."""

    api_key: str = ""
    base_url: str = "https://127.0.0.1:27124"
    default_note: str = "00-Inbox/Quick Captures.md"
    attachment_dir: str = "Attachments/"
    verify_ssl: bool = True
    timeout: int = 10
    ocr_language: str = "eng"
    _headers: dict = field(default_factory=dict, repr=False)
    _loaded: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        if not self._loaded:
            self.load()

    def load(self, env_file: str | Path | None = None) -> None:
        """Load configuration from environment variables and .env file."""
        if load_dotenv is not None:
            if env_file:
                load_dotenv(env_file)
            else:
                load_dotenv()
                config_dir = Path.home() / ".config" / "obsidian-clipper"
                standard_env = config_dir / ".env"
                if standard_env.exists():
                    load_dotenv(standard_env, override=False)

        self.api_key = os.getenv("OBSIDIAN_API_KEY", self.api_key)
        self.base_url = os.getenv("OBSIDIAN_BASE_URL", self.base_url)
        self.default_note = os.getenv("OBSIDIAN_DEFAULT_NOTE", self.default_note)
        self.attachment_dir = os.getenv("OBSIDIAN_ATTACHMENT_DIR", self.attachment_dir)
        _verify_val = os.getenv("OBSIDIAN_VERIFY_SSL")
        self.verify_ssl = (
            _verify_val.lower() == "true" if _verify_val is not None else self.verify_ssl
        )
        try:
            self.timeout = int(os.getenv("OBSIDIAN_TIMEOUT", str(self.timeout)))
        except (ValueError, TypeError):
            logger.warning("Invalid OBSIDIAN_TIMEOUT value, using default: %s", self.timeout)
        raw_ocr = os.getenv("OBSIDIAN_OCR_LANGUAGE", self.ocr_language)
        self.ocr_language = self._normalize_ocr_language(raw_ocr)

        self._loaded = True
        self._headers = {}

    @staticmethod
    def _normalize_ocr_language(value: str) -> str:
        return "+".join(t for t in re.split(r"[,+\s]+", value) if t) or "eng"

    @property
    def headers(self) -> dict[str, str]:
        if not self._headers:
            self._headers = {"Authorization": f"Bearer {self.api_key}"}
        return self._headers

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        if not self.api_key:
            errors.append("API key is required. Set OBSIDIAN_API_KEY environment variable.")
        elif len(self.api_key) < 10:
            errors.append("API key appears too short. Check your Obsidian Local REST API settings.")
        elif not re.fullmatch(r"[0-9a-fA-F]+", self.api_key):
            errors.append("API key should be a hex string. Check Obsidian Local REST API settings.")

        if not self.base_url:
            errors.append("Base URL is required.")
        elif not self.base_url.startswith(("http://", "https://")):
            errors.append(f"Base URL must start with http:// or https:// (got: {self.base_url}).")

        if not self.default_note:
            errors.append("Default note path is required.")
        if not isinstance(self.timeout, int) or self.timeout <= 0:
            errors.append(f"Timeout must be a positive integer (got: {self.timeout!r}).")
        if not self.ocr_language:
            errors.append("OCR language is required (default: 'eng').")
        return errors

    def is_valid(self) -> bool:
        return not self.validate()


# Global config singleton
_config: Config | None = None
_config_lock = threading.Lock()


def get_config(reload: bool = False) -> Config:
    global _config
    if _config is None or reload:
        with _config_lock:
            if _config is None or reload:
                _config = Config()
    return _config


def set_config(config: Config) -> None:
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
    """Get a capture profile, with optional env overrides."""
    profile = PROFILES.get(name)
    if profile is None:
        raise ValueError(f"Unknown profile '{name}'. Available: {', '.join(sorted(PROFILES))}")

    env_prefix = f"OBSIDIAN_PROFILE_{name.upper()}_"
    overrides: dict[str, str | bool | int] = {}
    for key, value in os.environ.items():
        if key.startswith(env_prefix):
            field = key[len(env_prefix):].lower()
            overrides[field] = value.lower() == "true" if value.lower() in ("true", "false") else value
    return {**profile, **overrides}


def get_vault_config(vault_name: str) -> Config:
    """Get a Config instance for a named vault."""
    prefix = f"OBSIDIAN_{vault_name.upper()}_"

    def _env(suffix: str, fallback: str) -> str:
        return os.environ.get(f"{prefix}{suffix}", os.environ.get(f"OBSIDIAN_{suffix}", fallback))

    config = Config(
        api_key=_env("API_KEY", ""),
        base_url=_env("BASE_URL", "https://127.0.0.1:27124"),
        default_note=_env("DEFAULT_NOTE", "00-Inbox/Quick Captures.md"),
        attachment_dir=_env("ATTACHMENT_DIR", "Attachments/"),
        _loaded=True,
    )
    verify_val = os.environ.get(f"{prefix}VERIFY_SSL", os.environ.get("OBSIDIAN_VERIFY_SSL"))
    config.verify_ssl = verify_val.lower() == "true" if verify_val is not None else True
    try:
        config.timeout = int(os.environ.get(f"{prefix}TIMEOUT", os.environ.get("OBSIDIAN_TIMEOUT", "10")))
    except (ValueError, TypeError):
        config.timeout = 10
    config.ocr_language = Config._normalize_ocr_language(
        os.environ.get(f"{prefix}OCR_LANGUAGE", os.environ.get("OBSIDIAN_OCR_LANGUAGE", "eng"))
    )
    return config
