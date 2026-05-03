"""Integration tests against live Obsidian Local REST API.

Run with: pytest tests/integration/test_api_integration.py -m integration

Requires OBSIDIAN_API_KEY and OBSIDIAN_BASE_URL environment variables.
"""

from __future__ import annotations

import os
import time

import pytest

from obsidian_clipper.config import Config
from obsidian_clipper.obsidian import ObsidianClient

# Skip all tests if API key is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("OBSIDIAN_API_KEY"),
    reason="OBSIDIAN_API_KEY not set — skipping integration tests",
)


@pytest.fixture
def config() -> Config:
    """Create config from environment variables."""
    return Config(
        api_key=os.environ["OBSIDIAN_API_KEY"],
        base_url=os.environ.get("OBSIDIAN_BASE_URL", "https://127.0.0.1:27124"),
        verify_ssl=os.environ.get("OBSIDIAN_VERIFY_SSL", "false").lower() == "true",
    )


@pytest.fixture
def client(config: Config) -> ObsidianClient:
    """Create API client."""
    return ObsidianClient(config)


@pytest.fixture
def test_note_path() -> str:
    """Generate unique test note path."""
    ts = int(time.time())
    return f"00-Inbox/_test_integration_{ts}.md"


@pytest.mark.integration
class TestLiveAPI:
    """Tests against live Obsidian Local REST API."""

    def test_check_connection(self, client: ObsidianClient):
        """Test connection to Obsidian API."""
        with client:
            assert client.check_connection() is True

    def test_create_and_read_note(
        self, client: ObsidianClient, test_note_path: str
    ):
        """Test creating and reading a note."""
        with client:
            content = "# Integration Test\n\nTest content."
            assert client.create_note(test_note_path, content) is True
            assert client.note_exists(test_note_path) is True

    def test_append_to_note(
        self, client: ObsidianClient, test_note_path: str
    ):
        """Test appending to a note."""
        with client:
            client.create_note(test_note_path, "# Test\n")
            assert client.append_to_note(test_note_path, "Appended line.") is True

    def test_ensure_note_exists(
        self, client: ObsidianClient, test_note_path: str
    ):
        """Test ensure_note_exists creates and caches."""
        with client:
            assert client.ensure_note_exists(test_note_path) is True
            # Second call should hit cache
            assert client.ensure_note_exists(test_note_path) is True

    def test_special_chars_in_path(
        self, client: ObsidianClient
    ):
        """Test note with special characters in path."""
        ts = int(time.time())
        path = f"00-Inbox/_test spaces_{ts}.md"
        with client:
            assert client.create_note(path, "# Special Chars") is True
            assert client.note_exists(path) is True
