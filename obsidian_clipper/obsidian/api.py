"""Obsidian Local REST API client."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import urllib3
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Suppress SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from ..config import Config, get_config
from ..exceptions import APIConnectionError, APIRequestError, PathSecurityError

logger = logging.getLogger(__name__)

# Pattern for detecting path traversal attempts
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
    path = path.replace("\\", "/")
    while path.startswith("/"):
        path = path[1:]
    if not path:
        return ""
    if PATH_TRAVERSAL_PATTERN.search(path):
        raise PathSecurityError(f"Path traversal detected: {path}")
    return path


class ObsidianClient:
    """Client for Obsidian Local REST API."""

    def __init__(self, config: Config | None = None):
        self.config = config or get_config()
        self._session: requests.Session | None = None

    def _get_session(self) -> requests.Session:
        """Get or create HTTP session with connection pooling."""
        if self._session is None:
            self._session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=0.3,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=10,
                pool_maxsize=20,
            )
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
            self._session.headers.update({"Connection": "keep-alive"})
        return self._session

    def _build_url(self, path: str) -> str:
        safe_path = validate_path(path)
        return f"{self.config.base_url}/vault/{safe_path}"

    def _execute_request(
        self, method: str, url: str, **kwargs: Any
    ) -> requests.Response:
        """Execute an HTTP request with error handling."""
        kwargs.setdefault("headers", {})
        kwargs["headers"].update(self.config.headers)
        kwargs.setdefault("verify", self.config.verify_ssl)
        kwargs.setdefault("timeout", self.config.timeout)

        try:
            return self._get_session().request(method, url, **kwargs)
        except requests.exceptions.ConnectionError as e:
            raise APIConnectionError(f"Failed to connect to Obsidian API: {e}") from e
        except requests.exceptions.Timeout as e:
            raise APIRequestError("Request timed out") from e
        except requests.exceptions.RequestException as e:
            raise APIRequestError(f"Request failed: {e}") from e

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        """Make an API request with path validation."""
        return self._execute_request(method, self._build_url(path), **kwargs)

    def check_connection(self) -> bool:
        """Check if the Obsidian Local REST API is reachable."""
        try:
            url = self.config.base_url + "/"
            response = self._execute_request("GET", url)
            return response.status_code in (200, 404)
        except (APIConnectionError, APIRequestError):
            return False

    def create_note(self, note_path: str, content: str) -> bool:
        """Create a new note with content.

        Args:
            note_path: Path for new note (relative to vault root).
            content: Note content.

        Returns:
            True if successful.
        """
        try:
            response = self._request(
                "PUT",
                note_path,
                headers={**self.config.headers, "Content-Type": "text/markdown"},
                data=content.encode("utf-8"),
            )
            return response.status_code in (200, 201, 204)
        except (APIConnectionError, APIRequestError) as e:
            logger.error(f"Failed to create note: {e}")
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
        dest_path = f"{directory}{filename}"

        try:
            with open(img_path, "rb") as f:
                img_data = f.read()

            response = self._request(
                "PUT",
                dest_path,
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

    def __enter__(self) -> "ObsidianClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
