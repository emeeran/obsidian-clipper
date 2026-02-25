"""Tests for configuration module."""

from __future__ import annotations

import os
from unittest.mock import patch

from obsidian_clipper.config import Config, get_config, set_config


class TestConfig:
    """Tests for Config class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = Config.__new__(Config)
        config._loaded = False
        # Don't call __post_init__ to avoid loading from env

        assert config.base_url == "https://127.0.0.1:27124"
        assert config.default_note == "00-Inbox/Quick Captures.md"
        assert config.attachment_dir == "Attachments/"
        assert config.verify_ssl is True
        assert config.timeout == 10
        assert config.ocr_language == "eng"

    def test_headers_property(self):
        """Test headers are generated correctly."""
        config = Config.__new__(Config)
        config._loaded = False
        config.api_key = "test-api-key"
        config._headers = {}

        headers = config.headers
        assert headers["Authorization"] == "Bearer test-api-key"

    def test_headers_cached(self):
        """Test headers are cached."""
        config = Config.__new__(Config)
        config._loaded = False
        config.api_key = "test-key"
        config._headers = {}

        headers1 = config.headers
        headers2 = config.headers
        assert headers1 is headers2

    def test_validate_missing_api_key(self):
        """Test validation fails without API key."""
        config = Config.__new__(Config)
        config._loaded = False
        config.api_key = ""
        config.base_url = "https://127.0.0.1:27124"
        config.default_note = "Notes.md"
        config.timeout = 10

        errors = config.validate()
        assert len(errors) == 1
        assert "API key" in errors[0]

    def test_validate_missing_base_url(self):
        """Test validation fails without base URL."""
        config = Config.__new__(Config)
        config._loaded = False
        config.api_key = "test-key"
        config.base_url = ""
        config.default_note = "Notes.md"
        config.timeout = 10

        errors = config.validate()
        assert len(errors) == 1
        assert "Base URL" in errors[0]

    def test_validate_invalid_timeout(self):
        """Test validation fails with invalid timeout."""
        config = Config.__new__(Config)
        config._loaded = False
        config.api_key = "test-key"
        config.base_url = "https://127.0.0.1:27124"
        config.default_note = "Notes.md"
        config.timeout = 0

        errors = config.validate()
        assert len(errors) == 1
        assert "Timeout" in errors[0]

    def test_validate_valid(self):
        """Test validation passes with valid config."""
        config = Config.__new__(Config)
        config._loaded = False
        config.api_key = "test-key"
        config.base_url = "https://127.0.0.1:27124"
        config.default_note = "Notes.md"
        config.timeout = 10

        errors = config.validate()
        assert len(errors) == 0
        assert config.is_valid()

    @patch.dict(os.environ, {"OBSIDIAN_API_KEY": "env-key"})
    def test_load_from_environment(self):
        """Test loading API key from environment."""
        config = Config.__new__(Config)
        config.api_key = ""
        config._loaded = False

        config.load()

        assert config.api_key == "env-key"

    @patch.dict(
        os.environ,
        {
            "OBSIDIAN_API_KEY": "key",
            "OBSIDIAN_BASE_URL": "https://example.com",
            "OBSIDIAN_DEFAULT_NOTE": "Custom/Note.md",
            "OBSIDIAN_VERIFY_SSL": "true",
            "OBSIDIAN_TIMEOUT": "30",
        },
    )
    def test_load_all_from_environment(self):
        """Test loading all config from environment."""
        config = Config.__new__(Config)
        config._loaded = False
        config.load()

        assert config.api_key == "key"
        assert config.base_url == "https://example.com"
        assert config.default_note == "Custom/Note.md"
        assert config.verify_ssl is True
        assert config.timeout == 30

    @patch.dict(os.environ, {"OBSIDIAN_OCR_LANGUAGE": "eng, tam"})
    def test_load_ocr_language_comma_separated(self):
        """Test OCR language normalization from comma-separated env value."""
        config = Config.__new__(Config)
        config._loaded = False
        config.load()

        assert config.ocr_language == "eng+tam"

    @patch.dict(os.environ, {"OBSIDIAN_OCR_LANGUAGE": "eng tam"})
    def test_load_ocr_language_space_separated(self):
        """Test OCR language normalization from space-separated env value."""
        config = Config.__new__(Config)
        config._loaded = False
        config.load()

        assert config.ocr_language == "eng+tam"


class TestGlobalConfig:
    """Tests for global config functions."""

    def test_get_config_singleton(self):
        """Test get_config returns same instance."""
        # Reset global config
        import obsidian_clipper.config as config_module

        config_module._config = None

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_get_config_reload(self):
        """Test get_config with reload creates new instance."""
        import obsidian_clipper.config as config_module

        config_module._config = None

        config1 = get_config()
        config2 = get_config(reload=True)

        assert config1 is not config2

    def test_set_config(self):
        """Test set_config updates global config."""
        import obsidian_clipper.config as config_module

        config_module._config = None

        custom_config = Config.__new__(Config)
        custom_config.api_key = "custom"
        custom_config._loaded = False

        set_config(custom_config)
        retrieved = get_config()

        assert retrieved is custom_config
