"""Tests for Obsidian API client."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from obsidian_clipper.config import Config
from obsidian_clipper.exceptions import (
    PathSecurityError,
)
from obsidian_clipper.obsidian import ObsidianClient, validate_path


class TestValidatePath:
    """Tests for path validation."""

    def test_validate_path_normal(self):
        """Test normal path passes validation."""
        assert validate_path("Notes/Journal.md") == "Notes/Journal.md"

    def test_validate_path_removes_leading_slash(self):
        """Test leading slash is removed."""
        assert validate_path("/Notes/Journal.md") == "Notes/Journal.md"

    def test_validate_path_traversal_parent(self):
        """Test path traversal with .. is blocked."""
        with pytest.raises(PathSecurityError):
            validate_path("../secrets.txt")

    def test_validate_path_traversal_absolute(self):
        """Test absolute path with traversal is blocked."""
        # Leading slash is stripped, so /etc/passwd becomes etc/passwd which is valid
        # But paths with .. should be blocked
        with pytest.raises(PathSecurityError):
            validate_path("/../../../etc/passwd")

    def test_validate_path_windows_drive(self):
        """Test Windows drive letter is blocked."""
        with pytest.raises(PathSecurityError):
            validate_path("C:\\Windows\\System32")


class TestObsidianClient:
    """Tests for ObsidianClient class."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return Config(
            api_key="test-key",
            base_url="https://127.0.0.1:27124",
            verify_ssl=False,
            timeout=5,
        )

    @pytest.fixture
    def client(self, config):
        """Create test client."""
        return ObsidianClient(config)

    def test_client_initialization(self, config):
        """Test client initializes correctly."""
        client = ObsidianClient(config)
        assert client.config == config

    def test_build_url(self, client):
        """Test URL building."""
        url = client._build_url("Notes/Test.md")
        assert "127.0.0.1:27124" in url
        assert "/vault/Notes/Test.md" in url

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_check_connection_success(self, mock_session, client):
        """Test successful connection check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session_instance = MagicMock()
        mock_session_instance.request.return_value = mock_response
        mock_session.return_value = mock_session_instance

        result = client.check_connection()
        assert result is True

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_check_connection_failure(self, mock_session, client):
        """Test failed connection check."""
        mock_session_instance = MagicMock()
        mock_session_instance.request.side_effect = (
            requests.exceptions.ConnectionError()
        )
        mock_session.return_value = mock_session_instance

        result = client.check_connection()
        assert result is False

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_note_exists_true(self, mock_session, client):
        """Test note exists check returns True."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.return_value.request.return_value = mock_response

        result = client.note_exists("Notes/Test.md")
        assert result is True

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_note_exists_false(self, mock_session, client):
        """Test note exists check returns False."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.return_value.request.return_value = mock_response

        result = client.note_exists("Notes/Nonexistent.md")
        assert result is False

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_append_to_note_success(self, mock_session, client):
        """Test successful note append."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.return_value.request.return_value = mock_response

        result = client.append_to_note("Notes/Test.md", "New content")
        assert result is True

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_append_to_note_failure(self, mock_session, client):
        """Test failed note append."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_session.return_value.request.return_value = mock_response

        result = client.append_to_note("Notes/Test.md", "New content")
        assert result is False

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_ensure_note_exists_already_exists(self, mock_session, client):
        """Test ensure_note_exists when note exists."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.return_value.request.return_value = mock_response

        result = client.ensure_note_exists("Notes/Test.md")
        assert result is True

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_ensure_note_exists_creates(self, mock_session, client):
        """Test ensure_note_exists creates note when missing."""
        # First call (GET) returns 404, second call (PUT) returns 201
        mock_get = Mock()
        mock_get.status_code = 404
        mock_put = Mock()
        mock_put.status_code = 201

        mock_session.return_value.request.side_effect = [mock_get, mock_put]

        result = client.ensure_note_exists("Notes/New.md")
        assert result is True

    def test_context_manager(self, config):
        """Test context manager usage."""
        with ObsidianClient(config) as client:
            assert client is not None
        # Session should be closed

    def test_close(self, client):
        """Test explicit close."""
        # Initialize session
        client._get_session()
        assert client._session is not None

        client.close()
        assert client._session is None
