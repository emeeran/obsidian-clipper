"""Tests for Obsidian API client."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from obsidian_clipper.config import Config
from obsidian_clipper.exceptions import (
    APIConnectionError,
    APIRequestError,
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

    def test_validate_path_removes_multiple_leading_slashes(self):
        """Test multiple leading slashes are removed."""
        assert validate_path("///Notes/Journal.md") == "Notes/Journal.md"

    def test_validate_path_empty(self):
        """Test empty path returns empty string."""
        assert validate_path("") == ""

    def test_validate_path_only_slashes(self):
        """Test path with only slashes returns empty string."""
        assert validate_path("///") == ""

    def test_validate_path_normalizes_backslashes(self):
        """Test backslashes are converted to forward slashes."""
        assert validate_path("Notes\\Journal.md") == "Notes/Journal.md"

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

    def test_validate_path_windows_drive_forward_slash(self):
        """Test Windows drive letter with forward slash is blocked."""
        with pytest.raises(PathSecurityError):
            validate_path("C:/Windows/System32")

    def test_validate_path_traversal_in_middle(self):
        """Test path traversal in middle of path is blocked."""
        with pytest.raises(PathSecurityError):
            validate_path("Notes/../secrets.txt")


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

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_execute_request_timeout(self, mock_session, client):
        """Test _execute_request raises APIRequestError on timeout."""
        mock_session_instance = MagicMock()
        mock_session_instance.request.side_effect = requests.exceptions.Timeout()
        mock_session.return_value = mock_session_instance

        with pytest.raises(APIRequestError) as exc_info:
            client._execute_request("GET", "https://test.com")
        assert "timed out" in str(exc_info.value).lower()

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_execute_request_general_error(self, mock_session, client):
        """Test _execute_request raises APIRequestError on general error."""
        mock_session_instance = MagicMock()
        mock_session_instance.request.side_effect = (
            requests.exceptions.RequestException("Network error")
        )
        mock_session.return_value = mock_session_instance

        with pytest.raises(APIRequestError) as exc_info:
            client._execute_request("GET", "https://test.com")
        assert "failed" in str(exc_info.value).lower()

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_note_exists_exception(self, mock_session, client):
        """Test note_exists returns False on exception."""
        mock_session_instance = MagicMock()
        mock_session_instance.request.side_effect = (
            requests.exceptions.ConnectionError()
        )
        mock_session.return_value = mock_session_instance

        result = client.note_exists("Notes/Test.md")
        assert result is False

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_ensure_note_exists_exception(self, mock_session, client):
        """Test ensure_note_exists returns False on exception."""
        mock_session_instance = MagicMock()
        mock_session_instance.request.side_effect = (
            requests.exceptions.ConnectionError()
        )
        mock_session.return_value = mock_session_instance

        result = client.ensure_note_exists("Notes/Test.md")
        assert result is False

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_ensure_note_exists_create_fails(self, mock_session, client):
        """Test ensure_note_exists returns False when create returns error."""
        mock_get = Mock()
        mock_get.status_code = 404
        mock_put = Mock()
        mock_put.status_code = 500

        mock_session.return_value.request.side_effect = [mock_get, mock_put]

        result = client.ensure_note_exists("Notes/New.md")
        assert result is False

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_ensure_note_exists_unexpected_status(self, mock_session, client):
        """Test ensure_note_exists returns False on unexpected status."""
        mock_response = Mock()
        mock_response.status_code = 403  # Forbidden

        mock_session.return_value.request.return_value = mock_response

        result = client.ensure_note_exists("Notes/Test.md")
        assert result is False

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_append_to_note_exception(self, mock_session, client):
        """Test append_to_note returns False on exception."""
        mock_session_instance = MagicMock()
        mock_session_instance.request.side_effect = (
            requests.exceptions.ConnectionError()
        )
        mock_session.return_value = mock_session_instance

        result = client.append_to_note("Notes/Test.md", "Content")
        assert result is False

    def test_upload_image_file_not_found(self, client):
        """Test upload_image returns False when file doesn't exist."""
        result = client.upload_image("/nonexistent/path/image.png")
        assert result is False

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_upload_image_success(self, mock_session, client):
        """Test successful image upload."""
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n")  # PNG header
            temp_path = f.name

        try:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_session.return_value.request.return_value = mock_response

            result = client.upload_image(temp_path)
            assert result is True
        finally:
            Path(temp_path).unlink()

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_upload_image_with_custom_dest(self, mock_session, client):
        """Test image upload with custom destination."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n")
            temp_path = f.name

        try:
            mock_response = Mock()
            mock_response.status_code = 201
            mock_session.return_value.request.return_value = mock_response

            result = client.upload_image(
                temp_path,
                dest_filename="custom.png",
                dest_dir="attachments/",
            )
            assert result is True
        finally:
            Path(temp_path).unlink()

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_upload_image_failure(self, mock_session, client):
        """Test upload_image returns False on API failure."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n")
            temp_path = f.name

        try:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_session.return_value.request.return_value = mock_response

            result = client.upload_image(temp_path)
            assert result is False
        finally:
            Path(temp_path).unlink()

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_upload_image_connection_error(self, mock_session, client):
        """Test upload_image returns False on connection error."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n")
            temp_path = f.name

        try:
            mock_session_instance = MagicMock()
            mock_session_instance.request.side_effect = (
                requests.exceptions.ConnectionError()
            )
            mock_session.return_value = mock_session_instance

            result = client.upload_image(temp_path)
            assert result is False
        finally:
            Path(temp_path).unlink()

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_upload_image_os_error(self, mock_session, client):
        """Test upload_image returns False on OS error reading file."""
        # Create a mock that will fail when trying to read
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(b"\x89PNG\r\n\x1a\n")
                temp_path = f.name

            try:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_session.return_value.request.return_value = mock_response

                result = client.upload_image(temp_path)
                assert result is False
            finally:
                Path(temp_path).unlink()

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_get_session_configures_pooling(self, mock_session, client):
        """Test _get_session configures connection pooling."""
        mock_adapter = MagicMock()
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        with patch("obsidian_clipper.obsidian.api.HTTPAdapter") as mock_http_adapter:
            mock_http_adapter.return_value = mock_adapter
            session = client._get_session()

            # Verify HTTPAdapter was called with pooling config
            mock_http_adapter.assert_called_once()
            call_kwargs = mock_http_adapter.call_args[1]
            assert call_kwargs["pool_connections"] == 10
            assert call_kwargs["pool_maxsize"] == 20

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_get_session_adds_keep_alive(self, mock_session, client):
        """Test _get_session adds keep-alive header."""
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        session = client._get_session()

        # Verify keep-alive header was added
        mock_session_instance.headers.update.assert_called()
        calls = mock_session_instance.headers.update.call_args_list
        # Check if any call included Connection: keep-alive
        found = False
        for call in calls:
            if "Connection" in call[0][0] and call[0][0]["Connection"] == "keep-alive":
                found = True
                break
        assert found

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_check_connection_404(self, mock_session, client):
        """Test check_connection returns True on 404."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session_instance = MagicMock()
        mock_session_instance.request.return_value = mock_response
        mock_session.return_value = mock_session_instance

        result = client.check_connection()
        assert result is True

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_check_connection_api_error(self, mock_session, client):
        """Test check_connection returns False on APIRequestError."""
        mock_session_instance = MagicMock()
        mock_session_instance.request.side_effect = requests.exceptions.Timeout()
        mock_session.return_value = mock_session_instance

        result = client.check_connection()
        assert result is False

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_append_to_note_created(self, mock_session, client):
        """Test append_to_note returns True on 201."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_session.return_value.request.return_value = mock_response

        result = client.append_to_note("Notes/Test.md", "Content")
        assert result is True

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_append_to_note_no_content(self, mock_session, client):
        """Test append_to_note returns True on 204."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_session.return_value.request.return_value = mock_response

        result = client.append_to_note("Notes/Test.md", "Content")
        assert result is True

    @patch("obsidian_clipper.obsidian.api.requests.Session")
    def test_ensure_note_exists_created_204(self, mock_session, client):
        """Test ensure_note_exists returns True on 204."""
        mock_get = Mock()
        mock_get.status_code = 404
        mock_put = Mock()
        mock_put.status_code = 204

        mock_session.return_value.request.side_effect = [mock_get, mock_put]

        result = client.ensure_note_exists("Notes/New.md")
        assert result is True
