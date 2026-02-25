"""Obsidian Local REST API client."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import Config, get_config
from ..exceptions import (
    APIConnectionError,
    APIRequestError,
    PathSecurityError,
)

logger = logging.getLogger(__name__)

# Pattern for detecting path traversal attempts (.. and Windows drive letters)
PATH_TRAVERSAL_PATTERN = re.compile(r"\.\.(/|\\)|^\w+:")


def validate_path(path: str) -> str:
    """Validate a path for security.

    Args:
        path: Path to validate.

    Returns:
        Sanitized path.

    Raises:
        PathSecurityError: If path contains traversal attempts.
    """
    # Normalize path separators
    path = path.replace("\\", "/")

    # Remove leading slashes (safe to do before validation)
    while path.startswith("/"):
        path = path[1:]

    # Handle empty path (root-level API calls)
    if not path:
        return ""

    # Check for path traversal and Windows drive letters
    if PATH_TRAVERSAL_PATTERN.search(path):
        raise PathSecurityError(f"Path traversal detected: {path}")

    return path


class ObsidianClient:
    """Client for Obsidian Local REST API.

    Features:
    - Connection pooling with retry logic
    - Path validation for security
    - Proper error handling
    - Session management

    Example:
        client = ObsidianClient()
        if client.check_connection():
            client.append_to_note("notes.md", "New content")
    """

    def __init__(self, config: Config | None = None):
        """Initialize the API client.

        Args:
            config: Configuration instance. Uses global config if None.
        """
        self.config = config or get_config()
        self._session: requests.Session | None = None

    def _get_session(self) -> requests.Session:
        """Get or create HTTP session with connection pooling."""
        if self._session is None:
            self._session = requests.Session()

            # Configure retry strategy with improved settings
            retry_strategy = Retry(
                total=3,
                backoff_factor=0.3,
                status_forcelist=[429, 500, 502, 503, 504],
            )

            # Configure connection pooling
            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=10,
                pool_maxsize=20,
            )
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)

            # Add keep-alive header for persistent connections
            self._session.headers.update({"Connection": "keep-alive"})

        return self._session

    def _build_url(self, path: str) -> str:
        """Build full URL for API endpoint.

        Args:
            path: API path (will be validated).

        Returns:
            Full URL string.
        """
        safe_path = validate_path(path)
        return f"{self.config.base_url}/vault/{safe_path}"

    def _execute_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> requests.Response:
        """Execute an HTTP request with error handling.

        Args:
            method: HTTP method.
            url: Full URL.
            **kwargs: Additional arguments for requests.

        Returns:
            Response object.

        Raises:
            APIConnectionError: If connection fails.
            APIRequestError: If request fails.
        """
        kwargs.setdefault("headers", {})
        kwargs["headers"].update(self.config.headers)
        kwargs.setdefault("verify", self.config.verify_ssl)
        kwargs.setdefault("timeout", self.config.timeout)

        try:
            session = self._get_session()
            response = session.request(method, url, **kwargs)
            return response
        except requests.exceptions.ConnectionError as e:
            raise APIConnectionError(f"Failed to connect to Obsidian API: {e}") from e
        except requests.exceptions.Timeout as e:
            raise APIRequestError("Request timed out") from e
        except requests.exceptions.RequestException as e:
            raise APIRequestError(f"Request failed: {e}") from e

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> requests.Response:
        """Make an API request with path validation.

        Args:
            method: HTTP method.
            path: API path (will be validated).
            **kwargs: Additional arguments for requests.

        Returns:
            Response object.

        Raises:
            APIRequestError: If request fails.
        """
        url = self._build_url(path)
        return self._execute_request(method, url, **kwargs)

    def check_connection(self) -> bool:
        """Check if the Obsidian Local REST API is reachable.

        Returns:
            True if API is reachable.
        """
        try:
            # Use root endpoint directly without path validation
            url = self.config.base_url + "/"
            response = self._execute_request("GET", url)
            return response.status_code in (200, 404)
        except (APIConnectionError, APIRequestError):
            return False

    def note_exists(self, note_path: str) -> bool:
        """Check if a note exists.

        Args:
            note_path: Path to note (relative to vault root).

        Returns:
            True if note exists.
        """
        try:
            response = self._request("GET", note_path)
            return response.status_code == 200
        except (APIConnectionError, APIRequestError):
            return False

    def ensure_note_exists(
        self,
        note_path: str,
        initial_content: str = "# Quick Captures\n",
    ) -> bool:
        """Create target note if missing.

        Args:
            note_path: Path to note (relative to vault root).
            initial_content: Content for new note.

        Returns:
            True if note exists or was created successfully.
        """
        safe_path = validate_path(note_path)

        try:
            response = self._request("GET", safe_path)
            if response.status_code == 200:
                return True

            if response.status_code == 404:
                create_response = self._request(
                    "PUT",
                    safe_path,
                    headers={**self.config.headers, "Content-Type": "text/markdown"},
                    data=initial_content.encode("utf-8"),
                )
                return create_response.status_code in (200, 201, 204)

            return False
        except (APIConnectionError, APIRequestError) as e:
            logger.error(f"Failed to ensure note exists: {e}")
            return False

    def append_to_note(self, note_path: str, content: str) -> bool:
        """Append content to a note.

        Args:
            note_path: Path to note (relative to vault root).
            content: Content to append.

        Returns:
            True if successful.
        """
        safe_path = validate_path(note_path)

        try:
            response = self._request(
                "POST",
                safe_path,
                headers={**self.config.headers, "Content-Type": "text/markdown"},
                data=content.encode("utf-8"),
            )
            return response.status_code in (200, 201, 204)
        except (APIConnectionError, APIRequestError) as e:
            logger.error(f"Failed to append to note: {e}")
            return False

    def upload_image(
        self,
        img_path: str | Path,
        dest_filename: str | None = None,
        dest_dir: str | None = None,
    ) -> bool:
        """Upload an image to the vault.

        Args:
            img_path: Path to local image file.
            dest_filename: Destination filename. Uses source filename if None.
            dest_dir: Destination directory. Uses config default if None.

        Returns:
            True if successful.
        """
        img_path = Path(img_path)
        if not img_path.exists():
            logger.error(f"Image file not found: {img_path}")
            return False

        filename = dest_filename or img_path.name
        directory = dest_dir or self.config.attachment_dir

        # Build destination path
        dest_path = f"{directory}{filename}"
        safe_dest = validate_path(dest_path)

        try:
            with open(img_path, "rb") as f:
                img_data = f.read()

            response = self._request(
                "PUT",
                safe_dest,
                headers={**self.config.headers, "Content-Type": "image/png"},
                data=img_data,
            )
            return response.status_code in (200, 201, 204)
        except (APIConnectionError, APIRequestError) as e:
            logger.error(f"Failed to upload image: {e}")
            return False
        except OSError as e:
            logger.error(f"Failed to read image file: {e}")
            return False

    def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self) -> ObsidianClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()
